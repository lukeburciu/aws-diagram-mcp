"""Classic Load Balancer (CLB) snippet for diagram generation."""

from typing import Dict, Any, Optional, Iterator
from diagrams.aws.network import ELB
from diagrams import Edge

from ...base import ConfiguredSnippet
from ...utils.discovery import Resource, AWSClient


class ClassicLBSnippet(ConfiguredSnippet):
    """Snippet for rendering Classic Load Balancers in diagrams."""
    
    def __init__(
        self,
        service: str = 'elb',
        resource_type: str = 'classic',
        config_loader=None,
        cli_overrides: Optional[Dict[str, Any]] = None
    ):
        """Initialize Classic LB snippet."""
        super().__init__(service, resource_type, config_loader, cli_overrides)
    
    def create_node(self, load_balancer: Dict[str, Any]) -> Any:
        """Create a diagram node for a Classic ELB."""
        # Generate the label
        label = self._generate_label(load_balancer)
        
        # Create and return the node
        return ELB(label)
    
    def _generate_label(self, load_balancer: Dict[str, Any]) -> str:
        """Generate label for Classic ELB based on configuration."""
        # Extract load balancer properties
        name = load_balancer.get('name', load_balancer.get('load_balancer_name', 'Unknown'))
        dns_name = load_balancer.get('dns_name', '')
        scheme = load_balancer.get('scheme', 'internet-facing')
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
            vpc_id=vpc_id
        )
        label_parts.append(primary_label)
        
        # Secondary label (usually scheme)
        if self.get_config_value('display.show_scheme', True) and scheme:
            secondary_template = self.get_config_value('label.secondary_format', '{scheme}')
            secondary_label = secondary_template.format(
                scheme=scheme.replace('-', ' ').title(),
                name=name
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
        
        # Show listener count with protocols
        if self.get_config_value('display.show_listeners', True):
            listeners = load_balancer.get('listeners', [])
            if listeners:
                protocols = set()
                for listener in listeners:
                    protocol = listener.get('protocol', 'HTTP')
                    protocols.add(protocol)
                
                if len(protocols) == 1:
                    additional.append(f"{len(listeners)} {list(protocols)[0]} listeners")
                else:
                    additional.append(f"{len(listeners)} listeners")
        
        # Show instance count
        if self.get_config_value('display.show_instances', True):
            instances = load_balancer.get('instances', [])
            if instances:
                additional.append(f"{len(instances)} instances")
        
        # Show availability zones
        if self.get_config_value('display.show_availability_zones', False):
            azs = load_balancer.get('availability_zones', [])
            if azs:
                az_count = len(azs)
                additional.append(f"{az_count} AZ" + ("s" if az_count > 1 else ""))
        
        # Show health check info
        if self.get_config_value('display.show_health_checks', True):
            health_check = load_balancer.get('health_check', {})
            if health_check:
                target = health_check.get('target', '')
                if target:
                    # Parse target like "HTTP:80/health"
                    if ':' in target:
                        protocol_port = target.split('/')[0]  # "HTTP:80"
                        additional.append(f"HC: {protocol_port}")
        
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
        """Create a connection edge with Classic ELB-specific styling."""
        # Extract connection details
        port = connection_info.get('port', 80)
        protocol = connection_info.get('protocol', 'HTTP')
        connection_type = connection_info.get('type', 'instance')
        health_check = connection_info.get('health_check', {})
        
        # Generate label based on connection type
        if connection_type == 'health_check':
            target = health_check.get('target', f'{protocol}:{port}/')
            hc_format = self.get_config_value('connections.health_check_label_format', 'HC: {port}{path}')
            
            # Parse target like "HTTP:80/health"
            if ':' in target and '/' in target:
                port_path = target.split(':', 1)[1]  # "80/health"
                if '/' in port_path:
                    hc_port, path = port_path.split('/', 1)
                    path = '/' + path
                else:
                    hc_port, path = port_path, ''
            else:
                hc_port, path = port, ''
            
            label = hc_format.format(port=hc_port, path=path)
            return Edge(label=label, style="dotted", color="orange")
        else:
            # Regular instance connection
            label_format = self.get_config_value('connections.connection_label_format', '{port}/{protocol}')
            label = label_format.format(port=port, protocol=protocol)
            
            # Style based on instance health if available
            instance_health = connection_info.get('health', 'InService')
            if instance_health == 'OutOfService':
                return Edge(label=label, style="dashed", color="red")
            else:
                return Edge(label=label, style="solid", color="green")
    
    def should_render(self, load_balancer: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Determine if this Classic ELB should be rendered based on filters."""
        # Use parent class basic filtering
        if not super().should_render(load_balancer, filters):
            return False
        
        # Check scheme filters
        scheme = load_balancer.get('scheme', 'internet-facing')
        
        exclude_schemes = self.get_config_value('filters.exclude_schemes', [])
        if exclude_schemes and scheme in exclude_schemes:
            return False
        
        include_only_schemes = self.get_config_value('filters.include_only_schemes', [])
        if include_only_schemes and scheme not in include_only_schemes:
            return False
        
        # Check protocol filters
        exclude_protocols = self.get_config_value('filters.exclude_protocols', [])
        if exclude_protocols:
            listeners = load_balancer.get('listeners', [])
            listener_protocols = [l.get('protocol', 'HTTP') for l in listeners]
            
            # If all protocols are excluded, don't show this ELB
            if all(protocol in exclude_protocols for protocol in listener_protocols):
                return False
        
        # Check instance count filters
        instances = load_balancer.get('instances', [])
        instance_count = len(instances)
        
        min_instances = self.get_config_value('filters.min_instance_count')
        max_instances = self.get_config_value('filters.max_instance_count')
        
        if min_instances is not None and instance_count < min_instances:
            return False
        if max_instances is not None and instance_count > max_instances:
            return False
        
        return True
    
    def get_cluster_info(self, load_balancer: Dict[str, Any]) -> Dict[str, str]:
        """Get clustering information for this Classic ELB."""
        cluster_by = self.get_config_value('clustering.group_by', 'scheme')
        
        if cluster_by == 'none':
            return {
                'cluster_type': 'none',
                'cluster_id': '',
                'cluster_label': ''
            }
        elif cluster_by == 'scheme':
            scheme = load_balancer.get('scheme', 'internet-facing')
            label_template = self.get_config_value('clustering.cluster_label_format', '{scheme} Classic Load Balancers')
            return {
                'cluster_type': 'scheme',
                'cluster_id': scheme,
                'cluster_label': label_template.format(scheme=scheme.replace('-', ' ').title())
            }
        elif cluster_by == 'vpc':
            vpc_id = load_balancer.get('vpc_id', 'EC2-Classic')
            return {
                'cluster_type': 'vpc',
                'cluster_id': vpc_id,
                'cluster_label': f'VPC: {vpc_id}' if vpc_id != 'EC2-Classic' else 'EC2-Classic'
            }
        elif cluster_by == 'availability_zone':
            # Use first AZ for clustering
            azs = load_balancer.get('availability_zones', [])
            az = azs[0] if azs else 'unknown-az'
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
        """Get Classic ELB-specific variables for label formatting."""
        return {
            'dns_name': resource.get('dns_name', ''),
            'scheme': resource.get('scheme', ''),
            'vpc_id': resource.get('vpc_id', '')
        }
    
    def get_metadata(self, load_balancer: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for tooltips or additional info."""
        return {
            'load_balancer_name': load_balancer.get('name', load_balancer.get('load_balancer_name')),
            'dns_name': load_balancer.get('dns_name'),
            'canonical_hosted_zone_name': load_balancer.get('canonical_hosted_zone_name'),
            'canonical_hosted_zone_name_id': load_balancer.get('canonical_hosted_zone_name_id'),
            'created_time': load_balancer.get('created_time'),
            'scheme': load_balancer.get('scheme'),
            'vpc_id': load_balancer.get('vpc_id'),
            'subnets': load_balancer.get('subnets', []),
            'availability_zones': load_balancer.get('availability_zones', []),
            'security_groups': load_balancer.get('security_groups', []),
            'instances': len(load_balancer.get('instances', [])),
            'listeners': len(load_balancer.get('listeners', [])),
            'health_check': load_balancer.get('health_check', {}),
            'tags': load_balancer.get('tags', {})
        }


def list_resources(aws_client: AWSClient, config: Dict[str, Any]) -> Iterator[Resource]:
    """
    Discover Classic Load Balancers in the configured region.
    
    Args:
        aws_client: Configured AWS client manager
        config: Snippet configuration for filtering
        
    Yields:
        Resource objects representing Classic ELBs
    """
    # Get filter configuration
    exclude_schemes = config.get('filters', {}).get('exclude_schemes', [])
    include_only_schemes = config.get('filters', {}).get('include_only_schemes', [])
    exclude_protocols = config.get('filters', {}).get('exclude_protocols', [])
    min_instances = config.get('filters', {}).get('min_instance_count')
    max_instances = config.get('filters', {}).get('max_instance_count')
    
    for page in aws_client.paginate('elb', 'describe_load_balancers'):
        for lb in page.get('LoadBalancerDescriptions', []):
            # Apply scheme filters
            scheme = lb.get('Scheme', 'internet-facing')
            
            if exclude_schemes and scheme in exclude_schemes:
                continue
            
            if include_only_schemes and scheme not in include_only_schemes:
                continue
            
            # Check protocol filters
            listeners = lb.get('ListenerDescriptions', [])
            listener_protocols = []
            for listener_desc in listeners:
                listener = listener_desc.get('Listener', {})
                protocol = listener.get('Protocol', 'HTTP')
                listener_protocols.append(protocol)
            
            if exclude_protocols and listener_protocols:
                # If all protocols are excluded, skip this ELB
                if all(protocol in exclude_protocols for protocol in listener_protocols):
                    continue
            
            # Apply instance count filters
            instances = lb.get('Instances', [])
            instance_count = len(instances)
            
            if min_instances is not None and instance_count < min_instances:
                continue
            if max_instances is not None and instance_count > max_instances:
                continue
            
            # Extract basic info
            id_key = 'LoadBalancerName'
            lb_name = lb[id_key]
            
            # Process tags
            tags_response = aws_client.describe_single(
                'elb',
                'describe_tags',
                LoadBalancerNames=[lb_name]
            )
            
            tags = {}
            if tags_response and 'TagDescriptions' in tags_response:
                for tag_desc in tags_response['TagDescriptions']:
                    if tag_desc.get('LoadBalancerName') == lb_name:
                        tags = aws_client.process_tags(tag_desc.get('Tags', []))
                        break
            
            # Get health check configuration
            health_check = lb.get('HealthCheck', {})
            
            # Convert listeners to simplified format
            processed_listeners = []
            for listener_desc in listeners:
                listener = listener_desc.get('Listener', {})
                processed_listeners.append({
                    'protocol': listener.get('Protocol'),
                    'load_balancer_port': listener.get('LoadBalancerPort'),
                    'instance_protocol': listener.get('InstanceProtocol'),
                    'instance_port': listener.get('InstancePort'),
                    'ssl_certificate_id': listener.get('SSLCertificateId')
                })
            
            yield Resource(
                type='aws.elb.classic',
                id=lb_name,
                id_key=id_key,
                _raw=lb,
                # Normalized fields for diagram generation
                name=lb_name,
                state='active',  # Classic ELBs don't have explicit state
                vpc_id=lb.get('VPCId'),  # None for EC2-Classic
                tags=tags,
                # Classic ELB-specific fields
                load_balancer_name=lb_name,
                dns_name=lb.get('DNSName'),
                canonical_hosted_zone_name=lb.get('CanonicalHostedZoneName'),
                canonical_hosted_zone_name_id=lb.get('CanonicalHostedZoneNameID'),
                created_time=lb.get('CreatedTime'),
                scheme=scheme,
                subnets=lb.get('Subnets', []),
                availability_zones=lb.get('AvailabilityZones', []),
                security_groups=lb.get('SecurityGroups', []),
                instances=[inst.get('InstanceId') for inst in instances if inst.get('InstanceId')],
                listeners=processed_listeners,
                health_check=health_check
            )