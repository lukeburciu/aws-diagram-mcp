"""Configuration loader for YAML config files."""

import os
from ruamel.yaml import YAML
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Handles loading and merging configuration from multiple sources."""
    
    def __init__(self):
        self.config = {}
    
    def load_from_file(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from a YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            yaml = YAML(typ='safe')
            yaml.preserve_quotes = True
            
            with open(config_path, 'r') as f:
                config = yaml.load(f) or {}
            
            logger.info(f"Loaded configuration from {config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Invalid YAML in {config_path}: {e}")
            raise
    
    def load_default_config(self, provider: str) -> Dict[str, Any]:
        """Load default configuration for a provider.
        
        Args:
            provider: Provider name (e.g., 'aws', 'azure', 'gcp')
            
        Returns:
            Default configuration dictionary
        """
        # Try to find provider default config
        package_root = Path(__file__).parent.parent
        provider_config = package_root / "providers" / provider / "config.yaml"
        
        if provider_config.exists():
            return self.load_from_file(provider_config)
        
        # Return basic default config
        return {
            "diagram": {
                "output_format": "png",
                "layout": "hierarchical"
            },
            "naming_conventions": {
                "vpc_format": "{name} ({cidr})",
                "instance_format": "{name}\\n{type}\\n{ip}"
            },
            "resource_filters": {},
            "hierarchy_rules": {
                "group_by": ["region", "vpc", "subnet_tier"]
            },
            "visual_rules": {
                "icon_size": "medium",
                "show_connections": True,
                "connection_labels": "ports",
                "color_scheme": f"{provider}_official"
            }
        }
    
    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries.
        
        Args:
            *configs: Configuration dictionaries to merge (in order of precedence)
            
        Returns:
            Merged configuration dictionary
        """
        result = {}
        
        for config in configs:
            if config:
                result = self._deep_merge(result, config)
        
        return result
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge two dictionaries.
        
        Args:
            base: Base dictionary
            override: Dictionary to merge in (takes precedence)
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result


def load_config(
    provider: str,
    user_config_path: Optional[Union[str, Path]] = None,
    **override_values
) -> Dict[str, Any]:
    """Load configuration from multiple sources with precedence.
    
    Precedence order (highest to lowest):
    1. Explicit override values passed as kwargs
    2. User-provided config file
    3. Environment variables
    4. Provider default config
    
    Args:
        provider: Provider name (e.g., 'aws', 'azure', 'gcp') 
        user_config_path: Optional path to user configuration file
        **override_values: Explicit configuration overrides
        
    Returns:
        Merged configuration dictionary
    """
    loader = ConfigLoader()
    
    # 1. Load provider defaults
    default_config = loader.load_default_config(provider)
    
    # 2. Load environment-based overrides
    env_config = _load_env_config()
    
    # 3. Load user config file if provided
    user_config = {}
    if user_config_path:
        try:
            user_config = loader.load_from_file(user_config_path)
        except FileNotFoundError:
            logger.warning(f"User config file not found: {user_config_path}")
        except Exception as e:
            logger.error(f"Failed to load user config: {e}")
    
    # 4. Apply explicit overrides
    explicit_config = _build_config_from_overrides(**override_values)
    
    # Merge in precedence order
    final_config = loader.merge_configs(
        default_config,
        env_config,  
        user_config,
        explicit_config
    )
    
    logger.info(f"Loaded configuration for provider '{provider}'")
    return final_config


def _load_env_config() -> Dict[str, Any]:
    """Load configuration from environment variables.
    
    Returns:
        Configuration dictionary from environment variables
    """
    config = {}
    
    # Example environment variable mappings
    if os.getenv("CLOUD_DIAGRAM_OUTPUT_FORMAT"):
        config.setdefault("diagram", {})["output_format"] = os.getenv("CLOUD_DIAGRAM_OUTPUT_FORMAT")
    
    if os.getenv("CLOUD_DIAGRAM_ICON_SIZE"):
        config.setdefault("visual_rules", {})["icon_size"] = os.getenv("CLOUD_DIAGRAM_ICON_SIZE")
    
    return config


def _build_config_from_overrides(**kwargs) -> Dict[str, Any]:
    """Build configuration dictionary from explicit override values.
    
    Args:
        **kwargs: Configuration override values
        
    Returns:
        Configuration dictionary
    """
    config = {}
    
    # Map common CLI arguments to config structure
    if "output_format" in kwargs:
        config.setdefault("diagram", {})["output_format"] = kwargs["output_format"]
    
    if "show_connections" in kwargs:
        config.setdefault("visual_rules", {})["show_connections"] = kwargs["show_connections"]
    
    # Add more mappings as needed
    
    return config