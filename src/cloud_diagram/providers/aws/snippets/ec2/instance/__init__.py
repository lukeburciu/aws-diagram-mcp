"""EC2 Instance snippet for diagram generation."""

from typing import Dict, Any, Optional, Iterator
from diagrams.aws.compute import EC2
from diagrams import Edge

from ...base import ConfiguredSnippet
from ...utils.discovery import Resource, AWSClient


class EC2InstanceSnippet(ConfiguredSnippet):
    """Snippet for rendering EC2 instances in diagrams."""
    
    def __init__(
        self,
        service: str = 'ec2',
        resource_type: str = 'instance',
        config_loader=None,
        cli_overrides: Optional[Dict[str, Any]] = None
    ):
        """Initialize EC2 instance snippet."""
        super().__init__(service, resource_type, config_loader, cli_overrides)
    
    def create_node(self, instance: Dict[str, Any]) -> Any:
        """Create a diagram node for an EC2 instance."""
        # Generate the label
        label = self._generate_label(instance)
        
        # Create and return the node
        return EC2(label)
    
    def _generate_label(self, instance: Dict[str, Any]) -> str:
        """Generate label for EC2 instance based on configuration."""
        # Extract instance properties
        name = self._get_instance_name(instance)
        instance_id = instance.get('instance_id', '')
        instance_type = instance.get('instance_type', '')
        private_ip = instance.get('private_ip', '')
        public_ip = instance.get('public_ip', '')
        state = instance.get('state', '')
        az = instance.get('availability_zone', '')
        platform = instance.get('platform', 'linux')
        key_pair = instance.get('key_name', '')
        
        # Build label parts
        label_parts = []
        
        # Primary label (usually the name)
        primary_template = self.get_config_value('label.primary_format', '{name}')
        primary_label = primary_template.format(
            name=name,
            id=instance_id,
            instance_type=instance_type,
            private_ip=private_ip,
            public_ip=public_ip,
            state=state,
            az=az,
            platform=platform,
            key_pair=key_pair
        )
        label_parts.append(primary_label)
        
        # Secondary label (usually instance type)
        if self.get_config_value('display.show_instance_type', True) and instance_type:
            secondary_template = self.get_config_value('label.secondary_format', '{instance_type}')
            secondary_label = secondary_template.format(
                instance_type=instance_type,
                name=name,
                private_ip=private_ip,
                public_ip=public_ip
            )
            if secondary_label and secondary_label != primary_label:
                label_parts.append(secondary_label)
        
        # Tertiary label (usually IP address)
        if self.get_config_value('display.show_private_ip', True) and private_ip:
            tertiary_template = self.get_config_value('label.tertiary_format', '{private_ip}')
            tertiary_label = tertiary_template.format(
                private_ip=private_ip,
                public_ip=public_ip,
                instance_type=instance_type
            )
            if tertiary_label and tertiary_label not in label_parts:
                label_parts.append(tertiary_label)
        
        # Build additional attributes based on config
        additional = []
        
        if self.get_config_value('display.show_public_ip', False) and public_ip:
            additional.append(f"Public: {public_ip}")
        
        if self.get_config_value('display.show_availability_zone', False) and az:
            additional.append(f"AZ: {az}")
        
        if self.get_config_value('display.show_instance_state', True) and state:
            additional.append(f"State: {state}")
        
        if self.get_config_value('display.show_key_pair', False) and key_pair:
            additional.append(f"Key: {key_pair}")
        
        if self.get_config_value('display.show_platform', False) and platform and platform != 'linux':
            additional.append(platform.title())
        
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
    
    def _get_instance_name(self, instance: Dict[str, Any]) -> str:
        """Get the display name for an EC2 instance."""
        # Try to get name from tags first
        tags = instance.get('tags', {})
        if isinstance(tags, dict) and 'Name' in tags:
            return tags['Name']
        
        # If we have a name field, use that
        if 'name' in instance and instance['name']:
            return instance['name']
        
        # Fall back to instance ID
        return instance.get('instance_id', 'Unknown')
    
    def create_connection(
        self,
        from_node: Any,
        to_node: Any,
        connection_info: Dict[str, Any]
    ) -> Edge:
        """Create a connection edge with EC2-specific styling."""
        # Extract connection details
        port = connection_info.get('port', '')
        protocol = connection_info.get('protocol', 'tcp')
        connection_type = connection_info.get('type', 'security_group')
        
        # Generate label
        label_format = self.get_config_value('connections.connection_label_format', '{port}/{protocol}')
        label = label_format.format(port=port, protocol=protocol) if port else protocol
        
        # Style based on connection type
        if connection_type == 'load_balancer':
            return Edge(label=label, style="bold", color="blue")
        elif connection_type == 'security_group':
            return Edge(label=label)
        else:
            return Edge(label=label)
    
    def should_render(self, instance: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Determine if this EC2 instance should be rendered based on filters."""
        # Use parent class basic filtering
        if not super().should_render(instance, filters):
            return False
        
        # Check instance state
        state = instance.get('state', '').lower()
        excluded_states = self.get_config_value('filters.exclude_states', ['terminated', 'shutting-down'])
        if state in excluded_states:
            return False
        
        # Check instance type filters
        instance_type = instance.get('instance_type', '')
        
        # Check exclude instance types
        exclude_types = self.get_config_value('filters.exclude_instance_types', [])
        if exclude_types:
            for excluded_type in exclude_types:
                if excluded_type.endswith('*'):
                    # Wildcard matching
                    prefix = excluded_type[:-1]
                    if instance_type.startswith(prefix):
                        return False
                elif instance_type == excluded_type:
                    return False
        
        # Check include only instance types
        include_only_types = self.get_config_value('filters.include_only_instance_types', [])
        if include_only_types:
            include_match = False
            for included_type in include_only_types:
                if included_type.endswith('*'):
                    # Wildcard matching
                    prefix = included_type[:-1]
                    if instance_type.startswith(prefix):
                        include_match = True
                        break
                elif instance_type == included_type:
                    include_match = True
                    break
            
            if not include_match:
                return False
        
        # Check platform filters
        platform = instance.get('platform', 'linux').lower()
        
        exclude_platforms = self.get_config_value('filters.exclude_platforms', [])
        if exclude_platforms and platform in [p.lower() for p in exclude_platforms]:
            return False
        
        include_only_platforms = self.get_config_value('filters.include_only_platforms', [])
        if include_only_platforms and platform not in [p.lower() for p in include_only_platforms]:
            return False
        
        return True
    
    def get_cluster_info(self, instance: Dict[str, Any]) -> Dict[str, str]:
        """Get clustering information for this EC2 instance."""
        cluster_by = self.get_config_value('clustering.group_by', 'subnet')
        
        if cluster_by == 'none':
            return {
                'cluster_type': 'none',
                'cluster_id': '',
                'cluster_label': ''
            }
        elif cluster_by == 'subnet':
            subnet_id = instance.get('subnet_id', 'no-subnet')
            label_template = self.get_config_value('clustering.cluster_label_format', '{type}: {name}')
            return {
                'cluster_type': 'subnet',
                'cluster_id': subnet_id,
                'cluster_label': label_template.format(type='Subnet', name=subnet_id)
            }
        elif cluster_by == 'availability_zone':
            az = instance.get('availability_zone', 'unknown-az')
            label_template = self.get_config_value('clustering.cluster_label_format', '{type}: {name}')
            return {
                'cluster_type': 'availability_zone',
                'cluster_id': az,
                'cluster_label': label_template.format(type='AZ', name=az)
            }
        elif cluster_by == 'instance_type':
            instance_type = instance.get('instance_type', 'unknown')
            # Try to categorize the instance type
            category = self._get_instance_type_category(instance_type)
            label_template = self.get_config_value('clustering.cluster_label_format', '{type}: {name}')
            return {
                'cluster_type': 'instance_type',
                'cluster_id': category,
                'cluster_label': label_template.format(type='Instance Type', name=category.replace('_', ' ').title())
            }
        elif cluster_by == 'security_group':
            # Use the first security group for clustering
            security_groups = instance.get('security_groups', [])
            sg_id = security_groups[0] if security_groups else 'no-sg'
            label_template = self.get_config_value('clustering.cluster_label_format', '{type}: {name}')
            return {
                'cluster_type': 'security_group',
                'cluster_id': sg_id,
                'cluster_label': label_template.format(type='Security Group', name=sg_id)
            }
        
        return {
            'cluster_type': 'none',
            'cluster_id': '',
            'cluster_label': ''
        }
    
    def _get_instance_type_category(self, instance_type: str) -> str:
        """Categorize instance type based on configuration."""
        categories = self.get_config_value('instance_type_categories', {})
        
        for category, patterns in categories.items():
            for pattern in patterns:
                if pattern.endswith('*'):
                    # Wildcard matching
                    prefix = pattern[:-1]
                    if instance_type.startswith(prefix):
                        return category
                elif instance_type == pattern:
                    return category
        
        return 'other'
    
    def get_label_variables(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Get EC2-specific variables for label formatting."""
        return {
            'instance_type': resource.get('instance_type', ''),
            'private_ip': resource.get('private_ip', ''),
            'public_ip': resource.get('public_ip', ''),
            'state': resource.get('state', ''),
            'az': resource.get('availability_zone', ''),
            'platform': resource.get('platform', ''),
            'key_pair': resource.get('key_name', '')
        }
    
    def get_metadata(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for tooltips or additional info."""
        return {
            'instance_id': instance.get('instance_id'),
            'instance_type': instance.get('instance_type'),
            'state': instance.get('state'),
            'private_ip': instance.get('private_ip'),
            'public_ip': instance.get('public_ip'),
            'subnet_id': instance.get('subnet_id'),
            'vpc_id': instance.get('vpc_id'),
            'availability_zone': instance.get('availability_zone'),
            'security_groups': instance.get('security_groups', []),
            'key_name': instance.get('key_name'),
            'platform': instance.get('platform'),
            'launch_time': instance.get('launch_time'),
            'tags': instance.get('tags', {}),
            'monitoring': instance.get('monitoring', {})
        }


def list_resources(aws_client: AWSClient, config: Dict[str, Any]) -> Iterator[Resource]:
    """
    Discover EC2 instances in the configured region.
    
    Args:
        aws_client: Configured AWS client manager
        config: Snippet configuration for filtering
        
    Yields:
        Resource objects representing EC2 instances
    """
    # Get filter configuration
    exclude_states = config.get('filters', {}).get('exclude_states', ['terminated', 'shutting-down'])
    exclude_types = config.get('filters', {}).get('exclude_instance_types', [])
    include_only_types = config.get('filters', {}).get('include_only_instance_types', [])
    exclude_platforms = config.get('filters', {}).get('exclude_platforms', [])
    include_only_platforms = config.get('filters', {}).get('include_only_platforms', [])
    
    for page in aws_client.paginate('ec2', 'describe_instances'):
        for reservation in page.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                # Apply state filters
                state = instance.get('State', {}).get('Name', '').lower()
                if state in exclude_states:
                    continue
                
                # Apply instance type filters
                instance_type = instance.get('InstanceType', '')
                
                # Check exclude instance types
                if exclude_types:
                    exclude_match = False
                    for excluded_type in exclude_types:
                        if excluded_type.endswith('*'):
                            prefix = excluded_type[:-1]
                            if instance_type.startswith(prefix):
                                exclude_match = True
                                break
                        elif instance_type == excluded_type:
                            exclude_match = True
                            break
                    
                    if exclude_match:
                        continue
                
                # Check include only instance types
                if include_only_types:
                    include_match = False
                    for included_type in include_only_types:
                        if included_type.endswith('*'):
                            prefix = included_type[:-1]
                            if instance_type.startswith(prefix):
                                include_match = True
                                break
                        elif instance_type == included_type:
                            include_match = True
                            break
                    
                    if not include_match:
                        continue
                
                # Apply platform filters
                platform = instance.get('Platform', 'linux').lower()
                
                if exclude_platforms and platform in [p.lower() for p in exclude_platforms]:
                    continue
                
                if include_only_platforms and platform not in [p.lower() for p in include_only_platforms]:
                    continue
                
                # Extract basic info
                id_key = 'InstanceId'
                instance_id = instance[id_key]
                
                # Process tags
                tags = aws_client.process_tags(instance.get('Tags', []))
                instance_name = aws_client.get_tag_value(instance.get('Tags', []), 'Name', instance_id)
                
                yield Resource(
                    type='aws.ec2.instance',
                    id=instance_id,
                    id_key=id_key,
                    _raw=instance,
                    # Normalized fields for diagram generation
                    name=instance_name,
                    state=state,
                    vpc_id=instance.get('VpcId'),
                    tags=tags,
                    # EC2-specific fields
                    instance_type=instance_type,
                    private_ip=instance.get('PrivateIpAddress'),
                    public_ip=instance.get('PublicIpAddress'),
                    subnet_id=instance.get('SubnetId'),
                    availability_zone=instance.get('Placement', {}).get('AvailabilityZone'),
                    key_name=instance.get('KeyName'),
                    platform=platform,
                    launch_time=instance.get('LaunchTime'),
                    security_groups=[
                        sg.get('GroupId') 
                        for sg in instance.get('SecurityGroups', [])
                        if sg.get('GroupId')
                    ],
                    monitoring=instance.get('Monitoring', {}).get('State')
                )