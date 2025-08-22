"""Provider registry for cloud diagram generation."""

import importlib
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Registry of available providers
PROVIDERS = {
    'aws': {
        'name': 'Amazon Web Services',
        'module': 'cloud_diagram.providers.aws',
        'discovery_class': 'AWSResourceDiscovery',
        'diagram_class': 'DiagramsGenerator'
    },
    # Future providers can be added here
    # 'azure': {
    #     'name': 'Microsoft Azure',
    #     'module': 'cloud_diagram.providers.azure',
    #     'discovery_class': 'AzureResourceDiscovery',
    #     'diagram_class': 'AzureDiagramGenerator'
    # },
    # 'gcp': {
    #     'name': 'Google Cloud Platform',
    #     'module': 'cloud_diagram.providers.gcp',
    #     'discovery_class': 'GCPResourceDiscovery',
    #     'diagram_class': 'GCPDiagramGenerator'
    # }
}


def list_providers() -> List[str]:
    """Get list of available providers.
    
    Returns:
        List of provider names
    """
    return list(PROVIDERS.keys())


def get_provider_info(provider: str) -> Dict[str, Any]:
    """Get information about a specific provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Provider information dictionary
        
    Raises:
        ValueError: If provider is not supported
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Provider '{provider}' not supported. Available: {list_providers()}")
    
    return PROVIDERS[provider]


def get_provider(provider: str, **kwargs):
    """Get provider discovery and diagram generator classes.
    
    Args:
        provider: Provider name (e.g., 'aws', 'azure', 'gcp')
        **kwargs: Arguments passed to the provider classes
        
    Returns:
        Tuple of (discovery_instance, diagram_generator_class)
        
    Raises:
        ValueError: If provider is not supported
        ImportError: If provider module cannot be imported
    """
    provider_info = get_provider_info(provider)
    
    try:
        # Import the provider module
        module = importlib.import_module(provider_info['module'])
        
        # Get the discovery class
        discovery_class = getattr(module, provider_info['discovery_class'])
        discovery_instance = discovery_class(**kwargs)
        
        # Get the diagram generator class  
        diagram_class = getattr(module, provider_info['diagram_class'])
        
        return discovery_instance, diagram_class
        
    except ImportError as e:
        logger.error(f"Failed to import provider '{provider}': {e}")
        raise ImportError(f"Provider '{provider}' is not available. Please install required dependencies.")
    
    except AttributeError as e:
        logger.error(f"Provider '{provider}' is missing required classes: {e}")
        raise ImportError(f"Provider '{provider}' is not properly configured: {e}")


def get_provider_config_path(provider: str) -> Optional[str]:
    """Get the default configuration file path for a provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Path to provider config file, or None if not available
    """
    provider_info = get_provider_info(provider)
    module_path = provider_info['module'].replace('.', '/')
    
    # This would be something like: cloud_diagram/providers/aws/config.yaml
    return f"{module_path}/config.yaml"