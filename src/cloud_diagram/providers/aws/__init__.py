"""AWS provider for cloud diagram generation."""

from .discovery_v2 import ModularAWSDiscovery as AWSResourceDiscovery
from .diagram import DiagramsGenerator

__all__ = ["AWSResourceDiscovery", "DiagramsGenerator"]