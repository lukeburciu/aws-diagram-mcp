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
import shutil

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
        output_path: str = "aws_infrastructure"
    ) -> str:
        """Generate a complete DOT diagram using Python Diagrams."""
        self.nodes = {}
        self.connections = []
        
        account_id = account_info.get("account_id", "unknown")
        diagram_title = f"AWS Infrastructure - {account_id}"
        
        # Set output directory
        output_dir = Path(output_path).parent
        output_name = Path(output_path).stem
        
        # Generate the diagram with a temporary name to preserve the .dot file
        temp_output_path = output_dir / f"{output_name}_temp"
        final_dot_path = output_dir / f"{output_name}.dot"
        
        with Diagram(
            diagram_title,
            filename=str(temp_output_path),
            show=False,
            direction="TB",
            graph_attr={
                "splines": "ortho",
                "nodesep": "1.0",
                "ranksep": "1.5",
                "bgcolor": "white"
            }
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
                instances, load_balancers, rds_instances, security_groups, route53_zones
            )
        
        # Copy the temporary dot file to preserve it
        temp_dot_path = temp_output_path.with_suffix('.dot')
        if temp_dot_path.exists():
            shutil.copy2(temp_dot_path, final_dot_path)
        
        # Move/rename the generated image files
        temp_png_path = temp_output_path.with_suffix('.png')
        temp_svg_path = temp_output_path.with_suffix('.svg')
        
        final_png_path = output_dir / f"{output_name}.png"
        final_svg_path = output_dir / f"{output_name}.svg"
        
        if temp_png_path.exists():
            shutil.move(temp_png_path, final_png_path)
        if temp_svg_path.exists():
            shutil.move(temp_svg_path, final_svg_path)
        
        # Clean up temporary dot file
        if temp_dot_path.exists():
            temp_dot_path.unlink()
        
        # Return the path to the generated files
        dot_path = str(final_dot_path)
        png_path = str(final_png_path)
        
        return {
            "dot_file": dot_path if final_dot_path.exists() else None,
            "png_file": png_path if final_png_path.exists() else None,
            "svg_file": str(final_svg_path) if final_svg_path.exists() else None
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
        route53_zones: List[Dict[str, Any]]
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
        
        # Security Group based connections (filter out intra-subnet traffic)
        sg_connections = self._analyze_security_group_connections(
            instances, rds_instances, security_groups
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
        security_groups: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze security group rules to determine inter-subnet connections only."""
        connections = []
        
        # Create instance ID to subnet mapping
        instance_subnet_map = {}
        for instance in instances:
            instance_subnet_map[instance["instance_id"]] = instance.get("subnet_id")
        
        # Create RDS ID to subnet mapping (RDS typically spans multiple subnets)
        rds_subnet_map = {}
        for rds in rds_instances:
            # RDS instances don't have a single subnet, so we'll always allow connections to them
            rds_subnet_map[rds["db_instance_id"]] = None
        
        # Map security groups to instances
        instance_sg_map = {}
        for instance in instances:
            for sg_id in instance.get("security_groups", []):
                if sg_id not in instance_sg_map:
                    instance_sg_map[sg_id] = []
                instance_sg_map[sg_id].append(instance["instance_id"])
        
        # Map security groups to RDS instances
        rds_sg_map = {}
        for rds in rds_instances:
            for sg_id in rds.get("security_groups", []):
                if sg_id not in rds_sg_map:
                    rds_sg_map[sg_id] = []
                rds_sg_map[sg_id].append(rds["db_instance_id"])
        
        # Analyze ingress rules
        for sg_id, sg_info in security_groups.items():
            for rule in sg_info.get("rules", {}).get("ingress", []):
                for source in rule.get("sources", []):
                    if source["type"] == "security_group":
                        source_sg = source["value"]
                        
                        from_instances = instance_sg_map.get(source_sg, [])
                        to_instances = instance_sg_map.get(sg_id, [])
                        to_rds = rds_sg_map.get(sg_id, [])
                        
                        port = rule.get("to_port", rule.get("from_port", ""))
                        protocol = self._normalize_protocol(rule.get("protocol", "tcp"))
                        label = f"{port}/{protocol}" if port else protocol
                        
                        # Instance to instance connections (only inter-subnet)
                        for from_id in from_instances:
                            from_subnet = instance_subnet_map.get(from_id)
                            
                            for to_id in to_instances:
                                to_subnet = instance_subnet_map.get(to_id)
                                
                                # Only show connections between different subnets or when subnet is unknown
                                if (from_id != to_id and 
                                    (from_subnet != to_subnet or not from_subnet or not to_subnet)):
                                    connections.append({
                                        "from": from_id,
                                        "to": to_id,
                                        "label": label,
                                        "type": "instance"
                                    })
                            
                            # Instance to database connections (always show - databases span subnets)
                            for to_id in to_rds:
                                connections.append({
                                    "from": from_id,
                                    "to": to_id,
                                    "label": label,
                                    "type": "database"
                                })
        
        return connections
    
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