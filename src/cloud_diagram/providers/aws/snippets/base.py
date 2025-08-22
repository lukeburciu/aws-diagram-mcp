"""Base classes for AWS diagram snippets."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from diagrams import Edge


class BaseSnippet(ABC):
    """Abstract base class for all AWS service snippets."""
    
    @abstractmethod
    def create_node(self, resource: Dict[str, Any]) -> Any:
        """Create a diagram node for this resource."""
        pass
    
    @abstractmethod
    def should_render(self, resource: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Determine if this resource should be rendered based on filters."""
        pass
    
    def create_connection(
        self,
        from_node: Any,
        to_node: Any,
        connection_info: Dict[str, Any]
    ) -> Edge:
        """Create a connection edge between nodes."""
        label = connection_info.get('label', '')
        style = connection_info.get('style', 'solid')
        color = connection_info.get('color', 'black')
        
        return Edge(label=label, style=style, color=color)
    
    def get_cluster_info(self, resource: Dict[str, Any]) -> Dict[str, str]:
        """Get clustering information for this resource."""
        return {
            'cluster_type': 'none',
            'cluster_id': '',
            'cluster_label': ''
        }
    
    def get_metadata(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for tooltips or additional info."""
        return {
            'resource_id': resource.get('id', 'unknown'),
            'resource_type': self.__class__.__name__,
            'tags': resource.get('tags', {})
        }


class ConfiguredSnippet(BaseSnippet):
    """Base class for snippets with hierarchical configuration support."""
    
    def __init__(
        self,
        service: str,
        resource_type: str,
        config_loader=None,
        cli_overrides: Optional[Dict[str, Any]] = None
    ):
        self.service = service
        self.resource_type = resource_type
        
        # Import here to avoid circular imports
        if config_loader is None:
            from cloud_diagram.providers.aws.config.hierarchical_loader import HierarchicalConfigLoader
            config_loader = HierarchicalConfigLoader()
            
        self.config_loader = config_loader
        self.config = self.config_loader.get_snippet_config(
            service, 
            resource_type,
            cli_overrides
        )
    
    def get_config_value(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            path: Dot-separated path to config value (e.g. 'display.show_endpoint')
            default: Default value if path not found
            
        Returns:
            Configuration value or default
        """
        keys = path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
                
        return value
    
    def format_label(
        self,
        resource: Dict[str, Any],
        template_key: str = 'label.primary_format',
        default_template: str = '{name}'
    ) -> str:
        """
        Format a label using configuration template and resource data.
        
        Args:
            resource: Resource data dictionary
            template_key: Config path to label template
            default_template: Default template if config not found
            
        Returns:
            Formatted label string
        """
        template = self.get_config_value(template_key, default_template)
        
        # Prepare variables for template formatting
        variables = {
            'name': resource.get('name', resource.get('id', 'Unknown')),
            'id': resource.get('id', ''),
            'tags': resource.get('tags', {}),
        }
        
        # Add resource-specific variables (overridden by subclasses)
        variables.update(self.get_label_variables(resource))
        
        try:
            return template.format(**variables)
        except KeyError as e:
            # If template variable not found, use default
            return default_template.format(**variables)
    
    def get_label_variables(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Get resource-specific variables for label formatting. Override in subclasses."""
        return {}
    
    def should_render(self, resource: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Default filtering logic using configuration."""
        # Check if resource is in excluded states
        excluded_states = self.get_config_value('filters.exclude_states', [])
        resource_state = resource.get('state', resource.get('status', '')).lower()
        
        if resource_state in excluded_states:
            return False
        
        # Check tag filters
        resource_tags = resource.get('tags', {})
        exclude_tags = filters.get('exclude_tags', {})
        
        for key, value in exclude_tags.items():
            if resource_tags.get(key) == value:
                return False
        
        return True