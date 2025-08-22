"""ACM Certificate snippet for diagram generation."""

from typing import Dict, Any, Optional, Iterator
from diagrams.aws.security import ACM
from diagrams import Edge

from ...base import ConfiguredSnippet
from ....utils.discovery import Resource, AWSClient


class ACMCertificateSnippet(ConfiguredSnippet):
    """Snippet for rendering ACM certificates in diagrams."""
    
    def __init__(
        self,
        service: str = 'acm',
        resource_type: str = 'certificate',
        config_loader=None,
        cli_overrides: Optional[Dict[str, Any]] = None
    ):
        """Initialize ACM certificate snippet."""
        super().__init__(service, resource_type, config_loader, cli_overrides)
    
    def create_node(self, certificate: Dict[str, Any]) -> Any:
        """Create a diagram node for an ACM certificate."""
        # Generate the label
        label = self._generate_label(certificate)
        
        # Create and return the node
        return ACM(label)
    
    def _generate_label(self, certificate: Dict[str, Any]) -> str:
        """Generate label for ACM certificate based on configuration."""
        # Extract certificate properties
        domain = self._get_primary_domain(certificate)
        arn = certificate.get('certificate_arn', certificate.get('arn', ''))
        status = certificate.get('status', 'UNKNOWN')
        cert_type = certificate.get('type', certificate.get('certificate_type', 'AMAZON_ISSUED'))
        validation_method = certificate.get('domain_validation_options', [{}])[0].get('validation_method', '')
        expiration_date = certificate.get('not_after', '')
        serial_number = certificate.get('serial', '')
        key_algorithm = certificate.get('key_algorithm', '')
        
        # Build label parts
        label_parts = []
        
        # Primary label (usually the domain name)
        primary_template = self.get_config_value('label.primary_format', '{domain}')
        primary_label = primary_template.format(
            domain=domain,
            arn=arn.split('/')[-1] if arn else '',
            status=status,
            type=cert_type,
            validation_method=validation_method,
            expiration_date=expiration_date,
            serial_number=serial_number,
            key_algorithm=key_algorithm
        )
        label_parts.append(primary_label)
        
        # Secondary label (usually status)
        if self.get_config_value('display.show_status', True) and status:
            secondary_template = self.get_config_value('label.secondary_format', '{status}')
            secondary_label = secondary_template.format(
                status=status.replace('_', ' ').title(),
                domain=domain,
                type=cert_type
            )
            if secondary_label and secondary_label != primary_label:
                label_parts.append(secondary_label)
        
        # Tertiary label (optional)
        tertiary_template = self.get_config_value('label.tertiary_format', '')
        if tertiary_template:
            tertiary_label = tertiary_template.format(
                validation_method=validation_method,
                type=cert_type,
                key_algorithm=key_algorithm
            )
            if tertiary_label and tertiary_label not in label_parts:
                label_parts.append(tertiary_label)
        
        # Build additional attributes based on config
        additional = []
        
        # Show domain validation method
        if self.get_config_value('display.show_domain_validation', True) and validation_method:
            additional.append(f"{validation_method} validated")
        
        # Show subject alternative names (SANs)
        if self.get_config_value('display.show_subject_alternative_names', True):
            sans = self._get_subject_alternative_names(certificate)
            if sans:
                max_sans = self.get_config_value('domains.max_san_display', 3)
                displayed_sans = sans[:max_sans]
                if len(sans) > max_sans:
                    san_summary = f"+{len(displayed_sans)} domains"
                else:
                    san_summary = f"{len(sans)} domain" + ("s" if len(sans) > 1 else "")
                additional.append(san_summary)
        
        # Show expiration date if configured
        if self.get_config_value('display.show_expiration_date', False) and expiration_date:
            # Format expiration date (assuming it's a datetime string or object)
            if hasattr(expiration_date, 'strftime'):
                exp_str = expiration_date.strftime('%Y-%m-%d')
            else:
                exp_str = str(expiration_date)[:10]  # Take first 10 chars for date
            additional.append(f"Exp: {exp_str}")
        
        # Show key algorithm if configured
        if self.get_config_value('display.show_key_algorithm', False) and key_algorithm:
            additional.append(key_algorithm)
        
        # Show wildcard indicator
        if self.get_config_value('domains.show_wildcard_indicator', True) and domain.startswith('*.'):
            wildcard_indicator = self.get_config_value('domains.wildcard_indicator', '*..')
            if additional:
                additional[0] = f"{wildcard_indicator} {additional[0]}"
            else:
                additional.append(f"{wildcard_indicator} Wildcard")
        
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
    
    def _get_primary_domain(self, certificate: Dict[str, Any]) -> str:
        """Get the primary domain name for the certificate."""
        # Try domain_name first (common field)
        domain = certificate.get('domain_name', '')
        if domain:
            return domain
        
        # Try subject field
        subject = certificate.get('subject', '')
        if subject and 'CN=' in subject:
            # Extract CN from subject string like "CN=example.com,OU=..."
            cn_part = [part.strip() for part in subject.split(',') if part.strip().startswith('CN=')]
            if cn_part:
                return cn_part[0][3:]  # Remove "CN=" prefix
        
        # Try subject_alternative_names
        sans = self._get_subject_alternative_names(certificate)
        if sans:
            return sans[0]  # Return first SAN
        
        # Fallback to certificate ARN or ID
        arn = certificate.get('certificate_arn', certificate.get('arn', ''))
        if arn:
            return arn.split('/')[-1]  # Get last part of ARN
        
        return 'Unknown Domain'
    
    def _get_subject_alternative_names(self, certificate: Dict[str, Any]) -> list:
        """Get list of subject alternative names from certificate."""
        # Try subject_alternative_names field
        sans = certificate.get('subject_alternative_names', [])
        if sans:
            return sans
        
        # Try domain_validation_options for domains
        domain_options = certificate.get('domain_validation_options', [])
        if domain_options:
            return [opt.get('domain_name', '') for opt in domain_options if opt.get('domain_name')]
        
        return []
    
    def create_connection(
        self,
        from_node: Any,
        to_node: Any,
        connection_info: Dict[str, Any]
    ) -> Edge:
        """Create a connection edge with ACM-specific styling."""
        # Extract connection details
        connection_type = connection_info.get('type', 'tls')
        service = connection_info.get('service', 'unknown')
        
        # Generate label
        label_format = self.get_config_value('connections.connection_label_format', 'TLS')
        label = label_format
        
        # Style based on service type
        if service == 'load_balancer':
            return Edge(label=label, style="solid", color="green")
        elif service == 'cloudfront':
            return Edge(label=label, style="solid", color="orange")
        elif service == 'api_gateway':
            return Edge(label=label, style="solid", color="purple")
        else:
            return Edge(label=label, style="solid", color="blue")
    
    def should_render(self, certificate: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Determine if this ACM certificate should be rendered based on filters."""
        # Use parent class basic filtering
        if not super().should_render(certificate, filters):
            return False
        
        # Check certificate status
        status = certificate.get('status', '').upper()
        excluded_statuses = self.get_config_value('filters.exclude_statuses', ['EXPIRED', 'REVOKED', 'FAILED'])
        if status in excluded_statuses:
            return False
        
        # Check validation method filters
        domain_options = certificate.get('domain_validation_options', [])
        validation_method = domain_options[0].get('validation_method', '') if domain_options else ''
        
        exclude_methods = self.get_config_value('filters.exclude_validation_methods', [])
        if exclude_methods and validation_method in exclude_methods:
            return False
        
        include_only_methods = self.get_config_value('filters.include_only_validation_methods', [])
        if include_only_methods and validation_method not in include_only_methods:
            return False
        
        # Check certificate type filters
        cert_type = certificate.get('type', certificate.get('certificate_type', 'AMAZON_ISSUED'))
        
        exclude_types = self.get_config_value('filters.exclude_certificate_types', [])
        if exclude_types and cert_type in exclude_types:
            return False
        
        include_only_types = self.get_config_value('filters.include_only_certificate_types', [])
        if include_only_types and cert_type not in include_only_types:
            return False
        
        # Check wildcard certificate filters
        domain = self._get_primary_domain(certificate)
        is_wildcard = domain.startswith('*.')
        
        exclude_wildcard = self.get_config_value('filters.exclude_wildcard_certificates', False)
        if exclude_wildcard and is_wildcard:
            return False
        
        include_only_wildcard = self.get_config_value('filters.include_only_wildcard_certificates', False)
        if include_only_wildcard and not is_wildcard:
            return False
        
        return True
    
    def get_cluster_info(self, certificate: Dict[str, Any]) -> Dict[str, str]:
        """Get clustering information for this ACM certificate."""
        cluster_by = self.get_config_value('clustering.group_by', 'validation_method')
        
        if cluster_by == 'none':
            return {
                'cluster_type': 'none',
                'cluster_id': '',
                'cluster_label': ''
            }
        elif cluster_by == 'validation_method':
            domain_options = certificate.get('domain_validation_options', [])
            validation_method = domain_options[0].get('validation_method', 'UNKNOWN') if domain_options else 'UNKNOWN'
            label_template = self.get_config_value('clustering.cluster_label_format', '{method} Validated Certificates')
            return {
                'cluster_type': 'validation_method',
                'cluster_id': validation_method,
                'cluster_label': label_template.format(method=validation_method)
            }
        elif cluster_by == 'status':
            status = certificate.get('status', 'UNKNOWN')
            return {
                'cluster_type': 'status',
                'cluster_id': status,
                'cluster_label': f'{status.replace("_", " ").title()} Certificates'
            }
        elif cluster_by == 'domain':
            domain = self._get_primary_domain(certificate)
            # Group by root domain
            if self.get_config_value('domains.group_by_root_domain', False):
                # Extract root domain (e.g., example.com from subdomain.example.com)
                parts = domain.split('.')
                if len(parts) >= 2:
                    root_domain = '.'.join(parts[-2:])
                else:
                    root_domain = domain
                return {
                    'cluster_type': 'root_domain',
                    'cluster_id': root_domain,
                    'cluster_label': f'{root_domain} Certificates'
                }
            else:
                return {
                    'cluster_type': 'domain',
                    'cluster_id': domain,
                    'cluster_label': f'{domain} Certificate'
                }
        
        return {
            'cluster_type': 'none',
            'cluster_id': '',
            'cluster_label': ''
        }
    
    def get_label_variables(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Get ACM-specific variables for label formatting."""
        domain_options = resource.get('domain_validation_options', [])
        return {
            'domain': self._get_primary_domain(resource),
            'arn': resource.get('certificate_arn', resource.get('arn', '')),
            'status': resource.get('status', ''),
            'type': resource.get('type', resource.get('certificate_type', '')),
            'validation_method': domain_options[0].get('validation_method', '') if domain_options else '',
            'expiration_date': resource.get('not_after', ''),
            'serial_number': resource.get('serial', ''),
            'key_algorithm': resource.get('key_algorithm', '')
        }
    
    def get_metadata(self, certificate: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for tooltips or additional info."""
        return {
            'certificate_arn': certificate.get('certificate_arn', certificate.get('arn')),
            'domain_name': self._get_primary_domain(certificate),
            'subject_alternative_names': self._get_subject_alternative_names(certificate),
            'status': certificate.get('status'),
            'type': certificate.get('type', certificate.get('certificate_type')),
            'key_algorithm': certificate.get('key_algorithm'),
            'key_usage': certificate.get('key_usage', []),
            'extended_key_usage': certificate.get('extended_key_usage', []),
            'serial': certificate.get('serial'),
            'subject': certificate.get('subject'),
            'issuer': certificate.get('issuer'),
            'created_at': certificate.get('created_at'),
            'issued_at': certificate.get('issued_at'),
            'not_before': certificate.get('not_before'),
            'not_after': certificate.get('not_after'),
            'domain_validation_options': certificate.get('domain_validation_options', []),
            'certificate_transparency_logging_preference': certificate.get('certificate_transparency_logging_preference'),
            'tags': certificate.get('tags', {}),
            'in_use': certificate.get('in_use_by', [])
        }


def list_resources(aws_client: AWSClient, config: Dict[str, Any]) -> Iterator[Resource]:
    """
    Discover ACM certificates in the configured region.
    
    Args:
        aws_client: Configured AWS client manager
        config: Snippet configuration for filtering
        
    Yields:
        Resource objects representing ACM certificates
    """
    # Get filter configuration
    exclude_statuses = config.get('filters', {}).get('exclude_statuses', ['EXPIRED', 'REVOKED', 'FAILED'])
    exclude_validation_methods = config.get('filters', {}).get('exclude_validation_methods', [])
    include_only_validation_methods = config.get('filters', {}).get('include_only_validation_methods', [])
    exclude_certificate_types = config.get('filters', {}).get('exclude_certificate_types', [])
    include_only_certificate_types = config.get('filters', {}).get('include_only_certificate_types', [])
    exclude_wildcard = config.get('filters', {}).get('exclude_wildcard_certificates', False)
    include_only_wildcard = config.get('filters', {}).get('include_only_wildcard_certificates', False)
    
    for page in aws_client.paginate('acm', 'list_certificates'):
        for cert_summary in page.get('CertificateSummaryList', []):
            cert_arn = cert_summary.get('CertificateArn')
            if not cert_arn:
                continue
            
            # Get detailed certificate information
            cert_detail = aws_client.describe_single(
                'acm', 
                'describe_certificate',
                CertificateArn=cert_arn
            )
            
            if not cert_detail or 'Certificate' not in cert_detail:
                continue
                
            certificate = cert_detail['Certificate']
            
            # Apply status filters
            status = certificate.get('Status', '').upper()
            if status in exclude_statuses:
                continue
            
            # Apply validation method filters
            domain_options = certificate.get('DomainValidationOptions', [])
            validation_method = domain_options[0].get('ValidationMethod', '') if domain_options else ''
            
            if exclude_validation_methods and validation_method in exclude_validation_methods:
                continue
            
            if include_only_validation_methods and validation_method not in include_only_validation_methods:
                continue
            
            # Apply certificate type filters
            cert_type = certificate.get('Type', 'AMAZON_ISSUED')
            
            if exclude_certificate_types and cert_type in exclude_certificate_types:
                continue
            
            if include_only_certificate_types and cert_type not in include_only_certificate_types:
                continue
            
            # Apply wildcard filters
            domain_name = certificate.get('DomainName', '')
            is_wildcard = domain_name.startswith('*.')
            
            if exclude_wildcard and is_wildcard:
                continue
            
            if include_only_wildcard and not is_wildcard:
                continue
            
            # Extract basic info
            id_key = 'CertificateArn'
            certificate_arn = certificate[id_key]
            
            # Process tags
            tags = aws_client.process_tags(certificate.get('Tags', []))
            
            yield Resource(
                type='aws.acm.certificate',
                id=certificate_arn,
                id_key=id_key,
                _raw=certificate,
                # Normalized fields for diagram generation
                name=domain_name or certificate_arn.split('/')[-1],
                state=status.lower(),
                vpc_id=None,  # ACM certificates are not VPC-specific
                tags=tags,
                # ACM-specific fields
                certificate_arn=certificate_arn,
                domain_name=domain_name,
                subject_alternative_names=certificate.get('SubjectAlternativeNames', []),
                status=status,
                certificate_type=cert_type,
                key_algorithm=certificate.get('KeyAlgorithm'),
                serial=certificate.get('Serial'),
                subject=certificate.get('Subject'),
                issuer=certificate.get('Issuer'),
                created_at=certificate.get('CreatedAt'),
                issued_at=certificate.get('IssuedAt'),
                not_before=certificate.get('NotBefore'),
                not_after=certificate.get('NotAfter'),
                domain_validation_options=domain_options,
                certificate_transparency_logging_preference=certificate.get('Options', {}).get('CertificateTransparencyLoggingPreference'),
                in_use_by=certificate.get('InUseBy', [])
            )