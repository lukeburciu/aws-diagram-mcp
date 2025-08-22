"""VPC snippet for diagram generation."""

from typing import Dict, Any, Optional, Iterator
from diagrams.aws.network import VPC
from diagrams import Edge

from ...base import ConfiguredSnippet
from ....utils.discovery import Resource, AWSClient


class VPCSnippet(ConfiguredSnippet):
    """Snippet for rendering VPCs in diagrams."""
    
    def __init__(
        self,
        service: str = 'ec2',
        resource_type: str = 'vpc',
        config_loader=None,
        cli_overrides: Optional[Dict[str, Any]] = None
    ):
        """Initialize VPC snippet."""
        super().__init__(service, resource_type, config_loader, cli_overrides)
    
    def create_node(self, vpc: Dict[str, Any]) -> Any:
        """Create a diagram node for a VPC."""
        # Generate the label
        label = self._generate_label(vpc)
        
        # Create and return the node
        return VPC(label)
    
    def _generate_label(self, vpc: Dict[str, Any]) -> str:
        """Generate label for VPC based on configuration."""
        # Extract VPC properties
        vpc_id = vpc.get('vpc_id', 'Unknown')
        name = vpc.get('name', vpc_id)
        cidr_block = vpc.get('cidr_block', '')
        state = vpc.get('state', '')
        is_default = vpc.get('is_default', False)
        region = vpc.get('region', '')
        
        # Build label parts
        label_parts = []
        
        # Primary label
        primary_template = self.get_config_value('label.primary_format', '{name}')
        primary_label = primary_template.format(
            name=name,
            id=vpc_id,
            cidr_block=cidr_block,
            state=state,
            is_default='(Default)' if is_default else '',
            region=region
        )
        label_parts.append(primary_label)
        
        # Secondary label
        if self.get_config_value('display.show_cidr_block', True) and cidr_block:
            secondary_template = self.get_config_value('label.secondary_format', '{cidr_block}')
            secondary_label = secondary_template.format(cidr_block=cidr_block)
            if secondary_label and secondary_label != primary_label:
                label_parts.append(secondary_label)
        
        # Tertiary label
        tertiary_template = self.get_config_value('label.tertiary_format', '')
        if tertiary_template:
            tertiary_label = tertiary_template.format(
                name=name,
                id=vpc_id,
                cidr_block=cidr_block,
                state=state,
                is_default='(Default)' if is_default else '',
                region=region
            )
            if tertiary_label and tertiary_label not in label_parts:
                label_parts.append(tertiary_label)
        
        # Build additional attributes based on config
        additional = []
        
        if self.get_config_value('display.show_is_default', True) and is_default:
            additional.append("Default VPC")
        
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
    
    def create_connection(
        self,
        from_node: Any,
        to_node: Any,
        connection_info: Dict[str, Any]
    ) -> Edge:
        """Create a connection edge with VPC-specific styling."""
        # Extract connection details
        connection_type = connection_info.get('type', 'peering')
        
        # Generate label
        label_format = self.get_config_value('connections.connection_label_format', '{type}')
        label = label_format.format(type=connection_type)
        
        # Style based on connection type
        if connection_type == 'peering':
            return Edge(label=label, style="dashed", color="blue")
        elif connection_type == 'internet_gateway':
            return Edge(label=label, style="solid", color="green")
        elif connection_type == 'nat_gateway':
            return Edge(label=label, style="solid", color="orange")
        else:
            return Edge(label=label)
    
    def should_render(self, vpc: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Determine if this VPC should be rendered based on filters."""
        # Use parent class basic filtering
        if not super().should_render(vpc, filters):
            return False
        
        # Check VPC state
        state = vpc.get('state', '').lower()
        excluded_states = self.get_config_value('filters.exclude_states', ['deleted'])
        if state in excluded_states:
            return False
        
        # Check default VPC filters
        is_default = vpc.get('is_default', False)
        exclude_default = self.get_config_value('filters.exclude_default_vpc', False)
        include_only_default = self.get_config_value('filters.include_only_default_vpc', False)
        
        if exclude_default and is_default:
            return False
        
        if include_only_default and not is_default:
            return False
        
        # Check CIDR filters
        cidr_block = vpc.get('cidr_block', '')
        exclude_cidrs = self.get_config_value('filters.exclude_cidrs', [])
        include_only_cidrs = self.get_config_value('filters.include_only_cidrs', [])
        
        if exclude_cidrs and any(excluded in cidr_block for excluded in exclude_cidrs):
            return False
        
        if include_only_cidrs and not any(included in cidr_block for included in include_only_cidrs):
            return False
        
        return True
    
    def get_cluster_info(self, vpc: Dict[str, Any]) -> Dict[str, str]:
        """Get clustering information for this VPC."""
        cluster_by = self.get_config_value('clustering.group_by', 'none')
        
        if cluster_by == 'none':
            return {
                'cluster_type': 'none',
                'cluster_id': '',
                'cluster_label': ''
            }
        elif cluster_by == 'region':
            region = vpc.get('region', 'unknown-region')
            label_template = self.get_config_value('clustering.cluster_label_format', 'Region: {name}')
            return {
                'cluster_type': 'region',
                'cluster_id': region,
                'cluster_label': label_template.format(name=region)
            }
        
        return {
            'cluster_type': 'none',
            'cluster_id': '',
            'cluster_label': ''
        }
    
    def get_label_variables(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Get VPC-specific variables for label formatting."""
        return {
            'cidr_block': resource.get('cidr_block', ''),
            'state': resource.get('state', ''),
            'is_default': 'Default' if resource.get('is_default', False) else '',
            'region': resource.get('region', '')
        }
    
    def get_metadata(self, vpc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for tooltips or additional info."""
        return {
            'vpc_id': vpc.get('vpc_id'),
            'cidr_block': vpc.get('cidr_block'),
            'state': vpc.get('state'),
            'is_default': vpc.get('is_default'),
            'region': vpc.get('region'),
            'dhcp_options_id': vpc.get('dhcp_options_id'),
            'instance_tenancy': vpc.get('instance_tenancy'),
            'tags': vpc.get('tags', {}),
            'owner_id': vpc.get('owner_id')
        }


def list_resources(aws_client: AWSClient, config: Dict[str, Any]) -> Iterator[Resource]:
    """
    Discover VPCs in the configured region.
    
    Args:
        aws_client: Configured AWS client manager
        config: Snippet configuration for filtering
        
    Yields:
        Resource objects representing VPCs
    """
    # Get filter configuration
    exclude_states = config.get('filters', {}).get('exclude_states', ['deleted'])
    exclude_default = config.get('filters', {}).get('exclude_default_vpc', False)
    include_only_default = config.get('filters', {}).get('include_only_default_vpc', False)
    exclude_cidrs = config.get('filters', {}).get('exclude_cidrs', [])
    include_only_cidrs = config.get('filters', {}).get('include_only_cidrs', [])
    
    for page in aws_client.paginate('ec2', 'describe_vpcs'):
        for vpc in page.get('Vpcs', []):
            # Apply state filters
            state = vpc.get('State', '').lower()
            if state in exclude_states:
                continue
            
            # Apply default VPC filters
            is_default = vpc.get('IsDefault', False)
            if exclude_default and is_default:
                continue
            if include_only_default and not is_default:
                continue
            
            # Apply CIDR filters
            cidr_block = vpc.get('CidrBlock', '')
            if exclude_cidrs and any(excluded in cidr_block for excluded in exclude_cidrs):
                continue
            if include_only_cidrs and not any(included in cidr_block for included in include_only_cidrs):
                continue
            
            # Extract basic info
            id_key = 'VpcId'
            vpc_id = vpc[id_key]
            
            # Process tags
            tags = aws_client.process_tags(vpc.get('Tags', []))
            vpc_name = aws_client.get_tag_value(vpc.get('Tags', []), 'Name', vpc_id)
            
            yield Resource(
                type='aws.ec2.vpc',
                id=vpc_id,
                id_key=id_key,
                _raw=vpc,
                # Normalized fields for diagram generation
                name=vpc_name,
                state=state,
                vpc_id=vpc_id,  # For consistency with other resources
                tags=tags,
                # VPC-specific fields
                cidr_block=cidr_block,
                is_default=is_default,
                region=aws_client.region,
                dhcp_options_id=vpc.get('DhcpOptionsId'),
                instance_tenancy=vpc.get('InstanceTenancy'),
                owner_id=vpc.get('OwnerId')
            )