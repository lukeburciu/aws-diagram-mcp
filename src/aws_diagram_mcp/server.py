"""FastMCP server for AWS diagram generation."""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import json

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from .aws_discovery import AWSResourceDiscovery
from .mermaid_generator import MermaidDiagramGenerator
from .diagrams_generator import DiagramsGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("aws-diagram-mcp")


class GenerateDiagramArgs(BaseModel):
    """Arguments for generating an AWS infrastructure diagram."""
    
    aws_account: str = Field(
        description="AWS account ID or alias for the diagram"
    )
    region: str = Field(
        default="us-east-1",
        description="AWS region to scan for resources"
    )
    profile: Optional[str] = Field(
        default=None,
        description="AWS CLI profile to use for authentication"
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Path to save the Mermaid diagram markdown file"
    )
    vpc_id: Optional[str] = Field(
        default=None,
        description="Specific VPC ID to diagram (optional, defaults to all VPCs)"
    )
    include_route53: bool = Field(
        default=True,
        description="Include Route53 hosted zones in the diagram"
    )
    include_acm: bool = Field(
        default=True,
        description="Include ACM certificates in the diagram"
    )


class GenerateDiagramDotArgs(BaseModel):
    """Arguments for generating an AWS infrastructure diagram in DOT/Graphviz format."""
    
    aws_account: str = Field(
        description="AWS account ID or alias for the diagram"
    )
    region: str = Field(
        default="us-east-1",
        description="AWS region to scan for resources"
    )
    profile: Optional[str] = Field(
        default=None,
        description="AWS CLI profile to use for authentication"
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Path to save the DOT diagram files (without extension)"
    )
    vpc_id: Optional[str] = Field(
        default=None,
        description="Specific VPC ID to diagram (optional, defaults to all VPCs)"
    )
    include_route53: bool = Field(
        default=True,
        description="Include Route53 hosted zones in the diagram"
    )
    include_acm: bool = Field(
        default=True,
        description="Include ACM certificates in the diagram"
    )
    output_format: str = Field(
        default="png",
        description="Output format for diagram: png, svg, pdf, or dot"
    )


class DiscoverResourcesArgs(BaseModel):
    """Arguments for discovering AWS resources."""
    
    region: str = Field(
        default="us-east-1",
        description="AWS region to scan"
    )
    profile: Optional[str] = Field(
        default=None,
        description="AWS CLI profile to use"
    )
    resource_types: List[str] = Field(
        default_factory=lambda: ["all"],
        description="Types of resources to discover: vpcs, subnets, instances, load_balancers, rds, security_groups, route53, acm, or 'all'"
    )


