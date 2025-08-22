"""Hierarchical configuration loader with deep merge support."""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import yaml
from collections.abc import Mapping
from copy import deepcopy

logger = logging.getLogger(__name__)


class ConfigMergeError(Exception):
    """Exception raised when configuration merge fails."""
    pass


class HierarchicalConfigLoader:
    """Load and merge configurations from multiple sources with precedence."""
    
    # Configuration precedence (lowest to highest priority)
    CONFIG_HIERARCHY = [
        'snippet',      # Lowest: snippet-level defaults
        'provider',     # Provider-level overrides
        'project',      # Project-level overrides
        'user',         # User-level overrides
        'cli'           # Highest: CLI arguments
    ]
    
    def __init__(self, provider: str = 'aws'):
        self.provider = provider
        self.configs: Dict[str, Dict[str, Any]] = {}
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        
    def load_snippet_config(self, service: str, resource_type: str) -> Dict[str, Any]:
        """Load snippet-specific default configuration."""
        cache_key = f"snippet.{service}.{resource_type}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        # Find snippet config file
        snippet_path = self._find_snippet_config_path(service, resource_type)
        
        config = {}
        if snippet_path and snippet_path.exists():
            try:
                with open(snippet_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
                logger.debug(f"Loaded snippet config from {snippet_path}")
            except (yaml.YAMLError, IOError) as e:
                logger.warning(f"Failed to load snippet config {snippet_path}: {e}")
        
        self._config_cache[cache_key] = config
        return config
    
    def _find_snippet_config_path(self, service: str, resource_type: str) -> Optional[Path]:
        """Find the snippet config file path."""
        # Start from this file's directory and work up to find snippets
        current_dir = Path(__file__).parent
        
        # Try to find the snippets directory
        while current_dir.name != 'aws' and current_dir != current_dir.parent:
            current_dir = current_dir.parent
            
        if current_dir.name == 'aws':
            snippets_dir = current_dir / 'snippets'
            config_path = snippets_dir / service / resource_type / 'config.yaml'
            return config_path
            
        return None
    
    def load_provider_config(self) -> Dict[str, Any]:
        """Load provider-level configuration."""
        cache_key = "provider"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        config = {}
        
        # Find provider config file
        current_dir = Path(__file__).parent
        while current_dir.name != 'aws' and current_dir != current_dir.parent:
            current_dir = current_dir.parent
            
        if current_dir.name == 'aws':
            provider_path = current_dir / 'config.yaml'
            if provider_path.exists():
                try:
                    with open(provider_path, 'r') as f:
                        full_config = yaml.safe_load(f) or {}
                        # Extract snippet-specific overrides
                        config = full_config.get('aws', {}).get('snippets', {})
                    logger.debug(f"Loaded provider config from {provider_path}")
                except (yaml.YAMLError, IOError) as e:
                    logger.warning(f"Failed to load provider config {provider_path}: {e}")
        
        self._config_cache[cache_key] = config
        return config
    
    def load_project_config(self) -> Dict[str, Any]:
        """Load project-level configuration."""
        cache_key = "project"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        config = {}
        
        # Search for config file in current directory and parent directories
        current = Path.cwd()
        
        config_names = [
            'cloud_diagram_config.yaml',
            'cloud_diagram.yaml',
            '.cloud_diagram.yaml'
        ]
        
        while current != current.parent:
            for config_name in config_names:
                config_path = current / config_name
                if config_path.exists():
                    try:
                        with open(config_path, 'r') as f:
                            full_config = yaml.safe_load(f) or {}
                            config = (full_config
                                    .get('providers', {})
                                    .get(self.provider, {})
                                    .get('snippets', {}))
                        logger.debug(f"Loaded project config from {config_path}")
                        break
                    except (yaml.YAMLError, IOError) as e:
                        logger.warning(f"Failed to load project config {config_path}: {e}")
            else:
                current = current.parent
                continue
            break
        
        self._config_cache[cache_key] = config
        return config
    
    def load_user_config(self) -> Dict[str, Any]:
        """Load user-level configuration from XDG_CONFIG_HOME."""
        cache_key = "user"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        config = {}
        
        # Get XDG config directory
        xdg_config = os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')
        user_config_path = Path(xdg_config) / 'cloud_diagram' / 'config.yaml'
        
        if user_config_path.exists():
            try:
                with open(user_config_path, 'r') as f:
                    full_config = yaml.safe_load(f) or {}
                    config = (full_config
                            .get('providers', {})
                            .get(self.provider, {})
                            .get('snippets', {}))
                logger.debug(f"Loaded user config from {user_config_path}")
            except (yaml.YAMLError, IOError) as e:
                logger.warning(f"Failed to load user config {user_config_path}: {e}")
        
        self._config_cache[cache_key] = config
        return config
    
    def deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries, with override taking precedence.
        
        Merge rules:
        - Dictionaries are merged recursively
        - Lists are replaced (not concatenated)
        - None values in override remove the key
        - All other values replace
        
        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary
            
        Returns:
            Merged configuration dictionary
            
        Raises:
            ConfigMergeError: If merge operation fails
        """
        try:
            result = deepcopy(base)
            
            for key, value in override.items():
                if value is None:
                    # None means remove this key
                    result.pop(key, None)
                elif (key in result and 
                      isinstance(result[key], Mapping) and 
                      isinstance(value, Mapping)):
                    # Recursively merge dictionaries
                    result[key] = self.deep_merge(result[key], value)
                else:
                    # Replace value (including lists)
                    result[key] = deepcopy(value)
                    
            return result
            
        except Exception as e:
            raise ConfigMergeError(f"Failed to merge configurations: {e}") from e
    
    def get_snippet_config(
        self,
        service: str,
        resource_type: str,
        cli_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get the final merged configuration for a snippet.
        
        Args:
            service: Service name (e.g., 'rds', 'ec2')
            resource_type: Resource type (e.g., 'db_instance', 'instance')
            cli_overrides: Optional CLI argument overrides
            
        Returns:
            Merged configuration dictionary
        """
        try:
            # Start with snippet defaults
            config = self.load_snippet_config(service, resource_type)
            
            # Load provider-level overrides
            provider_config = self.load_provider_config()
            if service in provider_config and resource_type in provider_config[service]:
                config = self.deep_merge(config, provider_config[service][resource_type])
            
            # Load project-level overrides
            project_config = self.load_project_config()
            if service in project_config and resource_type in project_config[service]:
                config = self.deep_merge(config, project_config[service][resource_type])
            
            # Load user-level overrides  
            user_config = self.load_user_config()
            if service in user_config and resource_type in user_config[service]:
                config = self.deep_merge(config, user_config[service][resource_type])
            
            # Apply CLI overrides (highest priority)
            if cli_overrides:
                config = self.deep_merge(config, cli_overrides)
                
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config for {service}.{resource_type}: {e}")
            return {}
    
    def get_global_config(self, cli_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get global configuration that applies to all snippets."""
        try:
            config = {}
            
            # Load provider global config
            current_dir = Path(__file__).parent
            while current_dir.name != 'aws' and current_dir != current_dir.parent:
                current_dir = current_dir.parent
                
            if current_dir.name == 'aws':
                provider_path = current_dir / 'config.yaml'
                if provider_path.exists():
                    try:
                        with open(provider_path, 'r') as f:
                            provider_config = yaml.safe_load(f) or {}
                            if 'aws' in provider_config and 'global' in provider_config['aws']:
                                config = self.deep_merge(config, provider_config['aws']['global'])
                    except (yaml.YAMLError, IOError) as e:
                        logger.warning(f"Failed to load global provider config: {e}")
            
            # Load project global config
            project_config = self.load_project_config()
            if 'global' in project_config:
                config = self.deep_merge(config, project_config['global'])
            
            # Load user global config
            user_config = self.load_user_config()
            if 'global' in user_config:
                config = self.deep_merge(config, user_config['global'])
            
            # Apply CLI overrides
            if cli_overrides:
                config = self.deep_merge(config, cli_overrides)
                
            return config
            
        except Exception as e:
            logger.error(f"Failed to load global config: {e}")
            return {}
    
    def clear_cache(self):
        """Clear the configuration cache."""
        self._config_cache.clear()
    
    def get_config_sources(self, service: str, resource_type: str) -> List[Dict[str, Any]]:
        """
        Get information about configuration sources for debugging.
        
        Returns:
            List of dicts with 'source', 'path', and 'exists' keys
        """
        sources = []
        
        # Snippet config
        snippet_path = self._find_snippet_config_path(service, resource_type)
        sources.append({
            'source': 'snippet',
            'path': str(snippet_path) if snippet_path else 'N/A',
            'exists': snippet_path.exists() if snippet_path else False
        })
        
        # Provider config
        current_dir = Path(__file__).parent
        while current_dir.name != 'aws' and current_dir != current_dir.parent:
            current_dir = current_dir.parent
        provider_path = current_dir / 'config.yaml' if current_dir.name == 'aws' else None
        sources.append({
            'source': 'provider',
            'path': str(provider_path) if provider_path else 'N/A',
            'exists': provider_path.exists() if provider_path else False
        })
        
        # Project config
        current = Path.cwd()
        config_names = ['cloud_diagram_config.yaml', 'cloud_diagram.yaml', '.cloud_diagram.yaml']
        project_path = None
        while current != current.parent:
            for config_name in config_names:
                config_path = current / config_name
                if config_path.exists():
                    project_path = config_path
                    break
            if project_path:
                break
            current = current.parent
        
        sources.append({
            'source': 'project',
            'path': str(project_path) if project_path else 'N/A',
            'exists': project_path.exists() if project_path else False
        })
        
        # User config
        xdg_config = os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')
        user_path = Path(xdg_config) / 'cloud_diagram' / 'config.yaml'
        sources.append({
            'source': 'user',
            'path': str(user_path),
            'exists': user_path.exists()
        })
        
        return sources