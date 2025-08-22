#!/usr/bin/env python3
"""
Cloud Infrastructure Diagram CLI Tool
Modern CLI for discovering cloud resources and generating architecture diagrams.
"""

import argparse
import json
import sys
import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

from .providers import get_provider, list_providers
from .config import load_config


# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CloudDiagramCLI:
    """Modern CLI for cloud diagram generation."""
    
    def __init__(self):
        self.discovery = None
        self.diagram_class = None
        self.args = None
    
    def setup_provider(self, provider: str, region: str, profile: Optional[str] = None):
        """Initialize the provider discovery and diagram classes."""
        try:
            self.discovery, self.diagram_class = get_provider(
                provider, 
                region=region, 
                profile=profile
            )
            if self.args and self.args.verbose:
                print(f"✓ Connected to {provider.upper()} in region {region}")
        except Exception as e:
            logger.error(f"Failed to setup provider {provider}: {e}")
            print(f"Error: Failed to connect to {provider}: {e}")
            sys.exit(1)
    
    def list_services(self) -> int:
        """List available services for the current provider."""
        if not self.discovery:
            print("Error: No provider configured")
            return 1
        
        if hasattr(self.discovery, 'list_available_snippets'):
            available = self.discovery.list_available_snippets()
            
            print("Available services:")
            for service, resource_types in available.items():
                print(f"  {service}:")
                for resource_type in resource_types:
                    print(f"    - {resource_type}")
            return 0
        else:
            print("Error: Provider does not support modular discovery")
            return 1
    
    def list_resources(self, service: Optional[str] = None) -> int:
        """List available resource types for a service."""
        if not self.discovery:
            print("Error: No provider configured")
            return 1
        
        if hasattr(self.discovery, 'list_available_snippets'):
            available = self.discovery.list_available_snippets()
            
            if service:
                if service in available:
                    print(f"Available resource types for {service}:")
                    for resource_type in available[service]:
                        print(f"  - {resource_type}")
                else:
                    print(f"Error: Service '{service}' not found")
                    print(f"Available services: {', '.join(available.keys())}")
                    return 1
            else:
                return self.list_services()
            
            return 0
        else:
            print("Error: Provider does not support modular discovery")
            return 1
    
    def discover_resources(
        self, 
        service: Optional[str] = None, 
        resource_type: Optional[str] = None,
        output_format: str = 'json',
        output_file: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Discover cloud resources."""
        if not self.discovery:
            print("Error: No provider configured")
            return 1
        
        if not hasattr(self.discovery, 'discover_resources'):
            print("Error: Provider does not support modular discovery")
            return 1
        
        if self.args.verbose:
            print(f"Discovering resources...")
            if service:
                print(f"  Service: {service}")
            if resource_type:
                print(f"  Resource Type: {resource_type}")
        
        try:
            # Collect resources
            resources = defaultdict(lambda: defaultdict(list))
            total_count = 0
            
            # Show progress in verbose mode
            if self.args.verbose:
                print("  Scanning...")
            
            for resource in self.discovery.discover_resources(service, resource_type):
                # Apply basic filters
                if filters and not self._apply_filters(resource, filters):
                    continue
                
                # Parse resource type (e.g., 'aws.ec2.instance' -> service='ec2', type='instance')
                parts = resource.type.split('.')
                if len(parts) >= 3:
                    svc = parts[1]
                    rtype = parts[2]
                else:
                    svc = service or 'unknown'
                    rtype = resource_type or 'unknown'
                
                resources[svc][rtype].append(resource.to_dict())
                total_count += 1
                
                if self.args.verbose and total_count % 10 == 0:
                    print(f"    Found {total_count} resources...")
            
            # Output results
            result = dict(resources)
            
            if self.args.verbose or not self.args.quiet:
                print(f"\nDiscovered {total_count} resources:")
                for svc, rtypes in result.items():
                    for rtype, items in rtypes.items():
                        print(f"  {svc}.{rtype}: {len(items)}")
            
            # Format and output
            if output_format == 'json':
                output_data = json.dumps(result, indent=2, default=str)
            elif output_format == 'yaml':
                try:
                    import yaml
                    output_data = yaml.dump(result, default_flow_style=False)
                except ImportError:
                    print("Error: PyYAML not installed for YAML output")
                    return 1
            elif output_format == 'table':
                output_data = self._format_table(result)
            else:
                print(f"Error: Unsupported output format '{output_format}'")
                return 1
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(output_data)
                if not self.args.quiet:
                    print(f"\nOutput saved to: {output_file}")
            else:
                if output_format != 'table' or self.args.quiet:
                    print()  # Add spacing
                print(output_data)
            
            return 0
            
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            print(f"Error during discovery: {e}")
            return 1
    
    def _apply_filters(self, resource, filters: Dict[str, Any]) -> bool:
        """Apply filters to a resource."""
        # VPC filter
        if 'vpc_id' in filters and filters['vpc_id']:
            if resource.vpc_id != filters['vpc_id']:
                return False
        
        # Tag filters
        if 'tags' in filters and filters['tags']:
            resource_tags = resource.tags or {}
            for tag_filter in filters['tags']:
                if '=' in tag_filter:
                    key, value = tag_filter.split('=', 1)
                    if resource_tags.get(key) != value:
                        return False
                else:
                    if tag_filter not in resource_tags:
                        return False
        
        return True
    
    def _format_table(self, resources: Dict[str, Dict[str, List[Dict]]]) -> str:
        """Format resources as a table."""
        lines = []
        lines.append(f"{'Service':<12} {'Type':<16} {'Count':<8} {'Resources'}")
        lines.append("-" * 70)
        
        for service, rtypes in resources.items():
            for rtype, items in rtypes.items():
                names = [item.get('name', item.get('id', 'Unknown'))[:20] for item in items[:3]]
                if len(items) > 3:
                    names.append(f"... +{len(items) - 3} more")
                
                resource_list = ", ".join(names)
                lines.append(f"{service:<12} {rtype:<16} {len(items):<8} {resource_list}")
        
        return "\n".join(lines)
    
    def generate_diagram(
        self,
        output: str = "infrastructure",
        format: str = "png",
        services: Optional[List[str]] = None,
        preset: Optional[str] = None,
        config_file: Optional[str] = None
    ) -> int:
        """Generate infrastructure diagram."""
        if not self.discovery or not self.diagram_class:
            print("Error: No provider configured")
            return 1
        
        try:
            if self.args.verbose:
                print("Generating diagram...")
                print(f"  Output: {output}.{format}")
                if services:
                    print(f"  Services: {', '.join(services)}")
                if preset:
                    print(f"  Preset: {preset}")
            
            # Load configuration
            config = load_config(
                self.args.provider, 
                config_file, 
                output_format=format
            )
            
            # Apply preset configurations
            if preset:
                config = self._apply_preset(config, preset)
            
            # Discover resources for diagram
            if self.args.verbose:
                print("  Discovering resources...")
            
            resources = defaultdict(list)
            total_count = 0
            
            for resource in self.discovery.discover_resources():
                # Filter by services if specified
                if services:
                    resource_service = resource.type.split('.')[1] if '.' in resource.type else None
                    if resource_service not in services:
                        continue
                
                # Group by resource type for diagram generator
                resource_key = self._get_diagram_resource_key(resource.type)
                if resource_key:
                    resources[resource_key].append(resource.to_dict())
                    total_count += 1
            
            if self.args.verbose:
                print(f"  Using {total_count} resources for diagram")
            
            # Generate diagram
            generator = self.diagram_class()
            account_info = self.discovery.get_account_info()
            
            result = generator.generate_diagram(
                account_info=account_info,
                vpcs=resources.get('vpcs', []),
                subnets=resources.get('subnets', []),
                instances=resources.get('instances', []),
                load_balancers=resources.get('load_balancers', []),
                rds_instances=resources.get('rds_instances', []),
                security_groups=resources.get('security_groups', {}),
                route53_zones=resources.get('route53_zones', []),
                region=self.discovery.aws_client.region if hasattr(self.discovery, 'aws_client') else 'unknown',
                output_path=output
            )
            
            if result:
                if not self.args.quiet:
                    print(f"\n✓ Diagram generated successfully:")
                    for file_type, path in result.items():
                        if path:
                            print(f"  {file_type.upper()}: {path}")
                return 0
            else:
                print("Error: Diagram generation failed")
                return 1
                
        except Exception as e:
            logger.error(f"Diagram generation failed: {e}")
            print(f"Error generating diagram: {e}")
            return 1
    
    def _get_diagram_resource_key(self, resource_type: str) -> Optional[str]:
        """Map resource type to diagram generator key."""
        # Map from snippet resource types to diagram generator expected keys
        mapping = {
            'aws.ec2.vpc': 'vpcs',
            'aws.ec2.subnet': 'subnets',
            'aws.ec2.instance': 'instances',
            'aws.ec2.security_group': 'security_groups',
            'aws.elb.alb': 'load_balancers',
            'aws.elb.nlb': 'load_balancers',
            'aws.elb.classic': 'load_balancers',
            'aws.rds.db_instance': 'rds_instances',
            'aws.route53.hosted_zone': 'route53_zones',
            'aws.acm.certificate': 'certificates'
        }
        return mapping.get(resource_type)
    
    def _apply_preset(self, config: Dict[str, Any], preset: str) -> Dict[str, Any]:
        """Apply diagram preset configurations."""
        presets = {
            'clean': {
                'security_groups': {'show_connections': False},
                'load_balancers': {'show_connections': False}
            },
            'network': {
                'security_groups': {'show_connections': True, 'connection_detail': 'ports'},
                'load_balancers': {'show_connections': True}
            },
            'security': {
                'security_groups': {'show_connections': True, 'connection_detail': 'full'},
                'load_balancers': {'show_connections': True, 'show_health': True}
            }
        }
        
        if preset in presets:
            # Merge preset config with existing config
            preset_config = presets[preset]
            for key, value in preset_config.items():
                if key in config:
                    config[key].update(value)
                else:
                    config[key] = value
        
        return config


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Cloud Infrastructure Diagram Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s discover                           # Discover all resources
  %(prog)s discover ec2                       # Discover EC2 resources
  %(prog)s discover ec2 instances             # Discover EC2 instances only
  %(prog)s discover --tags Environment=prod   # Filter by tags
  %(prog)s list-services                      # Show available services
  %(prog)s list-resources ec2                 # Show EC2 resource types
  %(prog)s diagram --output infra.png         # Generate diagram
  %(prog)s diagram --services ec2,rds         # Diagram specific services
        """
    )
    
    # Global options
    parser.add_argument('--provider', choices=list_providers(), default='aws',
                       help='Cloud provider (default: aws)')
    parser.add_argument('--region', default=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'),
                       help='Cloud region (default: from AWS_DEFAULT_REGION or us-east-1)')
    parser.add_argument('--profile', help='Authentication profile')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List services command
    list_services_parser = subparsers.add_parser('list-services', help='List available services')
    
    # List resources command
    list_resources_parser = subparsers.add_parser('list-resources', help='List available resource types')
    list_resources_parser.add_argument('service', nargs='?', help='Service name (optional)')
    
    # Discover command
    discover_parser = subparsers.add_parser('discover', help='Discover cloud resources')
    discover_parser.add_argument('service', nargs='?', help='Service to discover (e.g., ec2, rds)')
    discover_parser.add_argument('resource_type', nargs='?', help='Resource type (e.g., instances, vpc)')
    discover_parser.add_argument('--output', choices=['json', 'yaml', 'table'], default='json',
                                help='Output format (default: json)')
    discover_parser.add_argument('--output-file', help='Save output to file')
    discover_parser.add_argument('--vpc-id', help='Filter by VPC ID')
    discover_parser.add_argument('--tags', nargs='+', help='Filter by tags (key=value or key)')
    
    # Diagram command
    diagram_parser = subparsers.add_parser('diagram', help='Generate infrastructure diagram')
    diagram_parser.add_argument('--output', default='infrastructure', help='Output file name (without extension)')
    diagram_parser.add_argument('--format', choices=['png', 'svg', 'pdf', 'dot'], default='png',
                               help='Output format (default: png)')
    diagram_parser.add_argument('--services', nargs='+', help='Specific services to include')
    diagram_parser.add_argument('--preset', choices=['clean', 'network', 'security'],
                               help='Diagram preset configuration')
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger('cloud_diagram').setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    # Validate arguments
    if not args.command:
        parser.print_help()
        return 1
    
    if args.verbose and args.quiet:
        print("Error: Cannot use both --verbose and --quiet")
        return 1
    
    # Initialize CLI
    cli = CloudDiagramCLI()
    cli.args = args
    
    # Commands that don't need provider setup
    if args.command == 'list-services':
        # Need provider for service listing
        cli.setup_provider(args.provider, args.region, args.profile)
        return cli.list_services()
    elif args.command == 'list-resources':
        cli.setup_provider(args.provider, args.region, args.profile)
        return cli.list_resources(getattr(args, 'service', None))
    
    # Setup provider for other commands
    cli.setup_provider(args.provider, args.region, args.profile)
    
    # Route to appropriate command
    try:
        if args.command == 'discover':
            filters = {}
            if args.vpc_id:
                filters['vpc_id'] = args.vpc_id
            if args.tags:
                filters['tags'] = args.tags
            
            return cli.discover_resources(
                service=args.service,
                resource_type=args.resource_type,
                output_format=args.output,
                output_file=args.output_file,
                filters=filters
            )
        
        elif args.command == 'diagram':
            return cli.generate_diagram(
                output=args.output,
                format=args.format,
                services=args.services,
                preset=args.preset,
                config_file=args.config
            )
        
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())