"""Route53 Hosted Zone snippet for diagram generation."""

from typing import Dict, Any, Optional, Iterator
from diagrams.aws.network import Route53
from diagrams import Edge

from ...base import ConfiguredSnippet
from ...utils.discovery import Resource, AWSClient


class Route53ZoneSnippet(ConfiguredSnippet):
    """Snippet for rendering Route53 hosted zones in diagrams."""
    
    def __init__(
        self,
        service: str = 'route53',
        resource_type: str = 'hosted_zone',
        config_loader=None,
        cli_overrides: Optional[Dict[str, Any]] = None
    ):
        """Initialize Route53 hosted zone snippet."""
        super().__init__(service, resource_type, config_loader, cli_overrides)
    
    def create_node(self, hosted_zone: Dict[str, Any]) -> Any:
        """Create a diagram node for a Route53 hosted zone."""
        # Generate the label
        label = self._generate_label(hosted_zone)
        
        # Create and return the node
        return Route53(label)
    
    def _generate_label(self, hosted_zone: Dict[str, Any]) -> str:
        """Generate label for Route53 hosted zone based on configuration."""
        # Extract hosted zone properties
        name = hosted_zone.get('name', 'unknown.zone.')
        zone_id = hosted_zone.get('zone_id', hosted_zone.get('id', ''))
        zone_type = self._determine_zone_type(hosted_zone)
        comment = hosted_zone.get('comment', '')
        
        # Clean zone name (remove trailing dot)
        clean_name = name.rstrip('.')
        
        # Count records
        records = hosted_zone.get('records', [])
        record_count = len(records) if records else hosted_zone.get('resource_record_set_count', 0)
        
        # Build label parts
        label_parts = []
        
        # Primary label (usually the zone name)
        primary_template = self.get_config_value('label.primary_format', '{name}')
        primary_label = primary_template.format(
            name=clean_name,
            zone_id=zone_id,
            type=zone_type.title(),
            record_count=record_count,
            comment=comment
        )
        label_parts.append(primary_label)
        
        # Secondary label (usually zone type)
        if self.get_config_value('display.show_zone_type', True) and zone_type:
            secondary_template = self.get_config_value('label.secondary_format', '{type}')
            secondary_label = secondary_template.format(
                type=zone_type.title(),
                name=clean_name,
                record_count=record_count
            )
            if secondary_label and secondary_label != primary_label:
                label_parts.append(secondary_label)
        
        # Tertiary label (optional)
        tertiary_template = self.get_config_value('label.tertiary_format', '')
        if tertiary_template:
            tertiary_label = tertiary_template.format(
                zone_id=zone_id,
                comment=comment,
                record_count=record_count
            )
            if tertiary_label and tertiary_label not in label_parts:
                label_parts.append(tertiary_label)
        
        # Build additional attributes based on config
        additional = []
        
        # Show record count
        if self.get_config_value('display.show_record_count', True) and record_count:
            additional.append(f"{record_count} records")
        
        # Show record types summary
        if self.get_config_value('display.show_record_types', False) and records:
            record_types = set()
            for record in records:
                record_type = record.get('type', record.get('record_type', ''))
                if record_type:
                    record_types.add(record_type)
            
            if record_types:
                type_summary = ', '.join(sorted(record_types)[:3])  # Show first 3 types
                if len(record_types) > 3:
                    type_summary += f', +{len(record_types) - 3}'
                additional.append(f"Types: {type_summary}")
        
        # Show VPC associations for private zones
        if (self.get_config_value('display.show_vpc_associations', True) and 
            zone_type == 'private'):
            vpcs = hosted_zone.get('vpcs', [])
            if vpcs:
                vpc_count = len(vpcs)
                additional.append(f"{vpc_count} VPC" + ("s" if vpc_count > 1 else ""))
        
        # Show DNSSEC status
        if self.get_config_value('display.show_dnssec', False):
            dnssec = hosted_zone.get('dnssec_status', {})
            if dnssec and dnssec.get('status') == 'SIGNING':
                additional.append("DNSSEC")
        
        # Show comment if configured
        if self.get_config_value('display.show_comment', False) and comment:
            # Truncate comment if too long
            display_comment = comment[:20] + '...' if len(comment) > 20 else comment
            additional.append(f'"{display_comment}"')
        
        # Add zone type indicator
        type_indicators = self.get_config_value('visual.zone_type_indicators', {})
        indicator = type_indicators.get(zone_type, '')
        if indicator:
            if additional:
                additional[0] = f"{indicator} {additional[0]}"
            else:
                additional.append(f"{indicator} Zone")
        
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
    
    def _determine_zone_type(self, hosted_zone: Dict[str, Any]) -> str:
        """Determine if a hosted zone is public or private."""
        # Check config field first
        config = hosted_zone.get('config', {})
        if isinstance(config, dict) and 'private_zone' in config:
            return 'private' if config['private_zone'] else 'public'
        
        # Check VPC associations
        vpcs = hosted_zone.get('vpcs', [])
        if vpcs:
            return 'private'
        
        # Check private_zone field directly
        private_zone = hosted_zone.get('private_zone', False)
        return 'private' if private_zone else 'public'
    
    def create_connection(
        self,
        from_node: Any,
        to_node: Any,
        connection_info: Dict[str, Any]
    ) -> Edge:
        """Create a connection edge with Route53-specific styling."""
        # Extract connection details
        record_type = connection_info.get('record_type', connection_info.get('type', 'A'))
        connection_type = connection_info.get('connection_type', 'record')
        target = connection_info.get('target', '')
        
        # Generate label based on connection type
        if connection_type == 'alias':
            alias_format = self.get_config_value('connections.alias_label_format', 'ALIAS → {target}')
            # Simplify target for display
            display_target = target.split('.')[0] if '.' in target else target
            label = alias_format.format(target=display_target)
            return Edge(label=label, style="dashed", color="purple")
        else:
            # Regular DNS record connection
            label_format = self.get_config_value('connections.connection_label_format', '{record_type}')
            label = label_format.format(record_type=record_type)
            
            # Style based on record type
            if record_type in ['A', 'AAAA']:
                return Edge(label=label, style="solid", color="blue")
            elif record_type == 'CNAME':
                return Edge(label=label, style="dashed", color="green")
            elif record_type == 'MX':
                return Edge(label=label, style="solid", color="orange")
            else:
                return Edge(label=label, style="solid", color="gray")
    
    def should_render(self, hosted_zone: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Determine if this Route53 hosted zone should be rendered based on filters."""
        # Use parent class basic filtering
        if not super().should_render(hosted_zone, filters):
            return False
        
        # Check zone type filters
        zone_type = self._determine_zone_type(hosted_zone)
        
        exclude_types = self.get_config_value('filters.exclude_zone_types', [])
        if exclude_types and zone_type in exclude_types:
            return False
        
        include_only_types = self.get_config_value('filters.include_only_zone_types', [])
        if include_only_types and zone_type not in include_only_types:
            return False
        
        # Legacy private zone exclusion
        if (self.get_config_value('filters.exclude_private_zones', False) and 
            zone_type == 'private'):
            return False
        
        # Check record count filters
        records = hosted_zone.get('records', [])
        record_count = len(records) if records else hosted_zone.get('resource_record_set_count', 0)
        
        min_records = self.get_config_value('filters.min_record_count')
        max_records = self.get_config_value('filters.max_record_count')
        
        if min_records is not None and record_count < min_records:
            return False
        if max_records is not None and record_count > max_records:
            return False
        
        # Exclude system zones if configured
        if self.get_config_value('filters.exclude_system_zones', True):
            zone_name = hosted_zone.get('name', '').lower()
            # AWS system zones (examples)
            system_patterns = [
                'amazonaws.com.',
                'aws-internal.',
                'ec2.internal.'
            ]
            
            for pattern in system_patterns:
                if zone_name.endswith(pattern):
                    return False
        
        return True
    
    def get_cluster_info(self, hosted_zone: Dict[str, Any]) -> Dict[str, str]:
        """Get clustering information for this Route53 hosted zone."""
        cluster_by = self.get_config_value('clustering.group_by', 'type')
        
        if cluster_by == 'none':
            return {
                'cluster_type': 'none',
                'cluster_id': '',
                'cluster_label': ''
            }
        elif cluster_by == 'type':
            zone_type = self._determine_zone_type(hosted_zone)
            label_template = self.get_config_value('clustering.cluster_label_format', '{type} DNS Zones')
            return {
                'cluster_type': 'zone_type',
                'cluster_id': zone_type,
                'cluster_label': label_template.format(type=zone_type.title())
            }
        elif cluster_by == 'vpc':
            # Use first VPC for clustering (for private zones)
            vpcs = hosted_zone.get('vpcs', [])
            if vpcs:
                vpc_id = vpcs[0].get('vpc_id', 'unknown-vpc') if isinstance(vpcs[0], dict) else str(vpcs[0])
                return {
                    'cluster_type': 'vpc',
                    'cluster_id': vpc_id,
                    'cluster_label': f'VPC: {vpc_id}'
                }
            else:
                return {
                    'cluster_type': 'vpc',
                    'cluster_id': 'public',
                    'cluster_label': 'Public DNS Zones'
                }
        
        return {
            'cluster_type': 'none',
            'cluster_id': '',
            'cluster_label': ''
        }
    
    def get_label_variables(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Get Route53-specific variables for label formatting."""
        records = resource.get('records', [])
        record_count = len(records) if records else resource.get('resource_record_set_count', 0)
        
        return {
            'zone_id': resource.get('zone_id', resource.get('id', '')),
            'type': self._determine_zone_type(resource),
            'record_count': record_count,
            'comment': resource.get('comment', '')
        }
    
    def get_metadata(self, hosted_zone: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for tooltips or additional info."""
        config = hosted_zone.get('config', {})
        
        return {
            'hosted_zone_id': hosted_zone.get('zone_id', hosted_zone.get('id')),
            'name': hosted_zone.get('name'),
            'type': self._determine_zone_type(hosted_zone),
            'comment': hosted_zone.get('comment'),
            'caller_reference': hosted_zone.get('caller_reference'),
            'resource_record_set_count': hosted_zone.get('resource_record_set_count', 0),
            'name_servers': hosted_zone.get('name_servers', []),
            'vpcs': hosted_zone.get('vpcs', []),
            'dnssec_status': hosted_zone.get('dnssec_status', {}),
            'query_logging_configs': hosted_zone.get('query_logging_configs', []),
            'tags': hosted_zone.get('tags', {}),
            'delegation_set_id': hosted_zone.get('delegation_set_id')
        }


def list_resources(aws_client: AWSClient, config: Dict[str, Any]) -> Iterator[Resource]:
    """
    Discover Route53 hosted zones in the configured region.
    
    Args:
        aws_client: Configured AWS client manager
        config: Snippet configuration for filtering
        
    Yields:
        Resource objects representing Route53 hosted zones
    """
    # Get filter configuration
    exclude_zone_types = config.get('filters', {}).get('exclude_zone_types', [])
    include_only_zone_types = config.get('filters', {}).get('include_only_zone_types', [])
    exclude_private_zones = config.get('filters', {}).get('exclude_private_zones', False)
    exclude_system_zones = config.get('filters', {}).get('exclude_system_zones', True)
    min_records = config.get('filters', {}).get('min_record_count')
    max_records = config.get('filters', {}).get('max_record_count')
    
    # Route53 is a global service, so use global client
    for page in aws_client.paginate('route53', 'list_hosted_zones', use_global=True):
        for zone in page.get('HostedZones', []):
            # Extract basic zone info
            zone_id = zone.get('Id', '').replace('/hostedzone/', '')  # Clean up ID
            zone_name = zone.get('Name', '')
            config_info = zone.get('Config', {})
            private_zone = config_info.get('PrivateZone', False)
            
            # Determine zone type
            zone_type = 'private' if private_zone else 'public'
            
            # Apply zone type filters
            if exclude_zone_types and zone_type in exclude_zone_types:
                continue
            
            if include_only_zone_types and zone_type not in include_only_zone_types:
                continue
            
            # Legacy private zone exclusion
            if exclude_private_zones and zone_type == 'private':
                continue
            
            # Exclude system zones if configured
            if exclude_system_zones:
                zone_name_lower = zone_name.lower()
                system_patterns = [
                    'amazonaws.com.',
                    'aws-internal.',
                    'ec2.internal.'
                ]
                
                is_system_zone = any(zone_name_lower.endswith(pattern) for pattern in system_patterns)
                if is_system_zone:
                    continue
            
            # Get record count for filtering
            record_count = zone.get('ResourceRecordSetCount', 0)
            
            # Apply record count filters
            if min_records is not None and record_count < min_records:
                continue
            if max_records is not None and record_count > max_records:
                continue
            
            # Get VPC associations for private zones
            vpcs = []
            if private_zone:
                try:
                    vpcs_response = aws_client.describe_single(
                        'route53',
                        'get_hosted_zone',
                        use_global=True,
                        Id=zone_id
                    )
                    
                    if vpcs_response and 'VPCs' in vpcs_response:
                        vpcs = vpcs_response['VPCs']
                except Exception:
                    # If we can't get VPC info, continue without it
                    pass
            
            # Get tags
            tags = {}
            try:
                tags_response = aws_client.describe_single(
                    'route53',
                    'list_tags_for_resource',
                    use_global=True,
                    ResourceType='hostedzone',
                    ResourceId=zone_id
                )
                
                if tags_response and 'ResourceTagSet' in tags_response:
                    tag_set = tags_response['ResourceTagSet']
                    tags = aws_client.process_tags(tag_set.get('Tags', []))
            except Exception:
                # If we can't get tags, continue without them
                pass
            
            # Get name servers
            name_servers = []
            try:
                ns_response = aws_client.describe_single(
                    'route53',
                    'get_hosted_zone',
                    use_global=True,
                    Id=zone_id
                )
                
                if ns_response and 'DelegationSet' in ns_response:
                    delegation_set = ns_response['DelegationSet']
                    name_servers = delegation_set.get('NameServers', [])
            except Exception:
                # If we can't get name servers, continue without them
                pass
            
            yield Resource(
                type='aws.route53.hosted_zone',
                id=zone_id,
                id_key='Id',
                _raw=zone,
                # Normalized fields for diagram generation
                name=zone_name.rstrip('.'),  # Remove trailing dot
                state='active',  # Route53 zones don't have explicit state
                vpc_id=vpcs[0].get('VPCId') if vpcs else None,  # Use first VPC for normalization
                tags=tags,
                # Route53-specific fields
                zone_id=zone_id,
                comment=config_info.get('Comment', ''),
                caller_reference=zone.get('CallerReference'),
                resource_record_set_count=record_count,
                private_zone=private_zone,
                name_servers=name_servers,
                vpcs=vpcs,
                config=config_info
            )