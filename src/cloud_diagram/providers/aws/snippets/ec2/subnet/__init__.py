"""Subnet snippet for diagram generation."""

from typing import Dict, Any, Optional, Iterator
from diagrams.aws.network import PrivateSubnet, PublicSubnet
from diagrams import Edge

from ...base import ConfiguredSnippet
from ....utils.discovery import Resource, AWSClient


class SubnetSnippet(ConfiguredSnippet):
    """Snippet for rendering Subnets in diagrams."""
    
    def __init__(
        self,
        service: str = 'ec2',
        resource_type: str = 'subnet',
        config_loader=None,
        cli_overrides: Optional[Dict[str, Any]] = None
    ):
        """Initialize Subnet snippet."""
        super().__init__(service, resource_type, config_loader, cli_overrides)
    
    def create_node(self, subnet: Dict[str, Any]) -> Any:
        """Create a diagram node for a Subnet."""
        # Get the appropriate icon class
        icon_class = self._get_icon_class(subnet)
        
        # Generate the label
        label = self._generate_label(subnet)
        
        # Create and return the node
        return icon_class(label)
    
    def _get_icon_class(self, subnet: Dict[str, Any]) -> type:
        """Get the appropriate icon class for the subnet tier."""
        icon_style = self.get_config_value('visual.icon_style', 'tier_specific')
        
        if icon_style == 'generic':
            return PrivateSubnet
        
        tier = subnet.get('tier', 'private').lower()
        
        if tier == 'public':
            return PublicSubnet
        else:
            return PrivateSubnet
    
    def _generate_label(self, subnet: Dict[str, Any]) -> str:
        """Generate label for Subnet based on configuration."""
        # Extract subnet properties
        subnet_id = subnet.get('subnet_id', 'Unknown')
        name = subnet.get('name', subnet_id)
        cidr_block = subnet.get('cidr_block', '')
        availability_zone = subnet.get('availability_zone', '')
        state = subnet.get('state', '')
        vpc_id = subnet.get('vpc_id', '')
        tier = subnet.get('tier', '')
        map_public_ip = subnet.get('map_public_ip_on_launch', False)
        available_ips = subnet.get('available_ip_address_count', 0)
        
        # Build label parts
        label_parts = []
        
        # Primary label
        primary_template = self.get_config_value('label.primary_format', '{name}')
        primary_label = primary_template.format(
            name=name,
            id=subnet_id,
            cidr_block=cidr_block,
            az=availability_zone,
            state=state,
            vpc_id=vpc_id,
            tier=tier.title() if tier else ''
        )
        label_parts.append(primary_label)
        
        # Secondary label
        if self.get_config_value('display.show_cidr_block', True) and cidr_block:
            secondary_template = self.get_config_value('label.secondary_format', '{cidr_block}')
            secondary_label = secondary_template.format(cidr_block=cidr_block)
            if secondary_label and secondary_label != primary_label:
                label_parts.append(secondary_label)
        
        # Tertiary label
        if self.get_config_value('display.show_availability_zone', True) and availability_zone:
            tertiary_template = self.get_config_value('label.tertiary_format', '{az}')
            tertiary_label = tertiary_template.format(az=availability_zone)
            if tertiary_label and tertiary_label not in label_parts:
                label_parts.append(tertiary_label)
        
        # Build additional attributes based on config
        additional = []
        
        if self.get_config_value('display.show_tier', True) and tier:
            additional.append(f"{tier.title()} Subnet")
        
        if self.get_config_value('display.show_map_public_ip', True) and map_public_ip:
            additional.append("Auto-assign Public IP")
        
        if self.get_config_value('display.show_available_ips', False) and available_ips:
            additional.append(f"{available_ips} IPs")
        
        if self.get_config_value('display.show_state', False) and state:
            additional.append(f"State: {state}")
        
        # Combine labels with newlines
        final_label = '\\n'.join(label_parts)
        
        # Add additional info in parentheses
        if additional:
            final_label += f"\\n({', '.join(additional)})"
        
        # Apply max length limit
        max_length = self.get_config_value('label.max_label_length', 50)
        if len(final_label) > max_length:
            truncate_style = self.get_config_value('label.truncate_style', 'ellipsis')
            if truncate_style == 'ellipsis':
                final_label = final_label[:max_length-3] + '...'
        
        return final_label
    
    def _determine_subnet_tier(self, subnet: Dict[str, Any]) -> str:
        """Determine subnet tier based on name and configuration rules."""
        name = subnet.get('name', '').lower()
        tier_rules = self.get_config_value('tier_rules', {})
        
        # Check each tier
        for tier, patterns in tier_rules.items():
            for pattern in patterns:
                if pattern.replace('*', '') in name:
                    return tier
        
        # Default to private if no pattern matches
        return 'private'
    
    def create_connection(
        self,
        from_node: Any,
        to_node: Any,
        connection_info: Dict[str, Any]
    ) -> Edge:
        """Create a connection edge with Subnet-specific styling."""
        # Extract connection details
        connection_type = connection_info.get('type', 'route')
        
        # Generate label
        label_format = self.get_config_value('connections.connection_label_format', '{type}')
        label = label_format.format(type=connection_type)
        
        # Style based on connection type
        if connection_type == 'route_table':
            return Edge(label=label, style="solid", color="blue")
        elif connection_type == 'nat_gateway':
            return Edge(label=label, style="solid", color="orange")
        else:
            return Edge(label=label)
    
    def should_render(self, subnet: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Determine if this Subnet should be rendered based on filters."""
        # Use parent class basic filtering
        if not super().should_render(subnet, filters):
            return False
        
        # Check subnet state
        state = subnet.get('state', '').lower()
        excluded_states = self.get_config_value('filters.exclude_states', ['deleted'])
        if state in excluded_states:
            return False
        
        # Check tier filters
        tier = subnet.get('tier', 'private')
        exclude_tiers = self.get_config_value('filters.exclude_tiers', [])
        include_only_tiers = self.get_config_value('filters.include_only_tiers', [])
        
        if exclude_tiers and tier in exclude_tiers:
            return False
        
        if include_only_tiers and tier not in include_only_tiers:
            return False
        
        # Check availability zone filters
        az = subnet.get('availability_zone', '')
        exclude_azs = self.get_config_value('filters.exclude_availability_zones', [])
        include_only_azs = self.get_config_value('filters.include_only_availability_zones', [])
        
        if exclude_azs and az in exclude_azs:
            return False
        
        if include_only_azs and az not in include_only_azs:
            return False
        
        # Check CIDR filters
        cidr_block = subnet.get('cidr_block', '')
        exclude_cidrs = self.get_config_value('filters.exclude_cidrs', [])
        include_only_cidrs = self.get_config_value('filters.include_only_cidrs', [])
        
        if exclude_cidrs and any(excluded in cidr_block for excluded in exclude_cidrs):
            return False
        
        if include_only_cidrs and not any(included in cidr_block for included in include_only_cidrs):
            return False
        
        # Check available IPs filters
        available_ips = subnet.get('available_ip_address_count', 0)
        min_ips = self.get_config_value('filters.min_available_ips')
        max_ips = self.get_config_value('filters.max_available_ips')
        
        if min_ips is not None and available_ips < min_ips:
            return False
        if max_ips is not None and available_ips > max_ips:
            return False
        
        return True
    
    def get_cluster_info(self, subnet: Dict[str, Any]) -> Dict[str, str]:
        """Get clustering information for this Subnet."""
        cluster_by = self.get_config_value('clustering.group_by', 'availability_zone')
        
        if cluster_by == 'none':
            return {
                'cluster_type': 'none',
                'cluster_id': '',
                'cluster_label': ''
            }
        elif cluster_by == 'availability_zone':
            az = subnet.get('availability_zone', 'unknown-az')
            label_template = self.get_config_value('clustering.cluster_label_format', '{type}: {name}')
            return {
                'cluster_type': 'availability_zone',
                'cluster_id': az,
                'cluster_label': label_template.format(type='AZ', name=az)
            }
        elif cluster_by == 'vpc':
            vpc_id = subnet.get('vpc_id', 'default-vpc')
            return {
                'cluster_type': 'vpc',
                'cluster_id': vpc_id,
                'cluster_label': f'VPC: {vpc_id}'
            }
        elif cluster_by == 'tier':
            tier = subnet.get('tier', 'private')
            return {
                'cluster_type': 'tier',
                'cluster_id': tier,
                'cluster_label': f'{tier.title()} Subnets'
            }
        
        return {
            'cluster_type': 'none',
            'cluster_id': '',
            'cluster_label': ''
        }
    
    def get_label_variables(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Get Subnet-specific variables for label formatting."""
        return {
            'cidr_block': resource.get('cidr_block', ''),
            'az': resource.get('availability_zone', ''),
            'state': resource.get('state', ''),
            'vpc_id': resource.get('vpc_id', ''),
            'tier': resource.get('tier', ''),
            'available_ips': resource.get('available_ip_address_count', '')
        }
    
    def get_metadata(self, subnet: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for tooltips or additional info."""
        return {
            'subnet_id': subnet.get('subnet_id'),
            'cidr_block': subnet.get('cidr_block'),
            'availability_zone': subnet.get('availability_zone'),
            'state': subnet.get('state'),
            'vpc_id': subnet.get('vpc_id'),
            'tier': subnet.get('tier'),
            'map_public_ip_on_launch': subnet.get('map_public_ip_on_launch'),
            'available_ip_address_count': subnet.get('available_ip_address_count'),
            'tags': subnet.get('tags', {}),
            'owner_id': subnet.get('owner_id')
        }


def list_resources(aws_client: AWSClient, config: Dict[str, Any]) -> Iterator[Resource]:
    """
    Discover Subnets in the configured region.
    
    Args:
        aws_client: Configured AWS client manager
        config: Snippet configuration for filtering
        
    Yields:
        Resource objects representing Subnets
    """
    # Get filter configuration
    exclude_states = config.get('filters', {}).get('exclude_states', ['deleted'])
    exclude_tiers = config.get('filters', {}).get('exclude_tiers', [])
    include_only_tiers = config.get('filters', {}).get('include_only_tiers', [])
    exclude_azs = config.get('filters', {}).get('exclude_availability_zones', [])
    include_only_azs = config.get('filters', {}).get('include_only_availability_zones', [])
    exclude_cidrs = config.get('filters', {}).get('exclude_cidrs', [])
    include_only_cidrs = config.get('filters', {}).get('include_only_cidrs', [])
    min_ips = config.get('filters', {}).get('min_available_ips')
    max_ips = config.get('filters', {}).get('max_available_ips')
    tier_rules = config.get('tier_rules', {})
    
    def determine_subnet_tier(name: str) -> str:
        """Determine subnet tier based on name patterns."""
        name_lower = name.lower()
        for tier, patterns in tier_rules.items():
            for pattern in patterns:
                if pattern.replace('*', '') in name_lower:
                    return tier
        return 'private'
    
    for page in aws_client.paginate('ec2', 'describe_subnets'):
        for subnet in page.get('Subnets', []):
            # Apply state filters
            state = subnet.get('State', '').lower()
            if state in exclude_states:
                continue
            
            # Extract basic info
            id_key = 'SubnetId'
            subnet_id = subnet[id_key]
            
            # Process tags
            tags = aws_client.process_tags(subnet.get('Tags', []))
            subnet_name = aws_client.get_tag_value(subnet.get('Tags', []), 'Name', subnet_id)
            
            # Determine tier
            tier = determine_subnet_tier(subnet_name)
            
            # Apply tier filters
            if exclude_tiers and tier in exclude_tiers:
                continue
            if include_only_tiers and tier not in include_only_tiers:
                continue
            
            # Apply AZ filters
            az = subnet.get('AvailabilityZone', '')
            if exclude_azs and az in exclude_azs:
                continue
            if include_only_azs and az not in include_only_azs:
                continue
            
            # Apply CIDR filters
            cidr_block = subnet.get('CidrBlock', '')
            if exclude_cidrs and any(excluded in cidr_block for excluded in exclude_cidrs):
                continue
            if include_only_cidrs and not any(included in cidr_block for included in include_only_cidrs):
                continue
            
            # Apply available IPs filters
            available_ips = subnet.get('AvailableIpAddressCount', 0)
            if min_ips is not None and available_ips < min_ips:
                continue
            if max_ips is not None and available_ips > max_ips:
                continue
            
            yield Resource(
                type='aws.ec2.subnet',
                id=subnet_id,
                id_key=id_key,
                _raw=subnet,
                # Normalized fields for diagram generation
                name=subnet_name,
                state=state,
                vpc_id=subnet.get('VpcId'),
                tags=tags,
                # Subnet-specific fields
                subnet_id=subnet_id,
                cidr_block=cidr_block,
                availability_zone=az,
                tier=tier,
                map_public_ip_on_launch=subnet.get('MapPublicIpOnLaunch', False),
                available_ip_address_count=available_ips,
                default_for_az=subnet.get('DefaultForAz', False),
                owner_id=subnet.get('OwnerId')
            )