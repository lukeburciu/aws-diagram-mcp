"""Security Group snippet for diagram generation."""

from typing import Dict, Any, Optional, Iterator, List
from diagrams.aws.security import IAMRole  # Using IAMRole as closest security icon
from diagrams import Edge

from ...base import ConfiguredSnippet
from ....utils.discovery import Resource, AWSClient


class SecurityGroupSnippet(ConfiguredSnippet):
    """Snippet for rendering Security Groups in diagrams."""
    
    def __init__(
        self,
        service: str = 'ec2',
        resource_type: str = 'security_group',
        config_loader=None,
        cli_overrides: Optional[Dict[str, Any]] = None
    ):
        """Initialize Security Group snippet."""
        super().__init__(service, resource_type, config_loader, cli_overrides)
    
    def create_node(self, security_group: Dict[str, Any]) -> Any:
        """Create a diagram node for a Security Group."""
        # Generate the label
        label = self._generate_label(security_group)
        
        # Create and return the node
        return IAMRole(label)
    
    def _generate_label(self, sg: Dict[str, Any]) -> str:
        """Generate label for Security Group based on configuration."""
        # Extract security group properties
        group_id = sg.get('group_id', 'Unknown')
        name = sg.get('group_name', group_id)
        description = sg.get('description', '')
        vpc_id = sg.get('vpc_id', '')
        ingress_count = len(sg.get('ip_permissions', []))
        egress_count = len(sg.get('ip_permissions_egress', []))
        owner_id = sg.get('owner_id', '')
        
        # Build label parts
        label_parts = []
        
        # Primary label
        primary_template = self.get_config_value('label.primary_format', '{name}')
        primary_label = primary_template.format(
            name=name,
            id=group_id,
            description=description,
            vpc_id=vpc_id,
            ingress_count=ingress_count,
            egress_count=egress_count,
            owner=owner_id
        )
        label_parts.append(primary_label)
        
        # Secondary label
        if self.get_config_value('display.show_description', True) and description:
            secondary_template = self.get_config_value('label.secondary_format', '{description}')
            secondary_label = secondary_template.format(description=description)
            if secondary_label and secondary_label != primary_label:
                # Truncate long descriptions
                if len(secondary_label) > 30:
                    secondary_label = secondary_label[:27] + '...'
                label_parts.append(secondary_label)
        
        # Tertiary label
        if self.get_config_value('display.show_rule_count', True):
            tertiary_template = self.get_config_value('label.tertiary_format', '{ingress_count} in, {egress_count} out')
            tertiary_label = tertiary_template.format(
                ingress_count=ingress_count,
                egress_count=egress_count
            )
            if tertiary_label and tertiary_label not in label_parts:
                label_parts.append(tertiary_label)
        
        # Build additional attributes based on config
        additional = []
        
        if self.get_config_value('display.show_vpc_id', False) and vpc_id:
            additional.append(f"VPC: {vpc_id}")
        
        if self.get_config_value('display.show_owner', False) and owner_id:
            additional.append(f"Owner: {owner_id}")
        
        # Check for security issues
        if self._has_open_rules(sg):
            additional.append("⚠️ Open Rules")
        
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
    
    def _has_open_rules(self, sg: Dict[str, Any]) -> bool:
        """Check if security group has rules open to 0.0.0.0/0."""
        if not self.get_config_value('rule_analysis.highlight_open_rules', True):
            return False
        
        # Check ingress rules
        for rule in sg.get('ip_permissions', []):
            for ip_range in rule.get('ip_ranges', []):
                if ip_range.get('cidr_ip') == '0.0.0.0/0':
                    return True
            for ipv6_range in rule.get('ipv6_ranges', []):
                if ipv6_range.get('cidr_ipv6') == '::/0':
                    return True
        
        # Check egress rules if configured
        for rule in sg.get('ip_permissions_egress', []):
            for ip_range in rule.get('ip_ranges', []):
                if ip_range.get('cidr_ip') == '0.0.0.0/0':
                    return True
            for ipv6_range in rule.get('ipv6_ranges', []):
                if ipv6_range.get('cidr_ipv6') == '::/0':
                    return True
        
        return False
    
    def create_connection(
        self,
        from_node: Any,
        to_node: Any,
        connection_info: Dict[str, Any]
    ) -> Edge:
        """Create a connection edge with Security Group-specific styling."""
        # Extract connection details
        rule_type = connection_info.get('type', 'rule')
        protocol = connection_info.get('protocol', 'tcp')
        port = connection_info.get('port', '')
        
        # Generate label
        if self.get_config_value('connections.show_port_labels', True):
            label_format = self.get_config_value('connections.connection_label_format', '{protocol}:{port}')
            label = label_format.format(protocol=protocol, port=port)
        else:
            label = ''
        
        # Style based on rule type
        rule_colors = self.get_config_value('visual.rule_colors', {})
        if rule_type == 'ingress':
            color = rule_colors.get('ingress', 'green')
            return Edge(label=label, style="solid", color=color)
        elif rule_type == 'egress':
            color = rule_colors.get('egress', 'blue')
            return Edge(label=label, style="dashed", color=color)
        else:
            return Edge(label=label)
    
    def should_render(self, sg: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Determine if this Security Group should be rendered based on filters."""
        # Use parent class basic filtering
        if not super().should_render(sg, filters):
            return False
        
        # Check default group filters
        group_name = sg.get('group_name', '')
        is_default = group_name == 'default'
        
        exclude_default = self.get_config_value('filters.exclude_default_groups', False)
        include_only_default = self.get_config_value('filters.include_only_default_groups', False)
        
        if exclude_default and is_default:
            return False
        
        if include_only_default and not is_default:
            return False
        
        # Check rule count filters
        ingress_count = len(sg.get('ip_permissions', []))
        egress_count = len(sg.get('ip_permissions_egress', []))
        total_rules = ingress_count + egress_count
        
        min_rules = self.get_config_value('filters.min_rule_count')
        max_rules = self.get_config_value('filters.max_rule_count')
        
        if min_rules is not None and total_rules < min_rules:
            return False
        if max_rules is not None and total_rules > max_rules:
            return False
        
        # Check rule type filters
        exclude_rule_types = self.get_config_value('filters.exclude_rule_types', [])
        include_only_rule_types = self.get_config_value('filters.include_only_rule_types', [])
        
        has_ingress = ingress_count > 0
        has_egress = egress_count > 0
        
        if exclude_rule_types:
            if 'ingress' in exclude_rule_types and has_ingress:
                return False
            if 'egress' in exclude_rule_types and has_egress:
                return False
        
        if include_only_rule_types:
            include_match = False
            if 'ingress' in include_only_rule_types and has_ingress:
                include_match = True
            if 'egress' in include_only_rule_types and has_egress:
                include_match = True
            if not include_match:
                return False
        
        return True
    
    def get_cluster_info(self, sg: Dict[str, Any]) -> Dict[str, str]:
        """Get clustering information for this Security Group."""
        cluster_by = self.get_config_value('clustering.group_by', 'vpc')
        
        if cluster_by == 'none':
            return {
                'cluster_type': 'none',
                'cluster_id': '',
                'cluster_label': ''
            }
        elif cluster_by == 'vpc':
            vpc_id = sg.get('vpc_id', 'default-vpc')
            label_template = self.get_config_value('clustering.cluster_label_format', 'VPC: {name}')
            return {
                'cluster_type': 'vpc',
                'cluster_id': vpc_id,
                'cluster_label': label_template.format(name=vpc_id)
            }
        
        return {
            'cluster_type': 'none',
            'cluster_id': '',
            'cluster_label': ''
        }
    
    def get_label_variables(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Get Security Group-specific variables for label formatting."""
        return {
            'description': resource.get('description', ''),
            'vpc_id': resource.get('vpc_id', ''),
            'ingress_count': len(resource.get('ip_permissions', [])),
            'egress_count': len(resource.get('ip_permissions_egress', [])),
            'owner': resource.get('owner_id', '')
        }
    
    def get_metadata(self, sg: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for tooltips or additional info."""
        return {
            'group_id': sg.get('group_id'),
            'group_name': sg.get('group_name'),
            'description': sg.get('description'),
            'vpc_id': sg.get('vpc_id'),
            'owner_id': sg.get('owner_id'),
            'ingress_rules': len(sg.get('ip_permissions', [])),
            'egress_rules': len(sg.get('ip_permissions_egress', [])),
            'has_open_rules': self._has_open_rules(sg),
            'tags': sg.get('tags', {})
        }


def list_resources(aws_client: AWSClient, config: Dict[str, Any]) -> Iterator[Resource]:
    """
    Discover Security Groups in the configured region.
    
    Args:
        aws_client: Configured AWS client manager
        config: Snippet configuration for filtering
        
    Yields:
        Resource objects representing Security Groups
    """
    # Get filter configuration
    exclude_default = config.get('filters', {}).get('exclude_default_groups', False)
    include_only_default = config.get('filters', {}).get('include_only_default_groups', False)
    exclude_rule_types = config.get('filters', {}).get('exclude_rule_types', [])
    include_only_rule_types = config.get('filters', {}).get('include_only_rule_types', [])
    min_rules = config.get('filters', {}).get('min_rule_count')
    max_rules = config.get('filters', {}).get('max_rule_count')
    
    for page in aws_client.paginate('ec2', 'describe_security_groups'):
        for sg in page.get('SecurityGroups', []):
            # Extract basic info
            id_key = 'GroupId'
            group_id = sg[id_key]
            group_name = sg.get('GroupName', group_id)
            
            # Check default group filters
            is_default = group_name == 'default'
            if exclude_default and is_default:
                continue
            if include_only_default and not is_default:
                continue
            
            # Check rule count filters
            ingress_count = len(sg.get('IpPermissions', []))
            egress_count = len(sg.get('IpPermissionsEgress', []))
            total_rules = ingress_count + egress_count
            
            if min_rules is not None and total_rules < min_rules:
                continue
            if max_rules is not None and total_rules > max_rules:
                continue
            
            # Check rule type filters
            has_ingress = ingress_count > 0
            has_egress = egress_count > 0
            
            if exclude_rule_types:
                if 'ingress' in exclude_rule_types and has_ingress:
                    continue
                if 'egress' in exclude_rule_types and has_egress:
                    continue
            
            if include_only_rule_types:
                include_match = False
                if 'ingress' in include_only_rule_types and has_ingress:
                    include_match = True
                if 'egress' in include_only_rule_types and has_egress:
                    include_match = True
                if not include_match:
                    continue
            
            # Process tags
            tags = aws_client.process_tags(sg.get('Tags', []))
            
            yield Resource(
                type='aws.ec2.security_group',
                id=group_id,
                id_key=id_key,
                _raw=sg,
                # Normalized fields for diagram generation
                name=group_name,
                state='active',  # Security groups don't have a state
                vpc_id=sg.get('VpcId'),
                tags=tags,
                # Security Group-specific fields
                group_id=group_id,
                group_name=group_name,
                description=sg.get('Description', ''),
                owner_id=sg.get('OwnerId'),
                ip_permissions=sg.get('IpPermissions', []),
                ip_permissions_egress=sg.get('IpPermissionsEgress', [])
            )