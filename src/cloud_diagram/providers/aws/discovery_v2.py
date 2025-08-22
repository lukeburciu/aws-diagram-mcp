"""Modular AWS discovery using snippet-specific logic."""

import logging
import importlib
from typing import Dict, List, Iterator, Optional, Tuple, Any
from collections import defaultdict

from .utils.discovery import AWSClient, Resource
from .snippets import SnippetRegistry

logger = logging.getLogger(__name__)


class ModularAWSDiscovery:
    """Modular discovery using snippet-specific logic."""
    
    def __init__(self, region: str = 'us-east-1', profile: Optional[str] = None):
        """
        Initialize modular discovery system.
        
        Args:
            region: AWS region to discover in (single region)
            profile: AWS profile name to use
        """
        self.aws_client = AWSClient(region, profile)
        self.registry = SnippetRegistry()
        logger.info(f"Initialized modular discovery for region: {self.aws_client.region}")
    
    def discover_resources(
        self, 
        service: Optional[str] = None, 
        resource_type: Optional[str] = None
    ) -> Iterator[Resource]:
        """
        Discover resources using snippet discovery functions.
        
        Args:
            service: Optional service filter (e.g., 'rds', 'ec2')
            resource_type: Optional resource type filter (e.g., 'db_instance')
            
        Yields:
            Resource objects from matching snippets
        """
        snippets = self._get_snippets(service, resource_type)
        
        for snippet_service, snippet_type in snippets:
            try:
                # Get snippet instance for configuration
                snippet = self.registry.get_snippet(snippet_service, snippet_type)
                
                # Get snippet module to access list_resources function
                snippet_module = self._get_snippet_module(snippet_service, snippet_type)
                
                if hasattr(snippet_module, 'list_resources'):
                    logger.debug(f"Discovering {snippet_service}.{snippet_type} resources")
                    
                    # Get snippet config for filtering
                    config = snippet.config
                    
                    # Yield resources from this snippet
                    resource_count = 0
                    for resource in snippet_module.list_resources(self.aws_client, config):
                        resource_count += 1
                        yield resource
                    
                    logger.debug(f"Found {resource_count} {snippet_service}.{snippet_type} resources")
                else:
                    logger.debug(f"No list_resources function found for {snippet_service}.{snippet_type}")
                    
            except Exception as e:
                logger.error(f"Error discovering {snippet_service}.{snippet_type}: {e}")
                # Continue with other snippets
                continue
    
    def discover_all(self) -> Dict[str, List[Resource]]:
        """
        Discover all resources grouped by type.
        
        Returns:
            Dictionary mapping resource types to lists of resources
        """
        resources = defaultdict(list)
        
        total_resources = 0
        for resource in self.discover_resources():
            resources[resource.type].append(resource)
            total_resources += 1
        
        logger.info(f"Discovered {total_resources} total resources across {len(resources)} types")
        
        return dict(resources)
    
    def discover_by_service(self, service: str) -> Dict[str, List[Resource]]:
        """
        Discover all resources for a specific service.
        
        Args:
            service: Service name (e.g., 'rds', 'ec2')
            
        Returns:
            Dictionary mapping resource types to lists of resources
        """
        resources = defaultdict(list)
        
        for resource in self.discover_resources(service=service):
            resources[resource.type].append(resource)
        
        return dict(resources)
    
    def discover_by_vpc(self, vpc_id: str) -> Dict[str, List[Resource]]:
        """
        Discover all resources in a specific VPC.
        
        Args:
            vpc_id: VPC identifier
            
        Returns:
            Dictionary mapping resource types to lists of resources
        """
        resources = defaultdict(list)
        
        for resource in self.discover_resources():
            if resource.vpc_id == vpc_id:
                resources[resource.type].append(resource)
        
        return dict(resources)
    
    def get_region(self) -> str:
        """
        Get the current region being used for discovery.
        
        Returns:
            Current AWS region
        """
        return self.aws_client.region
    
    def get_account_info(self) -> Dict[str, str]:
        """Get AWS account information."""
        return self.aws_client.get_account_info()
    
    def _get_snippets(
        self, 
        service: Optional[str] = None, 
        resource_type: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """
        Get list of (service, resource_type) tuples to discover.
        
        Args:
            service: Optional service filter
            resource_type: Optional resource type filter
            
        Returns:
            List of (service, resource_type) tuples
        """
        available_snippets = self.registry.list_snippets()
        snippets = []
        
        for snippet_service, resource_types in available_snippets.items():
            # Filter by service if specified
            if service and snippet_service != service:
                continue
                
            for snippet_type in resource_types:
                # Filter by resource type if specified
                if resource_type and snippet_type != resource_type:
                    continue
                    
                snippets.append((snippet_service, snippet_type))
        
        return snippets
    
    def _get_snippet_module(self, service: str, resource_type: str):
        """
        Import the snippet module to access list_resources function.
        
        Args:
            service: Service name
            resource_type: Resource type name
            
        Returns:
            Imported module
        """
        module_path = f'cloud_diagram.providers.aws.snippets.{service}.{resource_type}'
        try:
            return importlib.import_module(module_path)
        except ImportError as e:
            logger.error(f"Failed to import snippet module {module_path}: {e}")
            raise
    
    def list_available_snippets(self) -> Dict[str, List[str]]:
        """
        List all available snippets that support discovery.
        
        Returns:
            Dictionary mapping services to resource types that have list_resources
        """
        available = {}
        
        for service, resource_types in self.registry.list_snippets().items():
            available[service] = []
            
            for resource_type in resource_types:
                try:
                    snippet_module = self._get_snippet_module(service, resource_type)
                    if hasattr(snippet_module, 'list_resources'):
                        available[service].append(resource_type)
                except Exception:
                    # Skip snippets that can't be imported or don't have discovery
                    pass
            
            # Remove services with no discoverable resource types
            if not available[service]:
                del available[service]
        
        return available
    
    def validate_discovery_setup(self) -> Dict[str, Any]:
        """
        Validate that discovery system is properly configured.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'account_info': self.get_account_info(),
            'region': self.aws_client.region,
            'available_snippets': self.list_available_snippets(),
            'errors': []
        }
        
        # Test basic AWS connectivity
        if not results['account_info']:
            results['errors'].append("Failed to get AWS account information")
        
        # Test region connectivity
        try:
            self.aws_client.get_client('ec2')
        except Exception as e:
            results['errors'].append(f"Failed to create EC2 client for region {self.aws_client.region}: {e}")
        
        results['valid'] = len(results['errors']) == 0
        
        return results