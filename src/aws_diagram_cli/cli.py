#!/usr/bin/env python3
"""
AWS Infrastructure Diagram CLI Tool
Discover AWS resources and generate comprehensive architecture diagrams.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from .aws_discovery import AWSResourceDiscovery
from .generators.mermaid import MermaidDiagramGenerator
from .generators.diagrams import DiagramsGenerator


def discover_resources(args):
    """Discover AWS resources and print as JSON."""
    discovery = AWSResourceDiscovery(regions=args.regions, profile=args.profile)
    
    regions_str = ", ".join(args.regions)
    print(f"Discovering AWS resources in {regions_str}...")
    
    # Get account info
    account_info = discovery.get_account_info()
    print(f"Account: {account_info.get('account_id', 'Unknown')}")
    
    # Discover resources
    resources = {}
    
    if not args.vpc_id:
        resources["vpcs"] = discovery.discover_vpcs()
        print(f"Found {len(resources['vpcs'])} VPCs")
    
    resources["instances"] = discovery.discover_ec2_instances(vpc_id=args.vpc_id)
    print(f"Found {len(resources['instances'])} EC2 instances")
    
    resources["load_balancers"] = discovery.discover_load_balancers(vpc_id=args.vpc_id)
    print(f"Found {len(resources['load_balancers'])} load balancers")
    
    resources["rds_instances"] = discovery.discover_rds_instances(vpc_id=args.vpc_id)
    print(f"Found {len(resources['rds_instances'])} RDS instances")
    
    resources["subnets"] = discovery.discover_subnets(vpc_id=args.vpc_id)
    print(f"Found {len(resources['subnets'])} subnets")
    
    # Get all security groups from instances, load balancers, and RDS, grouped by region
    sg_ids_by_region = {region: set() for region in args.regions}
    for instance in resources["instances"]:
        region = instance.get("region")
        if region in sg_ids_by_region:
            sg_ids_by_region[region].update(instance.get("security_groups", []))
    for rds in resources["rds_instances"]:
        region = rds.get("region")
        if region in sg_ids_by_region:
            sg_ids_by_region[region].update(rds.get("security_groups", []))
    
    # Convert sets to lists
    sg_ids_by_region = {region: list(sg_ids) for region, sg_ids in sg_ids_by_region.items()}
    resources["security_groups"] = discovery.discover_security_groups(sg_ids_by_region)
    print(f"Found {len(resources['security_groups'])} security groups")
    
    if args.include_route53:
        resources["route53_zones"] = discovery.discover_route53_zones()
        print(f"Found {len(resources['route53_zones'])} Route53 zones")
    
    if args.include_acm:
        resources["certificates"] = discovery.discover_acm_certificates()
        print(f"Found {len(resources['certificates'])} ACM certificates")
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(resources, f, indent=2, default=str)
        print(f"Resources saved to {args.output}")
    else:
        print(json.dumps(resources, indent=2, default=str))


def generate_mermaid(args):
    """Generate Mermaid diagram."""
    discovery = AWSResourceDiscovery(regions=args.regions, profile=args.profile)
    generator = MermaidDiagramGenerator()
    
    regions_str = ", ".join(args.regions)
    print(f"Generating Mermaid diagram for {regions_str}...")
    
    # Discover resources
    resources = {
        "instances": discovery.discover_ec2_instances(vpc_id=args.vpc_id),
        "load_balancers": discovery.discover_load_balancers(vpc_id=args.vpc_id),
        "rds_instances": discovery.discover_rds_instances(vpc_id=args.vpc_id),
        "subnets": discovery.discover_subnets(vpc_id=args.vpc_id),
        "vpcs": discovery.discover_vpcs() if not args.vpc_id else []
    }
    
    # Get security groups from resources, grouped by region
    sg_ids_by_region = {region: set() for region in args.regions}
    for instance in resources["instances"]:
        region = instance.get("region")
        if region in sg_ids_by_region:
            sg_ids_by_region[region].update(instance.get("security_groups", []))
    for rds in resources["rds_instances"]:
        region = rds.get("region")
        if region in sg_ids_by_region:
            sg_ids_by_region[region].update(rds.get("security_groups", []))
    
    # Convert sets to lists
    sg_ids_by_region = {region: list(sg_ids) for region, sg_ids in sg_ids_by_region.items()}
    resources["security_groups"] = discovery.discover_security_groups(sg_ids_by_region)
    
    if args.include_route53:
        resources["route53_zones"] = discovery.discover_route53_zones()
    
    if args.include_acm:
        resources["certificates"] = discovery.discover_acm_certificates()
    
    # Generate diagram
    account_info = discovery.get_account_info()
    diagram = generator.generate_diagram(
        account_info=account_info,
        vpcs=resources.get("vpcs", []),
        subnets=resources.get("subnets", []),
        instances=resources.get("instances", []),
        load_balancers=resources.get("load_balancers", []),
        rds_instances=resources.get("rds_instances", []),
        security_groups=resources.get("security_groups", {}),
        route53_zones=resources.get("route53_zones", []),
        regions=args.regions
    )
    
    # Save or print
    if args.output:
        output_path = Path(args.output)
        if output_path.suffix != '.md':
            output_path = output_path.with_suffix('.md')
        
        content = f"# AWS Infrastructure Diagram\n\n```mermaid\n{diagram}\n```\n"
        output_path.write_text(content)
        print(f"Mermaid diagram saved to {output_path}")
    else:
        print(diagram)


def generate_dot(args):
    """Generate DOT/Graphviz diagram."""
    discovery = AWSResourceDiscovery(regions=args.regions, profile=args.profile)
    generator = DiagramsGenerator()
    
    regions_str = ", ".join(args.regions)
    print(f"Generating DOT diagram for {regions_str}...")
    
    # Discover resources
    resources = {
        "instances": discovery.discover_ec2_instances(vpc_id=args.vpc_id),
        "load_balancers": discovery.discover_load_balancers(vpc_id=args.vpc_id),
        "rds_instances": discovery.discover_rds_instances(vpc_id=args.vpc_id),
        "subnets": discovery.discover_subnets(vpc_id=args.vpc_id),
        "vpcs": discovery.discover_vpcs() if not args.vpc_id else []
    }
    
    # Get security groups from resources, grouped by region
    sg_ids_by_region = {region: set() for region in args.regions}
    for instance in resources["instances"]:
        region = instance.get("region")
        if region in sg_ids_by_region:
            sg_ids_by_region[region].update(instance.get("security_groups", []))
    for rds in resources["rds_instances"]:
        region = rds.get("region")
        if region in sg_ids_by_region:
            sg_ids_by_region[region].update(rds.get("security_groups", []))
    
    # Convert sets to lists
    sg_ids_by_region = {region: list(sg_ids) for region, sg_ids in sg_ids_by_region.items()}
    resources["security_groups"] = discovery.discover_security_groups(sg_ids_by_region)
    
    if args.include_route53:
        resources["route53_zones"] = discovery.discover_route53_zones()
    
    if args.include_acm:
        resources["certificates"] = discovery.discover_acm_certificates()
    
    # Generate diagram
    account_info = discovery.get_account_info()
    output_path = args.output or "aws_infrastructure"
    
    # Prepare security group options
    sg_options = {
        "flows": args.sg_flows,
        "direction": args.sg_direction,
        "detail": args.sg_detail,
        "filter_internal": args.sg_filter_internal,
        "filter_ephemeral": args.sg_filter_ephemeral,
        "only_ingress": args.sg_only_ingress
    }
    
    # Prepare load balancer options
    lb_options = {
        "display": args.lb_display,
        "detail": args.lb_detail,
        "filter_unhealthy": args.lb_filter_unhealthy
    }
    
    result = generator.generate_diagram(
        account_info=account_info,
        vpcs=resources.get("vpcs", []),
        subnets=resources.get("subnets", []),
        instances=resources.get("instances", []),
        load_balancers=resources.get("load_balancers", []),
        rds_instances=resources.get("rds_instances", []),
        security_groups=resources.get("security_groups", {}),
        route53_zones=resources.get("route53_zones", []),
        regions=args.regions,
        output_path=output_path,
        sg_options=sg_options,
        lb_options=lb_options
    )
    
    if result:
        print(f"DOT diagram generated successfully:")
        for file_type, path in result.items():
            if path:
                print(f"  {file_type.upper()}: {path}")
    else:
        print(f"Error generating diagram")
        sys.exit(1)


def main():
    # Get default region from environment variable or fallback to us-east-1
    default_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    
    parser = argparse.ArgumentParser(description="AWS Infrastructure Diagram Generator")
    parser.add_argument("--regions", nargs="+", default=[default_region], 
                       help=f"AWS regions to scan (default: {default_region}). Can specify multiple: --regions us-east-1 us-west-2")
    parser.add_argument("--region", dest="regions", action="append", 
                       help="Single region (deprecated, use --regions instead)")
    parser.add_argument("--profile", help="AWS profile to use")
    parser.add_argument("--account", help="Account name/alias for diagram")
    parser.add_argument("--vpc-id", help="Specific VPC ID to diagram")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--include-route53", action="store_true", default=True, help="Include Route53 zones")
    parser.add_argument("--include-acm", action="store_true", default=True, help="Include ACM certificates")
    
    # Security Group behavior flags
    sg_group = parser.add_argument_group("Security Group Options", "Control how security group connections are displayed")
    sg_group.add_argument("--sg-flows", choices=["none", "inter-subnet", "tier-crossing", "external-only"], 
                         default="inter-subnet", help="Types of connections to show (default: inter-subnet)")
    sg_group.add_argument("--sg-direction", choices=["both", "north-south", "east-west"], 
                         default="both", help="Traffic direction filter (default: both)")
    sg_group.add_argument("--sg-detail", choices=["minimal", "ports", "protocols", "full"], 
                         default="ports", help="Connection label detail level (default: ports)")
    sg_group.add_argument("--sg-filter-internal", action="store_true", 
                         help="Hide same-subnet internal connections")
    sg_group.add_argument("--sg-filter-ephemeral", action="store_true", 
                         help="Hide high ephemeral ports (>32768)")
    sg_group.add_argument("--sg-only-ingress", action="store_true", 
                         help="Only show ingress rules (ignore egress)")
    sg_group.add_argument("--sg-preset", choices=["clean", "network", "security", "debug"], 
                         help="Predefined security group display presets")
    
    # Load Balancer behavior flags
    lb_group = parser.add_argument_group("Load Balancer Options", "Control how load balancers are displayed")
    lb_group.add_argument("--lb-display", choices=["all", "connected-only", "none"], 
                         default="all", help="Load balancer display mode (default: all)")
    lb_group.add_argument("--lb-detail", choices=["minimal", "ports", "full"], 
                         default="ports", help="Load balancer connection label detail (default: ports)")
    lb_group.add_argument("--lb-filter-unhealthy", action="store_true", 
                         help="Hide connections to unhealthy targets")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover AWS resources")
    
    # Mermaid command
    mermaid_parser = subparsers.add_parser("mermaid", help="Generate Mermaid diagram")
    
    # DOT command  
    dot_parser = subparsers.add_parser("dot", help="Generate DOT/Graphviz diagram")
    dot_parser.add_argument("--format", choices=["png", "svg", "pdf", "dot"], default="png",
                           help="Output format (default: png)")
    
    args = parser.parse_args()
    
    # Handle legacy --region argument
    if hasattr(args, 'region') and args.region and args.regions == [default_region]:
        args.regions = [args.region]
    
    # Apply security group presets
    if args.sg_preset:
        apply_sg_preset(args)
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == "discover":
            discover_resources(args)
        elif args.command == "mermaid":
            generate_mermaid(args)
        elif args.command == "dot":
            generate_dot(args)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def apply_sg_preset(args):
    """Apply predefined security group and load balancer presets."""
    if args.sg_preset == "clean":
        # Clean architecture view
        args.sg_flows = "none"
        args.sg_detail = "minimal"
        args.lb_display = "none"
    elif args.sg_preset == "network":
        # Network design view
        args.sg_flows = "tier-crossing"
        args.sg_direction = "north-south"
        args.sg_detail = "ports"
        args.lb_display = "connected-only"
        args.lb_detail = "ports"
    elif args.sg_preset == "security":
        # Security audit view
        args.sg_flows = "inter-subnet"
        args.sg_detail = "full"
        args.sg_only_ingress = True
        args.lb_display = "all"
        args.lb_detail = "full"
    elif args.sg_preset == "debug":
        # Troubleshooting view
        args.sg_flows = "external-only"
        args.sg_detail = "full"
        args.sg_filter_ephemeral = True
        args.lb_display = "connected-only"
        args.lb_detail = "full"


if __name__ == "__main__":
    main()