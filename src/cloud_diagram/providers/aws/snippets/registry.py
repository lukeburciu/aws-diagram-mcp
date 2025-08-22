"""Registry for AWS diagram snippets."""

from typing import Dict, Any, Optional, Type
import logging
from pathlib import Path

from .base import BaseSnippet

logger = logging.getLogger(__name__)


class SnippetRegistry:
    """Registry for loading and managing AWS service snippets."""
    
    def __init__(self, config_loader=None):
        self._snippets: Dict[str, Dict[str, Type[BaseSnippet]]] = {}
        self._instances: Dict[str, BaseSnippet] = {}
        self.config_loader = config_loader
        
        # Register built-in snippets
        self._register_builtin_snippets()
    
    def _register_builtin_snippets(self):
        """Register all built-in AWS service snippets."""
        # Import and register snippet classes
        try:
            from .rds.db_instance import RDSInstanceSnippet
            self.register('rds', 'db_instance', RDSInstanceSnippet)
        except ImportError as e:
            logger.debug(f"RDS snippet not available: {e}")
        
        try:
            from .ec2.instance import EC2InstanceSnippet
            self.register('ec2', 'instance', EC2InstanceSnippet)
        except ImportError:
            logger.debug("EC2 snippet not available")
        
        try:
            from .elb.alb import ALBSnippet
            self.register('elb', 'alb', ALBSnippet)
        except ImportError:
            logger.debug("ALB snippet not available")
            
        try:
            from .elb.nlb import NLBSnippet
            self.register('elb', 'nlb', NLBSnippet)
        except ImportError:
            logger.debug("NLB snippet not available")
            
        try:
            from .elb.classic import ClassicLBSnippet
            self.register('elb', 'classic', ClassicLBSnippet)
        except ImportError:
            logger.debug("Classic LB snippet not available")
        
        try:
            from .route53.hosted_zone import Route53ZoneSnippet
            self.register('route53', 'hosted_zone', Route53ZoneSnippet)
        except ImportError:
            logger.debug("Route53 snippet not available")
        
        try:
            from .acm.certificate import ACMCertificateSnippet
            self.register('acm', 'certificate', ACMCertificateSnippet)
        except ImportError:
            logger.debug("ACM snippet not available")
    
    def register(
        self,
        service: str,
        resource_type: str,
        snippet_class: Type[BaseSnippet]
    ):
        """Register a snippet class for a service/resource type."""
        if service not in self._snippets:
            self._snippets[service] = {}
        
        self._snippets[service][resource_type] = snippet_class
        logger.debug(f"Registered snippet: {service}.{resource_type}")
    
    def get_snippet(
        self,
        service: str,
        resource_type: str,
        cli_overrides: Optional[Dict[str, Any]] = None
    ) -> BaseSnippet:
        """
        Get a snippet instance for a service/resource type.
        
        Args:
            service: AWS service name (e.g., 'rds', 'ec2')
            resource_type: Resource type (e.g., 'db_instance', 'instance')
            cli_overrides: Optional CLI configuration overrides
            
        Returns:
            Configured snippet instance
            
        Raises:
            KeyError: If snippet not found
        """
        cache_key = f"{service}.{resource_type}"
        
        # Return cached instance if no CLI overrides
        if cli_overrides is None and cache_key in self._instances:
            return self._instances[cache_key]
        
        # Get snippet class
        if service not in self._snippets or resource_type not in self._snippets[service]:
            raise KeyError(f"No snippet registered for {service}.{resource_type}")
        
        snippet_class = self._snippets[service][resource_type]
        
        # Create instance with configuration
        instance = snippet_class(
            service=service,
            resource_type=resource_type,
            config_loader=self.config_loader,
            cli_overrides=cli_overrides
        )
        
        # Cache instance if no CLI overrides
        if cli_overrides is None:
            self._instances[cache_key] = instance
        
        return instance
    
    def has_snippet(self, service: str, resource_type: str) -> bool:
        """Check if a snippet is registered for service/resource type."""
        return (service in self._snippets and 
                resource_type in self._snippets[service])
    
    def list_snippets(self) -> Dict[str, list]:
        """List all registered snippets by service."""
        result = {}
        for service, resource_types in self._snippets.items():
            result[service] = list(resource_types.keys())
        return result
    
    def get_snippet_path(self, service: str, resource_type: str) -> Path:
        """Get the filesystem path for a snippet's config directory."""
        snippets_dir = Path(__file__).parent
        return snippets_dir / service / resource_type