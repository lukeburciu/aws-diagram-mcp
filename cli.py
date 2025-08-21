#!/usr/bin/env python3
"""
Standalone CLI for AWS Infrastructure Diagram Generation
Run AWS discovery and generate diagrams without MCP/LLM.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from src.aws_diagram_mcp.aws_discovery import AWSResourceDiscovery
from src.aws_diagram_mcp.mermaid_generator import MermaidDiagramGenerator
from src.aws_diagram_mcp.diagrams_generator import DiagramsGenerator


def discover_resources(args):
    """Discover AWS resources and print as JSON."""
    discovery = AWSResourceDiscovery(region=args.region, profile=args.profile)
    
    print(f"Discovering AWS resources in {args.region}...")
    
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
    
    # Get all security groups from instances, load balancers, and RDS
    all_sg_ids = set()
    for instance in resources["instances"]:
        all_sg_ids.update(instance.get("security_groups", []))
    for rds in resources["rds_instances"]:
        all_sg_ids.update(rds.get("security_groups", []))
    
    resources["security_groups"] = discovery.discover_security_groups(list(all_sg_ids))
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
    discovery = AWSResourceDiscovery(region=args.region, profile=args.profile)
    generator = MermaidDiagramGenerator()
    
    print(f"Generating Mermaid diagram for {args.region}...")
    
    # Discover resources
    resources = {
        "instances": discovery.discover_ec2_instances(vpc_id=args.vpc_id),
        "load_balancers": discovery.discover_load_balancers(vpc_id=args.vpc_id),
        "rds_instances": discovery.discover_rds_instances(vpc_id=args.vpc_id),
        "subnets": discovery.discover_subnets(vpc_id=args.vpc_id),
        "vpcs": discovery.discover_vpcs() if not args.vpc_id else []
    }
    
    # Get security groups from resources
    all_sg_ids = set()
    for instance in resources["instances"]:
        all_sg_ids.update(instance.get("security_groups", []))
    for rds in resources["rds_instances"]:
        all_sg_ids.update(rds.get("security_groups", []))
    resources["security_groups"] = discovery.discover_security_groups(list(all_sg_ids))
    
    if args.include_route53:
        resources["route53_zones"] = discovery.discover_route53_zones()
    
    if args.include_acm:
        resources["certificates"] = discovery.discover_acm_certificates()
    
    # Generate diagram
    account_info = discovery.get_account_info()
    diagram = generator.generate_mermaid_diagram(
        resources=resources,
        account_name=args.account or account_info.get('account_id', 'Unknown'),
        vpc_id=args.vpc_id
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
    discovery = AWSResourceDiscovery(region=args.region, profile=args.profile)
    generator = DiagramsGenerator()
    
    print(f"Generating DOT diagram for {args.region}...")
    
    # Discover resources
    resources = {
        "instances": discovery.discover_ec2_instances(vpc_id=args.vpc_id),
        "load_balancers": discovery.discover_load_balancers(vpc_id=args.vpc_id),
        "rds_instances": discovery.discover_rds_instances(vpc_id=args.vpc_id),
        "subnets": discovery.discover_subnets(vpc_id=args.vpc_id),
        "vpcs": discovery.discover_vpcs() if not args.vpc_id else []
    }
    
    # Get security groups from resources
    all_sg_ids = set()
    for instance in resources["instances"]:
        all_sg_ids.update(instance.get("security_groups", []))
    for rds in resources["rds_instances"]:
        all_sg_ids.update(rds.get("security_groups", []))
    resources["security_groups"] = discovery.discover_security_groups(list(all_sg_ids))
    
    if args.include_route53:
        resources["route53_zones"] = discovery.discover_route53_zones()
    
    if args.include_acm:
        resources["certificates"] = discovery.discover_acm_certificates()
    
    # Generate diagram
    account_info = discovery.get_account_info()
    output_path = args.output or "aws_infrastructure"
    
    result = generator.generate_diagram(
        account_info=account_info,
        vpcs=resources.get("vpcs", []),
        subnets=resources.get("subnets", []),
        instances=resources.get("instances", []),
        load_balancers=resources.get("load_balancers", []),
        rds_instances=resources.get("rds_instances", []),
        security_groups=resources.get("security_groups", {}),
        route53_zones=resources.get("route53_zones", []),
        region=args.region,
        output_path=output_path
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
    parser.add_argument("--region", default=default_region, help=f"AWS region (default: {default_region})")
    parser.add_argument("--profile", help="AWS profile to use")
    parser.add_argument("--account", help="Account name/alias for diagram")
    parser.add_argument("--vpc-id", help="Specific VPC ID to diagram")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--include-route53", action="store_true", default=True, help="Include Route53 zones")
    parser.add_argument("--include-acm", action="store_true", default=True, help="Include ACM certificates")
    
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


if __name__ == "__main__":
    main()