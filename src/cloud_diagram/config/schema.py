"""Configuration schema validation."""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration dictionary against expected schema.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    errors = []
    
    # Validate diagram section
    if "diagram" in config:
        diagram_errors = _validate_diagram_section(config["diagram"])
        errors.extend(diagram_errors)
    
    # Validate naming_conventions section
    if "naming_conventions" in config:
        naming_errors = _validate_naming_conventions(config["naming_conventions"])
        errors.extend(naming_errors)
    
    # Validate visual_rules section
    if "visual_rules" in config:
        visual_errors = _validate_visual_rules(config["visual_rules"])
        errors.extend(visual_errors)
    
    # Validate hierarchy_rules section
    if "hierarchy_rules" in config:
        hierarchy_errors = _validate_hierarchy_rules(config["hierarchy_rules"])
        errors.extend(hierarchy_errors)
    
    if errors:
        error_msg = "Configuration validation failed:\\n" + "\\n".join(errors)
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("Configuration validation passed")
    return True


def _validate_diagram_section(diagram: Dict[str, Any]) -> List[str]:
    """Validate diagram configuration section."""
    errors = []
    
    if "output_format" in diagram:
        valid_formats = ["png", "svg", "pdf", "dot"]
        if diagram["output_format"] not in valid_formats:
            errors.append(f"Invalid output_format: {diagram['output_format']}. Must be one of: {valid_formats}")
    
    if "layout" in diagram:
        valid_layouts = ["hierarchical", "flat", "circular"]
        if diagram["layout"] not in valid_layouts:
            errors.append(f"Invalid layout: {diagram['layout']}. Must be one of: {valid_layouts}")
    
    return errors


def _validate_naming_conventions(naming: Dict[str, Any]) -> List[str]:
    """Validate naming conventions configuration."""
    errors = []
    
    # Check that format strings contain valid placeholders
    required_placeholders = {
        "vpc_format": ["{name}", "{cidr}"],
        "instance_format": ["{name}", "{type}"],
        "subnet_format": ["{name}", "{cidr}"]
    }
    
    for key, required_vars in required_placeholders.items():
        if key in naming:
            format_str = naming[key]
            for var in required_vars:
                if var not in format_str and var.replace("{", "").replace("}", "") not in format_str:
                    logger.warning(f"Format string '{key}' missing recommended placeholder: {var}")
    
    return errors


def _validate_visual_rules(visual: Dict[str, Any]) -> List[str]:
    """Validate visual rules configuration."""
    errors = []
    
    if "icon_size" in visual:
        valid_sizes = ["small", "medium", "large"]
        if visual["icon_size"] not in valid_sizes:
            errors.append(f"Invalid icon_size: {visual['icon_size']}. Must be one of: {valid_sizes}")
    
    if "show_connections" in visual:
        if not isinstance(visual["show_connections"], bool):
            errors.append(f"show_connections must be boolean, got: {type(visual['show_connections'])}")
    
    if "connection_labels" in visual:
        valid_labels = ["none", "minimal", "ports", "protocols", "full"]
        if visual["connection_labels"] not in valid_labels:
            errors.append(f"Invalid connection_labels: {visual['connection_labels']}. Must be one of: {valid_labels}")
    
    return errors


def _validate_hierarchy_rules(hierarchy: Dict[str, Any]) -> List[str]:
    """Validate hierarchy rules configuration."""
    errors = []
    
    if "group_by" in hierarchy:
        if not isinstance(hierarchy["group_by"], list):
            errors.append(f"group_by must be a list, got: {type(hierarchy['group_by'])}")
        else:
            valid_groups = ["region", "vpc", "subnet", "subnet_tier", "availability_zone"]
            for group in hierarchy["group_by"]:
                if group not in valid_groups:
                    errors.append(f"Invalid group_by value: {group}. Must be one of: {valid_groups}")
    
    if "subnet_tiers" in hierarchy:
        if not isinstance(hierarchy["subnet_tiers"], dict):
            errors.append(f"subnet_tiers must be a dictionary, got: {type(hierarchy['subnet_tiers'])}")
    
    return errors


def get_config_template(provider: str) -> Dict[str, Any]:
    """Get a configuration template for a specific provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Configuration template dictionary
    """
    return {
        "diagram": {
            "output_format": "png",
            "layout": "hierarchical",
            "title": f"{provider.upper()} Infrastructure Diagram"
        },
        "naming_conventions": {
            "vpc_format": "{name} ({cidr})",
            "instance_format": "{name}\\n{type}\\n{ip}",
            "subnet_format": "{tier}: {name}\\n{cidr}",
            "database_format": "{name}\\n{engine} {version}\\n{instance_class}"
        },
        "resource_filters": {
            "exclude_tags": [],
            "include_only_regions": [],
            "exclude_resource_types": [],
            "max_resources_per_type": 100
        },
        "hierarchy_rules": {
            "group_by": ["region", "vpc", "subnet_tier"],
            "subnet_tiers": {
                "public": ["*public*", "*dmz*", "*web*"],
                "private": ["*private*", "*app*", "*application*"],
                "restricted": ["*db*", "*data*", "*database*"]
            }
        },
        "visual_rules": {
            "icon_size": "medium",
            "show_connections": True,
            "connection_labels": "ports",
            "color_scheme": f"{provider}_official",
            "layout_direction": "top_to_bottom",
            "cluster_padding": 20
        },
        "security_analysis": {
            "highlight_open_ports": True,
            "show_internet_gateways": True,
            "mark_public_resources": True,
            "connection_flows": "inter-subnet"
        }
    }