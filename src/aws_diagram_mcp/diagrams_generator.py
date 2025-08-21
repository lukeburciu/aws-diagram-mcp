"""Python Diagrams generator for AWS infrastructure (DOT/Graphviz output)."""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
import os
from collections import defaultdict

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB, ALB, NLB, Route53
from diagrams.aws.security import ACM
from diagrams.aws.general import General

logger = logging.getLogger(__name__)


class DiagramsGenerator:
    """Generates DOT/Graphviz diagrams using Python Diagrams from AWS resource data."""
    
    def __init__(self):
        self.nodes = {}
        self.connections = []
    
    def generate_diagram(
        self,
        account_info: Dict[str, str],
        vpcs: List[Dict[str, Any]],
        subnets: List[Dict[str, Any]],
        instances: List[Dict[str, Any]],
        load_balancers: List[Dict[str, Any]],
        rds_instances: List[Dict[str, Any]],
        security_groups: Dict[str, Any],
        route53_zones: List[Dict[str, Any]],
        region: str = "us-east-1",
        output_path: str = "aws_infrastructure",
        sg_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a complete DOT diagram using Python Diagrams."""
        self.nodes = {}
        self.connections = []
        
        account_id = account_info.get("account_id", "unknown")
        diagram_title = f"AWS Infrastructure - {account_id}"
        
        # Set output directory
        output_dir = Path(output_path).parent
        output_name = Path(output_path).stem
        
        # Generate the diagram directly to final location
        final_output_path = output_dir / output_name
        
        with Diagram(
            diagram_title,
            filename=str(final_output_path),
            show=False,
            direction="TB",
            graph_attr={
                "splines": "ortho",
                "nodesep": "1.0",
                "ranksep": "1.5",
                "bgcolor": "white"
            },
            outformat=["dot", "png", "svg"]
        ) as diagram:
            
            # Create Route53 nodes first (they go at the top)
            route53_nodes = self._create_route53_nodes(route53_zones)
            
            # Process each VPC
            for vpc in vpcs:
                self._create_vpc_cluster(
                    vpc, region, subnets, instances, load_balancers, rds_instances
                )
            
            # Create connections after all nodes are created
            self._create_connections(
                instances, load_balancers, rds_instances, security_groups, route53_zones, 
                subnets, sg_options or {}
            )
        
        # The outformat parameter generates all files automatically
        # Check which files were actually created
        dot_path = final_output_path.with_suffix('.dot')
        png_path = final_output_path.with_suffix('.png')
        svg_path = final_output_path.with_suffix('.svg')
        
        return {
            "dot_file": str(dot_path) if dot_path.exists() else None,
            "png_file": str(png_path) if png_path.exists() else None,
            "svg_file": str(svg_path) if svg_path.exists() else None
        }
    
    def _create_route53_nodes(self, route53_zones: List[Dict[str, Any]]) -> List[Any]:
        """Create Route53 nodes."""
        route53_nodes = []
        for zone in route53_zones:
            zone_name = zone["name"].rstrip(".")
            node = Route53(f"Route53\n{zone_name}")
            self.nodes[zone["zone_id"]] = node
            route53_nodes.append(node)
        return route53_nodes
    
    def _create_vpc_cluster(
        self,
        vpc: Dict[str, Any],
        region: str,
        subnets: List[Dict[str, Any]],
        instances: List[Dict[str, Any]],
        load_balancers: List[Dict[str, Any]],
        rds_instances: List[Dict[str, Any]]
    ) -> None:
        """Create VPC cluster with all its resources."""
        vpc_id = vpc["vpc_id"]
        vpc_name = vpc["tags"].get("Name", vpc_id)
        
        with Cluster(f"VPC: {vpc_name}\n({vpc['cidr_block']})"):
            with Cluster(f"Region: {region}"):
                
                # Filter resources for this VPC
                vpc_subnets = [s for s in subnets if s["vpc_id"] == vpc_id]
                vpc_instances = [i for i in instances if i["vpc_id"] == vpc_id]
                vpc_lbs = [lb for lb in load_balancers if lb["vpc_id"] == vpc_id]
                vpc_rds = [rds for rds in rds_instances if rds["vpc_id"] == vpc_id]
                
                # Organize resources by subnet
                subnet_resources = self._organize_resources_by_subnet(
                    vpc_subnets, vpc_instances, vpc_lbs, vpc_rds
                )
                
                # Create subnet clusters in tier order
                tier_order = ["presentation", "application", "restricted"]
                for tier in tier_order:
                    tier_subnets = [s for s in vpc_subnets if s.get("tier") == tier]
                    
                    for subnet in tier_subnets:
                        subnet_id = subnet["subnet_id"]
                        if subnet_id not in subnet_resources or not subnet_resources[subnet_id]:
                            continue
                        
                        self._create_subnet_cluster(subnet, subnet_resources[subnet_id])
    
    def _create_subnet_cluster(
        self,
        subnet: Dict[str, Any],
        resources: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """Create subnet cluster with its resources."""
        subnet_id = subnet["subnet_id"]
        subnet_name = subnet["tags"].get("Name", subnet_id)
        tier = subnet.get("tier", "unknown")
        
        tier_labels = {
            "presentation": "Public Subnet",
            "application": "Application Subnet", 
            "restricted": "Restricted Subnet"
        }
        label = f"{tier_labels.get(tier, 'Subnet')}\n{subnet_name}\n({subnet['cidr_block']})"
        
        with Cluster(label):
            
            # Create load balancer nodes
            for lb in resources.get("load_balancers", []):
                lb_type = lb["type"].upper()
                lb_name = lb["name"]
                ips = ", ".join(lb.get("ips", [])[:2])  # Limit to first 2 IPs for space
                
                if lb_type == "APPLICATION":
                    node = ALB(f"{lb_name}\n{ips}" if ips else lb_name)
                elif lb_type == "NETWORK":
                    node = NLB(f"{lb_name}\n{ips}" if ips else lb_name)
                else:
                    node = ELB(f"{lb_name}\n{ips}" if ips else lb_name)
                
                self.nodes[lb["arn"]] = node
            
            # Create EC2 instance nodes
            for instance in resources.get("instances", []):
                name = instance.get("name", instance["instance_id"])
                ip = instance.get("private_ip", "no-ip")
                instance_type = instance.get("instance_type", "")
                
                label = f"{name}\n{ip}"
                if instance_type:
                    label += f"\n({instance_type})"
                
                node = EC2(label)
                self.nodes[instance["instance_id"]] = node
            
            # Create RDS nodes
            for rds in resources.get("rds", []):
                db_id = rds["db_instance_id"]
                engine = rds["engine"]
                endpoint = rds.get("endpoint", "")
                
                label = f"{db_id}\n{engine}"
                if endpoint:
                    label += f"\n{endpoint}"
                
                node = RDS(label)
                self.nodes[rds["db_instance_id"]] = node
    
    def _create_connections(
        self,
        instances: List[Dict[str, Any]],
        load_balancers: List[Dict[str, Any]],
        rds_instances: List[Dict[str, Any]],
        security_groups: Dict[str, Any],
        route53_zones: List[Dict[str, Any]],
        subnets: List[Dict[str, Any]],
        sg_options: Dict[str, Any]
    ) -> None:
        """Create all connections between nodes."""
        
        # Route53 to Load Balancer connections
        for zone in route53_zones:
            zone_node = self.nodes.get(zone["zone_id"])
            if not zone_node:
                continue
            
            for record in zone.get("records", []):
                for value in record.get("values", []):
                    for lb in load_balancers:
                        if lb["dns_name"] in value:
                            lb_node = self.nodes.get(lb["arn"])
                            if lb_node:
                                zone_node >> Edge(label="53/tcp", color="blue") >> lb_node
        
        # Load Balancer to Target connections
        for lb in load_balancers:
            lb_node = self.nodes.get(lb["arn"])
            if not lb_node:
                continue
            
            for tg in lb.get("target_groups", []):
                port = tg.get("port", 443)
                protocol = tg.get("protocol", "tcp").lower()
                
                for target in tg.get("targets", []):
                    target_id = target["id"]
                    target_node = self.nodes.get(target_id)
                    if target_node:
                        lb_node >> Edge(
                            label=f"{port}/{protocol}",
                            color="green",
                            style="bold"
                        ) >> target_node
        
        # Security Group based connections with smart filtering
        sg_connections = self._analyze_security_group_connections(
            instances, rds_instances, security_groups, subnets, sg_options
        )
        
        for conn in sg_connections:
            from_node = self.nodes.get(conn["from"])
            to_node = self.nodes.get(conn["to"])
            
            if from_node and to_node:
                edge_color = "red" if conn.get("type") == "database" else "orange"
                edge_style = "dashed" if conn.get("type") == "database" else "solid"
                
                from_node >> Edge(
                    label=conn.get("label", ""),
                    color=edge_color,
                    style=edge_style
                ) >> to_node
    
    def _organize_resources_by_subnet(
        self,
        subnets: List[Dict[str, Any]],
        instances: List[Dict[str, Any]],
        load_balancers: List[Dict[str, Any]],
        rds_instances: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, List]]:
        """Organize resources by subnet."""
        subnet_resources = defaultdict(lambda: {
            "instances": [],
            "load_balancers": [],
            "rds": []
        })
        
        for instance in instances:
            subnet_id = instance.get("subnet_id")
            if subnet_id:
                subnet_resources[subnet_id]["instances"].append(instance)
        
        for lb in load_balancers:
            for subnet_id in lb.get("subnets", []):
                subnet_resources[subnet_id]["load_balancers"].append(lb)
        
        # RDS instances are typically in subnet groups spanning multiple subnets
        for rds in rds_instances:
            if rds.get("subnet_group"):
                # Add RDS to restricted tier subnets
                for subnet in subnets:
                    if subnet.get("tier") == "restricted":
                        subnet_resources[subnet["subnet_id"]]["rds"].append(rds)
                        break
        
        return subnet_resources
    
    def _analyze_security_group_connections(
        self,
        instances: List[Dict[str, Any]],
        rds_instances: List[Dict[str, Any]],
        security_groups: Dict[str, Any],
        subnets: List[Dict[str, Any]],
        sg_options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze security group rules with smart behavioral filtering."""
        connections = []
        
        # Early exit if flows are set to none
        flows = sg_options.get("flows", "inter-subnet")
        if flows == "none":
            return connections
        
        # Get filtering options
        direction_filter = sg_options.get("direction", "both")
        detail_level = sg_options.get("detail", "ports")
        filter_internal = sg_options.get("filter_internal", False)
        only_ingress = sg_options.get("only_ingress", False)
        
        # Create mappings
        instance_map = {inst["instance_id"]: inst for inst in instances}
        
        # Map security groups to resources
        instance_sg_map = {}
        rds_sg_map = {}
        
        for instance in instances:
            for sg_id in instance.get("security_groups", []):
                if sg_id not in instance_sg_map:
                    instance_sg_map[sg_id] = []
                instance_sg_map[sg_id].append(instance["instance_id"])
        
        for rds in rds_instances:
            for sg_id in rds.get("security_groups", []):
                if sg_id not in rds_sg_map:
                    rds_sg_map[sg_id] = []
                rds_sg_map[sg_id].append(rds["db_instance_id"])
        
        # Process rules (ingress only if specified)
        rule_types = ["ingress"] if only_ingress else ["ingress", "egress"]
        
        for sg_id, sg_info in security_groups.items():
            for rule_type in rule_types:
                for rule in sg_info.get("rules", {}).get(rule_type, []):
                    # Apply port filtering
                    if not self._filter_by_port_rules(rule, sg_options):
                        continue
                    
                    for source in rule.get("sources", []):
                        if source["type"] == "security_group":
                            source_sg = source["value"]
                            
                            from_instances = instance_sg_map.get(source_sg, [])
                            to_instances = instance_sg_map.get(sg_id, [])
                            to_rds = rds_sg_map.get(sg_id, [])
                            
                            # Generate label
                            label = self._generate_connection_label(rule, detail_level)
                            
                            # Process instance-to-instance connections
                            for from_id in from_instances:
                                from_instance = instance_map.get(from_id)
                                if not from_instance:
                                    continue
                                
                                for to_id in to_instances:
                                    if from_id == to_id:
                                        continue
                                    
                                    to_instance = instance_map.get(to_id)
                                    if not to_instance:
                                        continue
                                    
                                    # Apply flow filtering
                                    flow_type = self._classify_connection_flow(
                                        from_instance, to_instance, subnets, []
                                    )
                                    
                                    if not self._should_show_flow(flow_type, flows, filter_internal):
                                        continue
                                    
                                    # Apply direction filtering
                                    traffic_direction = self._get_traffic_direction(
                                        from_instance, to_instance, subnets
                                    )
                                    
                                    if not self._should_show_direction(traffic_direction, direction_filter):
                                        continue
                                    
                                    connections.append({
                                        "from": from_id,
                                        "to": to_id,
                                        "label": label,
                                        "type": "instance",
                                        "flow_type": flow_type,
                                        "direction": traffic_direction
                                    })
                                
                                # Process instance-to-database connections (always show unless flows=none)
                                for to_id in to_rds:
                                    connections.append({
                                        "from": from_id,
                                        "to": to_id,
                                        "label": label,
                                        "type": "database",
                                        "flow_type": "database",
                                        "direction": "north-south"
                                    })
        
        return connections
    
    def _should_show_flow(self, flow_type: str, flows_filter: str, filter_internal: bool) -> bool:
        """Determine if a flow should be shown based on flow type filters."""
        if filter_internal and flow_type == "intra-subnet":
            return False
        
        if flows_filter == "inter-subnet":
            return flow_type in ["inter-subnet", "tier-crossing"]
        elif flows_filter == "tier-crossing":
            return flow_type == "tier-crossing"
        elif flows_filter == "external-only":
            return flow_type == "external-only"
        
        return True
    
    def _should_show_direction(self, traffic_direction: str, direction_filter: str) -> bool:
        """Determine if a connection should be shown based on direction filter."""
        if direction_filter == "both":
            return True
        elif direction_filter == "north-south":
            return traffic_direction == "north-south"
        elif direction_filter == "east-west":
            return traffic_direction == "east-west"
        
        return True
    
    def _classify_connection_flow(
        self,
        from_instance: Dict[str, Any],
        to_instance: Dict[str, Any],
        subnets: List[Dict[str, Any]],
        load_balancers: List[Dict[str, Any]]
    ) -> str:
        """Classify the type of connection flow."""
        from_subnet_id = from_instance.get("subnet_id")
        to_subnet_id = to_instance.get("subnet_id")
        
        # Find subnet tiers
        from_tier = None
        to_tier = None
        for subnet in subnets:
            if subnet["subnet_id"] == from_subnet_id:
                from_tier = subnet.get("tier", "unknown")
            elif subnet["subnet_id"] == to_subnet_id:
                to_tier = subnet.get("tier", "unknown")
        
        # Check if either instance is behind a load balancer (external traffic)
        for lb in load_balancers:
            for tg in lb.get("target_groups", []):
                for target in tg.get("targets", []):
                    if target["id"] in [from_instance.get("instance_id"), to_instance.get("instance_id")]:
                        return "external-only"
        
        # Determine flow type
        if from_subnet_id == to_subnet_id:
            return "intra-subnet"
        elif from_tier != to_tier and from_tier and to_tier:
            return "tier-crossing"
        else:
            return "inter-subnet"
    
    def _get_traffic_direction(
        self,
        from_instance: Dict[str, Any],
        to_instance: Dict[str, Any],
        subnets: List[Dict[str, Any]]
    ) -> str:
        """Determine traffic direction (north-south vs east-west)."""
        from_subnet_id = from_instance.get("subnet_id")
        to_subnet_id = to_instance.get("subnet_id")
        
        # Find subnet tiers
        from_tier = None
        to_tier = None
        for subnet in subnets:
            if subnet["subnet_id"] == from_subnet_id:
                from_tier = subnet.get("tier", "unknown")
            elif subnet["subnet_id"] == to_subnet_id:
                to_tier = subnet.get("tier", "unknown")
        
        # Define tier hierarchy: presentation -> application -> restricted
        tier_hierarchy = {"presentation": 1, "application": 2, "restricted": 3}
        
        if from_tier and to_tier and from_tier in tier_hierarchy and to_tier in tier_hierarchy:
            from_level = tier_hierarchy[from_tier]
            to_level = tier_hierarchy[to_tier]
            
            if from_level != to_level:
                return "north-south"  # Up or down the stack
            else:
                return "east-west"    # Same tier, lateral traffic
        
        return "both"  # Unknown or mixed
    
    def _filter_by_port_rules(self, rule: Dict[str, Any], sg_options: Dict[str, Any]) -> bool:
        """Filter connections based on port and protocol rules."""
        if sg_options.get("filter_ephemeral", False):
            from_port = rule.get("from_port")
            to_port = rule.get("to_port")
            
            # Filter out high ephemeral ports
            if from_port and from_port > 32768:
                return False
            if to_port and to_port > 32768:
                return False
        
        return True
    
    def _generate_connection_label(
        self,
        rule: Dict[str, Any],
        detail_level: str
    ) -> str:
        """Generate connection labels based on detail level."""
        if detail_level == "minimal":
            return ""
        
        port = rule.get("to_port", rule.get("from_port", ""))
        protocol = self._normalize_protocol(rule.get("protocol", "tcp"))
        
        if detail_level == "ports":
            return str(port) if port else protocol
        elif detail_level == "protocols":
            if port:
                # Add common service names
                service_names = {
                    80: "http", 443: "https", 22: "ssh", 3306: "mysql",
                    5432: "postgres", 6379: "redis", 27017: "mongodb"
                }
                service = service_names.get(port, f"{port}")
                return f"{service}/{protocol}"
            return protocol
        elif detail_level == "full":
            label = f"{port}/{protocol}" if port else protocol
            # Could add source SG info here in future
            return label
        
        return ""
    
    def _normalize_protocol(self, protocol: str) -> str:
        """Normalize protocol string."""
        if protocol == "-1":
            return "all"
        elif protocol == "6":
            return "tcp"
        elif protocol == "17":
            return "udp"
        elif protocol == "1":
            return "icmp"
        return protocol.lower()
    
    def save_diagram_metadata(self, files: Dict[str, str], output_path: str) -> None:
        """Save metadata about the generated diagram files."""
        metadata = {
            "generator": "python-diagrams",
            "format": "dot/graphviz",
            "files": files,
            "description": "AWS Infrastructure Diagram generated using Python Diagrams library"
        }
        
        metadata_path = Path(output_path).parent / f"{Path(output_path).stem}_metadata.json"
        
        import json
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Diagram metadata saved to {metadata_path}")