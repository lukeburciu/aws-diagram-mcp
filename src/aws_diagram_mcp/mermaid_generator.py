"""Mermaid diagram generator for AWS infrastructure."""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class MermaidDiagramGenerator:
    """Generates Mermaid diagrams from AWS resource data."""
    
    def __init__(self):
        self.node_counter = 0
        self.node_map = {}
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
        region: str = "us-east-1"
    ) -> str:
        """Generate a complete Mermaid diagram."""
        self.node_counter = 0
        self.node_map = {}
        self.connections = []
        
        diagram_lines = ["graph TD"]
        
        account_id = account_info.get("account_id", "unknown")
        account_name = f"Account: {account_id}"
        
        diagram_lines.append(f'    subgraph Account["{account_name}"]')
        
        for vpc in vpcs:
            vpc_lines = self._generate_vpc_section(
                vpc, region, subnets, instances, load_balancers, rds_instances
            )
            diagram_lines.extend(vpc_lines)
        
        diagram_lines.append("    end")
        
        if route53_zones:
            route53_lines = self._generate_route53_section(route53_zones, load_balancers)
            diagram_lines.extend(route53_lines)
        
        connection_lines = self._generate_connections(
            instances, load_balancers, rds_instances, security_groups
        )
        diagram_lines.extend(connection_lines)
        
        return "\n".join(diagram_lines)
    
    def _generate_vpc_section(
        self,
        vpc: Dict[str, Any],
        region: str,
        subnets: List[Dict[str, Any]],
        instances: List[Dict[str, Any]],
        load_balancers: List[Dict[str, Any]],
        rds_instances: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate VPC section of the diagram."""
        lines = []
        vpc_id = vpc["vpc_id"]
        vpc_name = vpc["tags"].get("Name", vpc_id)
        
        lines.append(f'        subgraph VPC_{self._sanitize_id(vpc_id)}["VPC: {vpc_name}"]')
        lines.append(f'            subgraph Region_{self._sanitize_id(region)}["Region: {region}"]')
        
        vpc_subnets = [s for s in subnets if s["vpc_id"] == vpc_id]
        vpc_instances = [i for i in instances if i["vpc_id"] == vpc_id]
        vpc_lbs = [lb for lb in load_balancers if lb["vpc_id"] == vpc_id]
        vpc_rds = [rds for rds in rds_instances if rds["vpc_id"] == vpc_id]
        
        subnet_resources = self._organize_resources_by_subnet(
            vpc_subnets, vpc_instances, vpc_lbs, vpc_rds
        )
        
        tier_order = ["presentation", "application", "restricted"]
        for tier in tier_order:
            tier_subnets = [s for s in vpc_subnets if s.get("tier") == tier]
            if not tier_subnets:
                continue
            
            for subnet in tier_subnets:
                subnet_id = subnet["subnet_id"]
                if subnet_id not in subnet_resources or not subnet_resources[subnet_id]:
                    continue
                
                subnet_lines = self._generate_subnet_section(
                    subnet, subnet_resources[subnet_id]
                )
                lines.extend(subnet_lines)
        
        lines.append("            end")
        lines.append("        end")
        
        return lines
    
    def _generate_subnet_section(
        self,
        subnet: Dict[str, Any],
        resources: Dict[str, List[Dict[str, Any]]]
    ) -> List[str]:
        """Generate subnet section of the diagram."""
        lines = []
        subnet_id = subnet["subnet_id"]
        subnet_name = subnet["tags"].get("Name", subnet_id)
        tier = subnet.get("tier", "unknown")
        
        tier_labels = {
            "presentation": "Public Subnet",
            "application": "Application Subnet",
            "restricted": "Restricted Subnet"
        }
        label = tier_labels.get(tier, f"Subnet: {subnet_name}")
        
        lines.append(f'                subgraph Subnet_{self._sanitize_id(subnet_id)}["{label}"]')
        
        for lb in resources.get("load_balancers", []):
            node_id = self._get_node_id(f"lb_{lb['name']}")
            ips = "<br/>".join(lb.get("ips", []))
            node_label = f"{lb['type']}: {lb['name']}"
            if ips:
                node_label += f"<br/>{ips}"
            lines.append(f'                    {node_id}[/"{node_label}"\\]')
            self.node_map[lb["arn"]] = node_id
        
        for instance in resources.get("instances", []):
            node_id = self._get_node_id(f"ec2_{instance['instance_id']}")
            name = instance.get("name", instance["instance_id"])
            ip = instance.get("private_ip", "no-ip")
            node_label = f"EC2: {name}<br/>{ip}"
            lines.append(f'                    {node_id}["{node_label}"]')
            self.node_map[instance["instance_id"]] = node_id
        
        for rds in resources.get("rds", []):
            node_id = self._get_node_id(f"rds_{rds['db_instance_id']}")
            node_label = f"RDS: {rds['db_instance_id']}<br/>{rds['engine']}"
            if rds.get("endpoint"):
                node_label += f"<br/>{rds['endpoint']}"
            lines.append(f'                    {node_id}[("{node_label}")]')
            self.node_map[rds["db_instance_id"]] = node_id
        
        lines.append("                end")
        
        return lines
    
    def _generate_route53_section(
        self,
        route53_zones: List[Dict[str, Any]],
        load_balancers: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate Route53 section."""
        lines = []
        
        for zone in route53_zones:
            node_id = self._get_node_id(f"route53_{zone['zone_id']}")
            node_label = f"Route53: {zone['name']}"
            lines.append(f'    {node_id}(["{node_label}"])')
            self.node_map[zone["zone_id"]] = node_id
            
            for record in zone.get("records", []):
                for value in record.get("values", []):
                    for lb in load_balancers:
                        if lb["dns_name"] in value:
                            self.connections.append({
                                "from": node_id,
                                "to": self.node_map.get(lb["arn"]),
                                "label": "53/tcp",
                                "style": "standard"
                            })
        
        return lines
    
    def _generate_connections(
        self,
        instances: List[Dict[str, Any]],
        load_balancers: List[Dict[str, Any]],
        rds_instances: List[Dict[str, Any]],
        security_groups: Dict[str, Any]
    ) -> List[str]:
        """Generate connection lines."""
        lines = []
        
        for lb in load_balancers:
            lb_node = self.node_map.get(lb["arn"])
            if not lb_node:
                continue
            
            for tg in lb.get("target_groups", []):
                port = tg.get("port", 443)
                protocol = tg.get("protocol", "tcp").lower()
                
                for target in tg.get("targets", []):
                    target_id = target["id"]
                    target_node = self.node_map.get(target_id)
                    if target_node:
                        lines.append(f'    {lb_node} ==>|"{port}/{protocol}"| {target_node}')
        
        sg_connections = self._analyze_security_group_connections(
            instances, rds_instances, security_groups
        )
        
        for conn in sg_connections:
            from_node = self.node_map.get(conn["from"])
            to_node = self.node_map.get(conn["to"])
            if from_node and to_node:
                label = conn.get("label", "")
                if conn.get("type") == "database":
                    lines.append(f'    {from_node} -.->|"{label}"| {to_node}')
                else:
                    lines.append(f'    {from_node} -->|"{label}"| {to_node}')
        
        for conn in self.connections:
            if conn["from"] and conn["to"]:
                lines.append(f'    {conn["from"]} -->|"{conn["label"]}"| {conn["to"]}')
        
        return lines
    
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
        
        for rds in rds_instances:
            if rds.get("subnet_group"):
                for subnet in subnets:
                    subnet_resources[subnet["subnet_id"]]["rds"].append(rds)
                    break
        
        return subnet_resources
    
    def _analyze_security_group_connections(
        self,
        instances: List[Dict[str, Any]],
        rds_instances: List[Dict[str, Any]],
        security_groups: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze security group rules to determine connections."""
        connections = []
        
        instance_sg_map = {}
        for instance in instances:
            for sg_id in instance.get("security_groups", []):
                if sg_id not in instance_sg_map:
                    instance_sg_map[sg_id] = []
                instance_sg_map[sg_id].append(instance["instance_id"])
        
        rds_sg_map = {}
        for rds in rds_instances:
            for sg_id in rds.get("security_groups", []):
                if sg_id not in rds_sg_map:
                    rds_sg_map[sg_id] = []
                rds_sg_map[sg_id].append(rds["db_instance_id"])
        
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
                        
                        for from_id in from_instances:
                            for to_id in to_instances:
                                if from_id != to_id:
                                    connections.append({
                                        "from": from_id,
                                        "to": to_id,
                                        "label": label,
                                        "type": "instance"
                                    })
                            
                            for to_id in to_rds:
                                connections.append({
                                    "from": from_id,
                                    "to": to_id,
                                    "label": label,
                                    "type": "database"
                                })
        
        return connections
    
    def _get_node_id(self, prefix: str) -> str:
        """Generate a unique node ID."""
        self.node_counter += 1
        return f"{self._sanitize_id(prefix)}_{self.node_counter}"
    
    def _sanitize_id(self, text: str) -> str:
        """Sanitize text for use as Mermaid node ID."""
        return text.replace("-", "_").replace(".", "_").replace("/", "_")
    
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
    
    def save_diagram(self, diagram: str, output_path: str) -> None:
        """Save the diagram to a file."""
        with open(output_path, "w") as f:
            f.write("# AWS Infrastructure Diagram\n\n")
            f.write("```mermaid\n")
            f.write(diagram)
            f.write("\n```\n")
        logger.info(f"Diagram saved to {output_path}")