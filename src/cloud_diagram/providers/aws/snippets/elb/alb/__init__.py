"""Application Load Balancer (ALB) snippet for diagram generation."""

from typing import Dict, Any, Optional, Iterator
from diagrams.aws.network import ALB
from diagrams import Edge

from ...base import ConfiguredSnippet
from ....utils.discovery import Resource, AWSClient


class ALBSnippet(ConfiguredSnippet):
    """Snippet for rendering Application Load Balancers in diagrams."""
    
    def __init__(
        self,
        service: str = 'elb',
        resource_type: str = 'alb',
        config_loader=None,
        cli_overrides: Optional[Dict[str, Any]] = None
    ):
        """Initialize ALB snippet."""
        super().__init__(service, resource_type, config_loader, cli_overrides)
    
    def create_node(self, load_balancer: Dict[str, Any]) -> Any:
        """Create a diagram node for an ALB."""
        # Generate the label
        label = self._generate_label(load_balancer)
        
        # Create and return the node
        return ALB(label)
    
    def _generate_label(self, load_balancer: Dict[str, Any]) -> str:
        """Generate label for ALB based on configuration."""
        # Extract load balancer properties
        name = load_balancer.get('name', load_balancer.get('load_balancer_name', 'Unknown'))
        dns_name = load_balancer.get('dns_name', '')
        scheme = load_balancer.get('scheme', 'internet-facing')
        lb_type = load_balancer.get('type', 'application')
        state = load_balancer.get('state', {})
        vpc_id = load_balancer.get('vpc_id', '')
        
        # Get shortened DNS name for display
        short_dns = dns_name.split('.')[0] if dns_name else ''
        
        # Build label parts
        label_parts = []
        
        # Primary label (usually the name)
        primary_template = self.get_config_value('label.primary_format', '{name}')
        primary_label = primary_template.format(
            name=name,
            dns_name=short_dns,
            scheme=scheme,
            type=lb_type,
            state=state.get('code', '') if isinstance(state, dict) else str(state),
            vpc_id=vpc_id
        )
        label_parts.append(primary_label)
        
        # Secondary label (usually scheme)
        if self.get_config_value('display.show_scheme', True) and scheme:
            secondary_template = self.get_config_value('label.secondary_format', '{scheme}')
            secondary_label = secondary_template.format(
                scheme=scheme.replace('-', ' ').title(),
                name=name,
                type=lb_type
            )
            if secondary_label and secondary_label != primary_label:
                label_parts.append(secondary_label)
        
        # Tertiary label (optional)
        tertiary_template = self.get_config_value('label.tertiary_format', '')
        if tertiary_template:
            tertiary_label = tertiary_template.format(
                dns_name=short_dns,
                vpc_id=vpc_id,
                name=name
            )
            if tertiary_label and tertiary_label not in label_parts:
                label_parts.append(tertiary_label)
        
        # Build additional attributes based on config
        additional = []
        
        # Show target group count
        if self.get_config_value('display.show_target_groups', True):
            target_groups = load_balancer.get('target_groups', [])
            if target_groups:
                additional.append(f"{len(target_groups)} TG")
        
        # Show listener count
        if self.get_config_value('display.show_listeners', True):
            listeners = load_balancer.get('listeners', [])
            if listeners:
                additional.append(f"{len(listeners)} listeners")
        
        # Show availability zones
        if self.get_config_value('display.show_availability_zones', False):
            azs = load_balancer.get('availability_zones', [])
            if azs:
                az_count = len(azs)
                additional.append(f"{az_count} AZ" + ("s" if az_count > 1 else ""))
        
        # Show SSL certificates
        if self.get_config_value('display.show_ssl_certificates', True):
            # Check if any listeners have SSL certificates
            listeners = load_balancer.get('listeners', [])
            ssl_count = 0
            for listener in listeners:
                certificates = listener.get('certificates', [])
                ssl_count += len(certificates)
            
            if ssl_count > 0:
                additional.append(f"{ssl_count} SSL cert" + ("s" if ssl_count > 1 else ""))
        
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
        """Create a connection edge with ALB-specific styling."""
        # Extract connection details
        port = connection_info.get('port', 80)
        protocol = connection_info.get('protocol', 'HTTP')
        connection_type = connection_info.get('type', 'target')
        health_check = connection_info.get('health_check', {})
        
        # Generate label based on connection type
        if connection_type == 'health_check' and self.get_config_value('display.show_health_checks', True):
            hc_format = self.get_config_value('connections.health_check_label_format', 'HC: {port}{path}')
            hc_port = health_check.get('port', port)
            hc_path = health_check.get('path', '/')
            label = hc_format.format(port=hc_port, path=hc_path)
            return Edge(label=label, style="dotted", color="orange")
        else:
            # Regular target connection
            label_format = self.get_config_value('connections.connection_label_format', '{port}/{protocol}')
            label = label_format.format(port=port, protocol=protocol)
            
            # Style based on target health if available
            target_health = connection_info.get('health', 'healthy')
            if target_health == 'unhealthy':
                return Edge(label=label, style="dashed", color="red")
            elif target_health == 'draining':
                return Edge(label=label, style="dashed", color="orange")
            else:
                return Edge(label=label, style="solid", color="blue")
    
    def should_render(self, load_balancer: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Determine if this ALB should be rendered based on filters."""
        # Use parent class basic filtering
        if not super().should_render(load_balancer, filters):
            return False
        
        # Check load balancer state
        state = load_balancer.get('state', {})
        if isinstance(state, dict):
            state_code = state.get('code', '').lower()
        else:
            state_code = str(state).lower()
        
        excluded_states = self.get_config_value('filters.exclude_states', ['failed'])
        if state_code in excluded_states:
            return False
        
        # Check scheme filters
        scheme = load_balancer.get('scheme', 'internet-facing')
        
        exclude_schemes = self.get_config_value('filters.exclude_schemes', [])
        if exclude_schemes and scheme in exclude_schemes:
            return False
        
        include_only_schemes = self.get_config_value('filters.include_only_schemes', [])
        if include_only_schemes and scheme not in include_only_schemes:
            return False
        
        # Check target count filters
        target_groups = load_balancer.get('target_groups', [])
        target_count = sum(len(tg.get('targets', [])) for tg in target_groups)
        
        min_targets = self.get_config_value('filters.min_target_count')
        max_targets = self.get_config_value('filters.max_target_count')
        
        if min_targets is not None and target_count < min_targets:
            return False
        if max_targets is not None and target_count > max_targets:
            return False
        
        return True
    
    def get_cluster_info(self, load_balancer: Dict[str, Any]) -> Dict[str, str]:
        """Get clustering information for this ALB."""
        cluster_by = self.get_config_value('clustering.group_by', 'scheme')
        
        if cluster_by == 'none':
            return {
                'cluster_type': 'none',
                'cluster_id': '',
                'cluster_label': ''
            }
        elif cluster_by == 'scheme':
            scheme = load_balancer.get('scheme', 'internet-facing')
            label_template = self.get_config_value('clustering.cluster_label_format', '{scheme} Load Balancers')
            return {
                'cluster_type': 'scheme',
                'cluster_id': scheme,
                'cluster_label': label_template.format(scheme=scheme.replace('-', ' ').title())
            }
        elif cluster_by == 'vpc':
            vpc_id = load_balancer.get('vpc_id', 'default-vpc')
            return {
                'cluster_type': 'vpc',
                'cluster_id': vpc_id,
                'cluster_label': f'VPC: {vpc_id}'
            }
        elif cluster_by == 'availability_zone':
            # Use first AZ for clustering
            azs = load_balancer.get('availability_zones', [])
            az = azs[0]['zone_name'] if azs and isinstance(azs[0], dict) else 'unknown-az'
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
        """Get ALB-specific variables for label formatting."""
        state = resource.get('state', {})
        return {
            'dns_name': resource.get('dns_name', ''),
            'scheme': resource.get('scheme', ''),
            'type': resource.get('type', 'application'),
            'state': state.get('code', '') if isinstance(state, dict) else str(state),
            'vpc_id': resource.get('vpc_id', '')
        }
    
    def get_metadata(self, load_balancer: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for tooltips or additional info."""
        state = load_balancer.get('state', {})
        
        return {
            'load_balancer_name': load_balancer.get('name', load_balancer.get('load_balancer_name')),
            'dns_name': load_balancer.get('dns_name'),
            'canonical_hosted_zone_id': load_balancer.get('canonical_hosted_zone_id'),
            'created_time': load_balancer.get('created_time'),
            'scheme': load_balancer.get('scheme'),
            'type': load_balancer.get('type'),
            'state': state.get('code') if isinstance(state, dict) else str(state),
            'vpc_id': load_balancer.get('vpc_id'),
            'availability_zones': load_balancer.get('availability_zones', []),
            'security_groups': load_balancer.get('security_groups', []),
            'ip_address_type': load_balancer.get('ip_address_type'),
            'target_groups': len(load_balancer.get('target_groups', [])),
            'listeners': len(load_balancer.get('listeners', [])),
            'tags': load_balancer.get('tags', {})
        }


def list_resources(aws_client: AWSClient, config: Dict[str, Any]) -> Iterator[Resource]:
    """
    Discover Application Load Balancers in the configured region.
    
    Args:
        aws_client: Configured AWS client manager
        config: Snippet configuration for filtering
        
    Yields:
        Resource objects representing ALBs
    """
    # Get filter configuration
    exclude_states = config.get('filters', {}).get('exclude_states', ['failed'])
    exclude_schemes = config.get('filters', {}).get('exclude_schemes', [])
    include_only_schemes = config.get('filters', {}).get('include_only_schemes', [])
    min_targets = config.get('filters', {}).get('min_target_count')
    max_targets = config.get('filters', {}).get('max_target_count')
    
    for page in aws_client.paginate('elbv2', 'describe_load_balancers'):
        for lb in page.get('LoadBalancers', []):
            # Filter to only Application Load Balancers
            lb_type = lb.get('Type', '')
            if lb_type.lower() != 'application':
                continue
            
            # Apply state filters
            state = lb.get('State', {})
            state_code = state.get('Code', '').lower() if isinstance(state, dict) else str(state).lower()
            if state_code in exclude_states:
                continue
            
            # Apply scheme filters
            scheme = lb.get('Scheme', 'internet-facing')
            
            if exclude_schemes and scheme in exclude_schemes:
                continue
            
            if include_only_schemes and scheme not in include_only_schemes:
                continue
            
            # Extract basic info
            id_key = 'LoadBalancerArn'
            lb_arn = lb[id_key]
            lb_name = lb.get('LoadBalancerName', lb_arn.split('/')[-2] if '/' in lb_arn else lb_arn)
            
            # Process tags
            tags_response = aws_client.describe_single(
                'elbv2',
                'describe_tags',
                ResourceArns=[lb_arn]
            )
            
            tags = {}
            if tags_response and 'TagDescriptions' in tags_response:
                for tag_desc in tags_response['TagDescriptions']:
                    if tag_desc.get('ResourceArn') == lb_arn:
                        tags = aws_client.process_tags(tag_desc.get('Tags', []))
                        break
            
            # Get target groups for target count filtering
            target_groups_response = aws_client.describe_single(
                'elbv2',
                'describe_target_groups',
                LoadBalancerArn=lb_arn
            )
            
            target_groups = []
            total_targets = 0
            
            if target_groups_response and 'TargetGroups' in target_groups_response:
                target_groups = target_groups_response['TargetGroups']
                
                # Count targets across all target groups
                for tg in target_groups:
                    tg_arn = tg.get('TargetGroupArn')
                    if tg_arn:
                        targets_response = aws_client.describe_single(
                            'elbv2',
                            'describe_target_health',
                            TargetGroupArn=tg_arn
                        )
                        if targets_response and 'TargetHealthDescriptions' in targets_response:
                            total_targets += len(targets_response['TargetHealthDescriptions'])
            
            # Apply target count filters
            if min_targets is not None and total_targets < min_targets:
                continue
            if max_targets is not None and total_targets > max_targets:
                continue
            
            # Get listeners
            listeners_response = aws_client.describe_single(
                'elbv2',
                'describe_listeners',
                LoadBalancerArn=lb_arn
            )
            
            listeners = []
            if listeners_response and 'Listeners' in listeners_response:
                listeners = listeners_response['Listeners']
            
            yield Resource(
                type='aws.elb.alb',
                id=lb_arn,
                id_key=id_key,
                _raw=lb,
                # Normalized fields for diagram generation
                name=lb_name,
                state=state_code,
                vpc_id=lb.get('VpcId'),
                tags=tags,
                # ALB-specific fields
                load_balancer_name=lb_name,
                dns_name=lb.get('DNSName'),
                canonical_hosted_zone_id=lb.get('CanonicalHostedZoneId'),
                created_time=lb.get('CreatedTime'),
                scheme=scheme,
                lb_type=lb_type,
                ip_address_type=lb.get('IpAddressType'),
                availability_zones=lb.get('AvailabilityZones', []),
                security_groups=lb.get('SecurityGroups', []),
                target_groups=target_groups,
                listeners=listeners
            )