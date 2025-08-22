"""RDS DB Instance snippet for diagram generation."""

from typing import Dict, Any, Optional, Iterator
from diagrams.aws.database import RDS
from diagrams import Edge

from ...base import ConfiguredSnippet
from ....utils.discovery import Resource, AWSClient


class RDSInstanceSnippet(ConfiguredSnippet):
    """Snippet for rendering RDS DB instances in diagrams."""
    
    # Engine-specific icon mapping (using generic RDS icon for compatibility)
    ENGINE_ICONS = {
        'mysql': RDS,
        'postgres': RDS,
        'postgresql': RDS,
        'mariadb': RDS,
        'oracle': RDS,
        'sqlserver': RDS,
        'aurora': RDS,
        'aurora-mysql': RDS,
        'aurora-postgresql': RDS
    }
    
    def __init__(
        self,
        service: str = 'rds',
        resource_type: str = 'db_instance',
        config_loader=None,
        cli_overrides: Optional[Dict[str, Any]] = None
    ):
        """Initialize RDS instance snippet."""
        super().__init__(service, resource_type, config_loader, cli_overrides)
    
    def create_node(self, instance: Dict[str, Any]) -> Any:
        """Create a diagram node for an RDS instance."""
        # Get the appropriate icon class
        icon_class = self._get_icon_class(instance)
        
        # Generate the label
        label = self._generate_label(instance)
        
        # Create and return the node
        return icon_class(label)
    
    def _get_icon_class(self, instance: Dict[str, Any]) -> type:
        """Get the appropriate icon class for the RDS engine."""
        icon_style = self.get_config_value('visual.icon_style', 'engine_specific')
        
        if icon_style == 'generic':
            return RDS
        
        engine = instance.get('engine', '').lower()
        
        # Handle aurora variants (all use RDS for now)
        if 'aurora' in engine:
            return RDS
        
        # Map engine to icon
        return self.ENGINE_ICONS.get(engine, RDS)
    
    def _generate_label(self, instance: Dict[str, Any]) -> str:
        """Generate label for RDS instance based on configuration."""
        # Extract instance properties
        name = instance.get('db_instance_id', 'Unknown')
        engine = instance.get('engine', 'unknown')
        version = instance.get('engine_version', '')
        instance_class = instance.get('instance_class', '')
        endpoint = instance.get('endpoint', '')
        multi_az = instance.get('multi_az', False)
        storage = instance.get('allocated_storage', 0)
        encrypted = instance.get('storage_encrypted', False)
        backup_retention = instance.get('backup_retention_period', 0)
        
        # Format version (simplify if needed)
        if version and self.get_config_value('display.show_engine_version', True):
            # Extract major.minor version
            version_parts = version.split('.')
            if len(version_parts) >= 2:
                version = f"{version_parts[0]}.{version_parts[1]}"
        else:
            version = ''
        
        # Format endpoint based on config
        formatted_endpoint = self._format_endpoint(endpoint)
        
        # Build label parts
        label_parts = []
        
        # Primary label
        primary_template = self.get_config_value('label.primary_format', '{name}')
        primary_label = primary_template.format(
            name=name,
            id=instance.get('db_instance_id', ''),
            engine=engine.capitalize(),
            version=version,
            instance_class=instance_class,
            endpoint=formatted_endpoint
        )
        label_parts.append(primary_label)
        
        # Secondary label
        if self.get_config_value('display.show_engine_version', True) and version:
            secondary_template = self.get_config_value('label.secondary_format', '{engine} {version}')
            secondary_label = secondary_template.format(
                engine=engine.capitalize(),
                version=version
            )
            if secondary_label and secondary_label != primary_label:
                label_parts.append(secondary_label)
        
        # Tertiary label
        if self.get_config_value('display.show_instance_class', True) and instance_class:
            tertiary_template = self.get_config_value('label.tertiary_format', '{instance_class}')
            tertiary_label = tertiary_template.format(instance_class=instance_class)
            if tertiary_label and tertiary_label not in label_parts:
                label_parts.append(tertiary_label)
        
        # Build additional attributes based on config
        additional = []
        
        if self.get_config_value('display.show_multi_az', True) and multi_az:
            additional.append("Multi-AZ")
        
        if self.get_config_value('display.show_storage', False) and storage:
            additional.append(f"{storage}GB")
        
        if self.get_config_value('display.show_encryption', False) and encrypted:
            additional.append("Encrypted")
        
        if self.get_config_value('display.show_backup_retention', False) and backup_retention:
            additional.append(f"Backup: {backup_retention}d")
        
        if self.get_config_value('display.show_endpoint', True) and formatted_endpoint and formatted_endpoint not in ''.join(label_parts):
            additional.append(formatted_endpoint)
        
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
    
    def _format_endpoint(self, endpoint: str) -> str:
        """Format endpoint based on configuration."""
        if not endpoint:
            return ''
        
        show_endpoint = self.get_config_value('display.show_endpoint', True)
        if not show_endpoint:
            return ''
        
        # For simplicity, just return the first part of the endpoint
        parts = endpoint.split('.')
        if parts:
            return parts[0]
        
        return endpoint
    
    def create_connection(
        self,
        from_node: Any,
        to_node: Any,
        connection_info: Dict[str, Any]
    ) -> Edge:
        """Create a connection edge with RDS-specific styling."""
        # Extract connection details
        port = connection_info.get('port', 3306)
        protocol = connection_info.get('protocol', 'tcp')
        connection_type = connection_info.get('type', 'database')
        
        # Generate label
        label_format = self.get_config_value('connections.connection_label_format', '{port}/{protocol}')
        label = label_format.format(port=port, protocol=protocol)
        
        # Style based on connection type
        if connection_type == 'read_replica':
            style = self.get_config_value('connections.read_replica_style', 'dashed')
            return Edge(label=label, style=style, color="blue")
        elif connection_type == 'cluster_member':
            style = self.get_config_value('connections.cluster_member_style', 'dotted')
            return Edge(label=label, style=style, color="purple")
        else:
            return Edge(label=label)
    
    def should_render(self, instance: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Determine if this RDS instance should be rendered based on filters."""
        # Use parent class basic filtering
        if not super().should_render(instance, filters):
            return False
        
        # Check instance state
        status = instance.get('db_instance_status', '').lower()
        excluded_states = self.get_config_value('filters.exclude_states', ['deleting', 'deleted', 'failed'])
        if status in excluded_states:
            return False
        
        # Check engine filters
        engine = instance.get('engine', '').lower()
        
        # Check exclude engines
        exclude_engines = self.get_config_value('filters.exclude_engines', [])
        if exclude_engines and any(excluded in engine for excluded in exclude_engines):
            return False
        
        # Check include only engines
        include_only_engines = self.get_config_value('filters.include_only_engines', [])
        if include_only_engines and not any(included in engine for included in include_only_engines):
            return False
        
        # Check instance class filters
        instance_class = instance.get('instance_class', '')
        exclude_classes = self.get_config_value('filters.exclude_instance_classes', [])
        if exclude_classes and instance_class in exclude_classes:
            return False
        
        # Check storage filters
        storage = instance.get('allocated_storage', 0)
        min_storage = self.get_config_value('filters.min_storage_gb')
        max_storage = self.get_config_value('filters.max_storage_gb')
        
        if min_storage is not None and storage < min_storage:
            return False
        if max_storage is not None and storage > max_storage:
            return False
        
        return True
    
    def get_cluster_info(self, instance: Dict[str, Any]) -> Dict[str, str]:
        """Get clustering information for this RDS instance."""
        cluster_by = self.get_config_value('clustering.group_by', 'subnet_group')
        
        if cluster_by == 'none':
            return {
                'cluster_type': 'none',
                'cluster_id': '',
                'cluster_label': ''
            }
        elif cluster_by == 'subnet_group':
            subnet_group = instance.get('db_subnet_group', {})
            name = subnet_group.get('name', 'default') if isinstance(subnet_group, dict) else str(subnet_group)
            label_template = self.get_config_value('clustering.cluster_label_format', 'DB Subnet Group: {name}')
            return {
                'cluster_type': 'subnet_group',
                'cluster_id': name,
                'cluster_label': label_template.format(name=name)
            }
        elif cluster_by == 'vpc':
            vpc_id = instance.get('vpc_id', 'default-vpc')
            return {
                'cluster_type': 'vpc',
                'cluster_id': vpc_id,
                'cluster_label': f'VPC: {vpc_id}'
            }
        elif cluster_by == 'availability_zone':
            az = instance.get('availability_zone', 'unknown-az')
            return {
                'cluster_type': 'availability_zone',
                'cluster_id': az,
                'cluster_label': f'AZ: {az}'
            }
        
        return {
            'cluster_type': 'none',
            'cluster_id': '',
            'cluster_label': ''
        }
    
    def get_label_variables(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Get RDS-specific variables for label formatting."""
        return {
            'engine': resource.get('engine', ''),
            'version': resource.get('engine_version', ''),
            'instance_class': resource.get('instance_class', ''),
            'endpoint': resource.get('endpoint', ''),
            'port': resource.get('port', ''),
            'storage': resource.get('allocated_storage', ''),
            'multi_az': 'Multi-AZ' if resource.get('multi_az', False) else '',
            'az': resource.get('availability_zone', '')
        }
    
    def get_metadata(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for tooltips or additional info."""
        return {
            'db_instance_id': instance.get('db_instance_id'),
            'engine': f"{instance.get('engine')} {instance.get('engine_version')}",
            'instance_class': instance.get('instance_class'),
            'storage': f"{instance.get('allocated_storage')}GB {instance.get('storage_type', 'standard')}",
            'multi_az': instance.get('multi_az'),
            'encrypted': instance.get('storage_encrypted'),
            'backup_retention': instance.get('backup_retention_period'),
            'maintenance_window': instance.get('preferred_maintenance_window'),
            'endpoint': instance.get('endpoint'),
            'port': instance.get('port'),
            'vpc_id': instance.get('vpc_id'),
            'subnet_group': instance.get('db_subnet_group', {}).get('name') if isinstance(instance.get('db_subnet_group'), dict) else str(instance.get('db_subnet_group', '')),
            'security_groups': instance.get('security_groups', []),
            'tags': instance.get('tags', {}),
            'status': instance.get('db_instance_status', 'unknown')
        }


def list_resources(aws_client: AWSClient, config: Dict[str, Any]) -> Iterator[Resource]:
    """
    Discover RDS DB instances in the configured region.
    
    Args:
        aws_client: Configured AWS client manager
        config: Snippet configuration for filtering
        
    Yields:
        Resource objects representing RDS DB instances
    """
    # Get filter configuration
    exclude_engines = config.get('filters', {}).get('exclude_engines', [])
    exclude_states = config.get('filters', {}).get('exclude_states', ['deleting', 'deleted', 'failed'])
    include_only_engines = config.get('filters', {}).get('include_only_engines', [])
    min_storage = config.get('filters', {}).get('min_storage_gb')
    max_storage = config.get('filters', {}).get('max_storage_gb')
    
    for page in aws_client.paginate('rds', 'describe_db_instances'):
        for db in page.get('DBInstances', []):
            # Apply engine filters
            engine = db.get('Engine', '').lower()
            if exclude_engines and any(excluded in engine for excluded in exclude_engines):
                continue
                
            if include_only_engines and not any(included in engine for included in include_only_engines):
                continue
            
            # Apply state filters
            status = db.get('DBInstanceStatus', '').lower()
            if status in exclude_states:
                continue
            
            # Apply storage filters
            storage = db.get('AllocatedStorage', 0)
            if min_storage is not None and storage < min_storage:
                continue
            if max_storage is not None and storage > max_storage:
                continue
            
            # Extract basic info
            id_key = 'DBInstanceIdentifier'
            instance_id = db[id_key]
            
            # Process tags
            tags = aws_client.process_tags(db.get('TagList', []))
            
            # Get VPC information
            subnet_group = db.get('DBSubnetGroup', {})
            vpc_id = subnet_group.get('VpcId')
            
            yield Resource(
                type='aws.rds.db_instance',
                id=instance_id,
                id_key=id_key,
                _raw=db,
                # Normalized fields for diagram generation
                name=instance_id,
                state=status,
                vpc_id=vpc_id,
                tags=tags,
                # RDS-specific fields
                engine=db.get('Engine'),
                engine_version=db.get('EngineVersion'),
                instance_class=db.get('DBInstanceClass'),
                endpoint=db.get('Endpoint', {}).get('Address'),
                port=db.get('Endpoint', {}).get('Port'),
                multi_az=db.get('MultiAZ', False),
                allocated_storage=db.get('AllocatedStorage'),
                storage_encrypted=db.get('StorageEncrypted', False),
                backup_retention_period=db.get('BackupRetentionPeriod'),
                availability_zone=db.get('AvailabilityZone'),
                subnet_group=subnet_group.get('DBSubnetGroupName'),
                security_groups=[
                    sg.get('VpcSecurityGroupId') 
                    for sg in db.get('VpcSecurityGroups', [])
                    if sg.get('VpcSecurityGroupId')
                ]
            )