@mcp.tool()
async def generate_aws_diagram(args: GenerateDiagramArgs) -> Dict[str, Any]:
    """
    Generate a comprehensive AWS infrastructure diagram in Mermaid format.
    
    This tool discovers AWS resources and creates a hierarchical diagram showing:
    - VPCs, Regions, and Subnets
    - EC2 instances with IPs
    - Load balancers with target connections
    - RDS instances
    - Security group connections
    - Route53 and ACM certificates (optional)
    """
    try:
        logger.info(f"Starting diagram generation for account: {args.aws_account}")
        
        discovery = AWSResourceDiscovery(region=args.region, profile=args.profile)
        
        logger.info("Getting account information...")
        account_info = discovery.get_account_info()
        
        logger.info("Discovering VPCs...")
        vpcs = discovery.discover_vpcs()
        if args.vpc_id:
            vpcs = [vpc for vpc in vpcs if vpc["vpc_id"] == args.vpc_id]
        
        if not vpcs:
            return {
                "success": False,
                "error": f"No VPCs found{' with ID ' + args.vpc_id if args.vpc_id else ''}"
            }
        
        logger.info("Discovering subnets...")
        subnets = discovery.discover_subnets(args.vpc_id)
        
        logger.info("Discovering EC2 instances...")
        instances = discovery.discover_ec2_instances(args.vpc_id)
        
        logger.info("Discovering load balancers...")
        load_balancers = discovery.discover_load_balancers(args.vpc_id)
        
        logger.info("Discovering RDS instances...")
        rds_instances = discovery.discover_rds_instances(args.vpc_id)
        
        all_sg_ids = set()
        for instance in instances:
            all_sg_ids.update(instance.get("security_groups", []))
        for rds in rds_instances:
            all_sg_ids.update(rds.get("security_groups", []))
        
        logger.info(f"Discovering {len(all_sg_ids)} security groups...")
        security_groups = discovery.discover_security_groups(list(all_sg_ids))
        
        route53_zones = []
        if args.include_route53:
            logger.info("Discovering Route53 zones...")
            route53_zones = discovery.discover_route53_zones()
        
        acm_certificates = []
        if args.include_acm:
            logger.info("Discovering ACM certificates...")
            acm_certificates = discovery.discover_acm_certificates()
        
        logger.info("Generating Mermaid diagram...")
        generator = MermaidDiagramGenerator()
        diagram = generator.generate_diagram(
            account_info=account_info,
            vpcs=vpcs,
            subnets=subnets,
            instances=instances,
            load_balancers=load_balancers,
            rds_instances=rds_instances,
            security_groups=security_groups,
            route53_zones=route53_zones,
            region=args.region
        )
        
        output_path = args.output_path
        if not output_path:
            output_dir = Path(f"docs/as-built/{args.aws_account}")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{args.aws_account}_mermaid.md"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        generator.save_diagram(diagram, str(output_path))
        
        return {
            "success": True,
            "message": f"Diagram generated successfully",
            "output_path": str(output_path),
            "statistics": {
                "vpcs": len(vpcs),
                "subnets": len(subnets),
                "instances": len(instances),
                "load_balancers": len(load_balancers),
                "rds_instances": len(rds_instances),
                "security_groups": len(security_groups),
                "route53_zones": len(route53_zones),
                "acm_certificates": len(acm_certificates)
            },
            "diagram": diagram
        }
        
    except Exception as e:
        logger.error(f"Error generating diagram: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def discover_aws_resources(args: DiscoverResourcesArgs) -> Dict[str, Any]:
    """
    Discover AWS resources without generating a diagram.
    
    Useful for exploring what resources exist in an AWS account/region
    before generating a diagram.
    """
    try:
        discovery = AWSResourceDiscovery(region=args.region, profile=args.profile)
        resources = {}
        
        resource_types = args.resource_types
        if "all" in resource_types:
            resource_types = [
                "account", "vpcs", "subnets", "instances", 
                "load_balancers", "rds", "security_groups", 
                "route53", "acm"
            ]
        
        if "account" in resource_types:
            resources["account"] = discovery.get_account_info()
        
        if "vpcs" in resource_types:
            resources["vpcs"] = discovery.discover_vpcs()
        
        if "subnets" in resource_types:
            resources["subnets"] = discovery.discover_subnets()
        
        if "instances" in resource_types:
            resources["instances"] = discovery.discover_ec2_instances()
        
        if "load_balancers" in resource_types:
            resources["load_balancers"] = discovery.discover_load_balancers()
        
        if "rds" in resource_types:
            resources["rds_instances"] = discovery.discover_rds_instances()
        
        if "security_groups" in resource_types:
            all_sg_ids = set()
            if "instances" in resources:
                for instance in resources["instances"]:
                    all_sg_ids.update(instance.get("security_groups", []))
            if "rds_instances" in resources:
                for rds in resources["rds_instances"]:
                    all_sg_ids.update(rds.get("security_groups", []))
            
            if all_sg_ids:
                resources["security_groups"] = discovery.discover_security_groups(list(all_sg_ids))
        
        if "route53" in resource_types:
            resources["route53_zones"] = discovery.discover_route53_zones()
        
        if "acm" in resource_types:
            resources["acm_certificates"] = discovery.discover_acm_certificates()
        
        return {
            "success": True,
            "region": args.region,
            "resources": resources
        }
        
    except Exception as e:
        logger.error(f"Error discovering resources: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def validate_mermaid_syntax(diagram: str) -> Dict[str, Any]:
    """
    Validate that a Mermaid diagram has correct syntax.
    
    This performs basic syntax validation without rendering.
    """
    try:
        lines = diagram.strip().split("\n")
        
        if not lines or not lines[0].startswith("graph"):
            return {
                "valid": False,
                "error": "Diagram must start with 'graph' directive"
            }
        
        open_subgraphs = 0
        for i, line in enumerate(lines):
            if "subgraph" in line:
                open_subgraphs += 1
            elif line.strip() == "end":
                open_subgraphs -= 1
                if open_subgraphs < 0:
                    return {
                        "valid": False,
                        "error": f"Unmatched 'end' at line {i+1}"
                    }
        
        if open_subgraphs != 0:
            return {
                "valid": False,
                "error": f"Unclosed subgraph (missing {open_subgraphs} 'end' statements)"
            }
        
        return {
            "valid": True,
            "message": "Diagram syntax appears valid"
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


@mcp.tool()
async def generate_aws_diagram_dot(args: GenerateDiagramDotArgs) -> Dict[str, Any]:
    """
    Generate a comprehensive AWS infrastructure diagram in DOT/Graphviz format using Python Diagrams.
    
    This tool creates professional-looking diagrams that can be exported to PNG, SVG, PDF, or DOT formats.
    The diagrams show:
    - VPCs, Regions, and Subnets with proper clustering
    - EC2 instances with AWS icons
    - Load balancers with target connections
    - RDS instances with database icons
    - Security group connections with proper edge styling
    - Route53 and ACM certificates (optional)
    """
    try:
        logger.info(f"Starting DOT diagram generation for account: {args.aws_account}")
        
        discovery = AWSResourceDiscovery(region=args.region, profile=args.profile)
        
        logger.info("Getting account information...")
        account_info = discovery.get_account_info()
        
        logger.info("Discovering VPCs...")
        vpcs = discovery.discover_vpcs()
        if args.vpc_id:
            vpcs = [vpc for vpc in vpcs if vpc["vpc_id"] == args.vpc_id]
        
        if not vpcs:
            return {
                "success": False,
                "error": f"No VPCs found{' with ID ' + args.vpc_id if args.vpc_id else ''}"
            }
        
        logger.info("Discovering subnets...")
        subnets = discovery.discover_subnets(args.vpc_id)
        
        logger.info("Discovering EC2 instances...")
        instances = discovery.discover_ec2_instances(args.vpc_id)
        
        logger.info("Discovering load balancers...")
        load_balancers = discovery.discover_load_balancers(args.vpc_id)
        
        logger.info("Discovering RDS instances...")
        rds_instances = discovery.discover_rds_instances(args.vpc_id)
        
        all_sg_ids = set()
        for instance in instances:
            all_sg_ids.update(instance.get("security_groups", []))
        for rds in rds_instances:
            all_sg_ids.update(rds.get("security_groups", []))
        
        logger.info(f"Discovering {len(all_sg_ids)} security groups...")
        security_groups = discovery.discover_security_groups(list(all_sg_ids))
        
        route53_zones = []
        if args.include_route53:
            logger.info("Discovering Route53 zones...")
            route53_zones = discovery.discover_route53_zones()
        
        acm_certificates = []
        if args.include_acm:
            logger.info("Discovering ACM certificates...")
            acm_certificates = discovery.discover_acm_certificates()
        
        # Set up output path
        output_path = args.output_path
        if not output_path:
            output_dir = Path(f"docs/as-built/{args.aws_account}")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{args.aws_account}_diagram"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("Generating DOT diagram using Python Diagrams...")
        generator = DiagramsGenerator()
        files = generator.generate_diagram(
            account_info=account_info,
            vpcs=vpcs,
            subnets=subnets,
            instances=instances,
            load_balancers=load_balancers,
            rds_instances=rds_instances,
            security_groups=security_groups,
            route53_zones=route53_zones,
            region=args.region,
            output_path=str(output_path)
        )
        
        generator.save_diagram_metadata(files, str(output_path))
        
        return {
            "success": True,
            "message": f"DOT diagram generated successfully",
            "output_files": files,
            "output_format": args.output_format,
            "statistics": {
                "vpcs": len(vpcs),
                "subnets": len(subnets),
                "instances": len(instances),
                "load_balancers": len(load_balancers),
                "rds_instances": len(rds_instances),
                "security_groups": len(security_groups),
                "route53_zones": len(route53_zones),
                "acm_certificates": len(acm_certificates)
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating DOT diagram: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def serve():
    """Run the MCP server."""
    asyncio.run(mcp.run())


if __name__ == "__main__":
    serve()