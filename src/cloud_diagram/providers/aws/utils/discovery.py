"""Core discovery utilities for AWS resources."""

from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, List
import boto3
import logging

logger = logging.getLogger(__name__)


@dataclass
class Resource:
    """Universal resource representation."""
    type: str        # e.g., 'aws.rds.db_instance'
    id: str          # Primary identifier
    id_key: str      # Field name for ID (e.g., 'DBInstanceIdentifier')
    _raw: Dict[str, Any]  # Original AWS API response
    
    # Additional normalized fields (set as needed)
    name: Optional[str] = None
    state: Optional[str] = None
    vpc_id: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        """Ensure we have basic fields."""
        if self.name is None:
            self.name = self.id
        if self.tags is None:
            self.tags = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from raw AWS response."""
        return self._raw.get(key, default)
    
    def has_tag(self, key: str, value: str = None) -> bool:
        """Check if resource has a specific tag."""
        if value is None:
            return key in self.tags
        return self.tags.get(key) == value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for diagram generation."""
        result = {
            'id': self.id,
            'name': self.name,
            'vpc_id': self.vpc_id,
            'state': self.state,
            'tags': self.tags
        }
        
        # Include all fields from _raw for backward compatibility
        result.update(self._raw)
        
        return result


class AWSClient:
    """Manages boto3 clients and provides paginated access."""
    
    def __init__(self, region: str = 'us-east-1', profile: Optional[str] = None):
        """
        Initialize AWS client manager.
        
        Args:
            region: AWS region to operate in
            profile: AWS profile name to use
        """
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.region = region
        self._clients = {}
        logger.debug(f"Initialized AWSClient for region: {self.region}")
    
    def get_client(self, service: str, use_global: bool = False):
        """
        Get or create a boto3 client.
        
        Args:
            service: AWS service name (e.g., 'ec2', 'rds')
            use_global: Whether to use no region (for global services like Route53)
            
        Returns:
            boto3 client instance
        """
        region = None if use_global else self.region
        key = f"{service}:{region or 'global'}"
        
        if key not in self._clients:
            try:
                self._clients[key] = self.session.client(
                    service, 
                    region_name=region
                )
                logger.debug(f"Created {service} client for region {region or 'global'}")
            except Exception as e:
                logger.error(f"Failed to create {service} client for region {region}: {e}")
                raise
                
        return self._clients[key]
    
    def paginate(self, service: str, operation: str, use_global: bool = False, **kwargs) -> Iterator[Dict[str, Any]]:
        """
        Paginate through AWS API responses.
        
        Args:
            service: AWS service name
            operation: API operation name
            use_global: Whether to use global client (for Route53, etc.)
            **kwargs: Additional parameters for the API call
            
        Yields:
            Page responses from AWS API
        """
        try:
            client = self.get_client(service, use_global)
            
            # Check if operation supports pagination
            if client.can_paginate(operation):
                paginator = client.get_paginator(operation)
                yield from paginator.paginate(**kwargs)
            else:
                # For non-paginated operations, call directly and wrap in list
                response = getattr(client, operation)(**kwargs)
                yield response
                
        except Exception as e:
            region = 'global' if use_global else self.region
            logger.error(f"Error paginating {service}.{operation} in region {region}: {e}")
            # Don't re-raise to allow other services to continue
    
    def describe_single(self, service: str, operation: str, use_global: bool = False, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Call a single describe operation (non-paginated).
        
        Args:
            service: AWS service name
            operation: API operation name
            use_global: Whether to use global client
            **kwargs: Additional parameters for the API call
            
        Returns:
            API response or None if error
        """
        try:
            client = self.get_client(service, use_global)
            return getattr(client, operation)(**kwargs)
        except Exception as e:
            region = 'global' if use_global else self.region
            logger.error(f"Error calling {service}.{operation} in region {region}: {e}")
            return None
    
    def get_account_info(self) -> Dict[str, str]:
        """Get AWS account information."""
        try:
            sts_client = self.get_client('sts', use_global=True)
            response = sts_client.get_caller_identity()
            return {
                "account_id": response["Account"],
                "arn": response["Arn"],
                "user_id": response["UserId"]
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
    
    def process_tags(self, tags_list: List[Dict[str, str]]) -> Dict[str, str]:
        """
        Convert AWS tags list to dictionary.
        
        Args:
            tags_list: List of {'Key': 'key', 'Value': 'value'} dicts
            
        Returns:
            Dictionary of tag key-value pairs
        """
        if not tags_list:
            return {}
        
        return {tag.get('Key', ''): tag.get('Value', '') for tag in tags_list if tag.get('Key')}
    
    def get_tag_value(self, tags_list: List[Dict[str, str]], key: str, default: str = '') -> str:
        """
        Get a specific tag value from AWS tags list.
        
        Args:
            tags_list: List of AWS tag dictionaries
            key: Tag key to find
            default: Default value if not found
            
        Returns:
            Tag value or default
        """
        tags_dict = self.process_tags(tags_list)
        return tags_dict.get(key, default)