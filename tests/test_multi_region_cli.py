#!/usr/bin/env python3
"""Test multi-region functionality in CLI."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
from src.aws_diagram_mcp.aws_discovery import AWSResourceDiscovery

def test_multi_region_discovery():
    """Test that discovery works with multiple regions."""
    
    # Mock boto3 clients
    with patch('boto3.Session') as mock_session:
        # Create mock clients
        mock_ec2_us_east = MagicMock()
        mock_ec2_us_west = MagicMock()
        mock_elbv2_us_east = MagicMock()
        mock_elbv2_us_west = MagicMock()
        
        # Set up mock returns for VPCs
        mock_ec2_us_east.describe_vpcs.return_value = {
            'Vpcs': [{
                'VpcId': 'vpc-east-1',
                'CidrBlock': '10.0.0.0/16',
                'State': 'available',
                'IsDefault': False,
                'Tags': [{'Key': 'Name', 'Value': 'US-East VPC'}]
            }]
        }
        
        mock_ec2_us_west.describe_vpcs.return_value = {
            'Vpcs': [{
                'VpcId': 'vpc-west-1',
                'CidrBlock': '10.1.0.0/16', 
                'State': 'available',
                'IsDefault': False,
                'Tags': [{'Key': 'Name', 'Value': 'US-West VPC'}]
            }]
        }
        
        # Set up mock returns for EC2 instances
        mock_ec2_us_east.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-east-1',
                    'InstanceType': 't2.micro',
                    'State': {'Name': 'running'},
                    'PrivateIpAddress': '10.0.1.10',
                    'VpcId': 'vpc-east-1',
                    'SubnetId': 'subnet-east-1',
                    'SecurityGroups': [{'GroupId': 'sg-east-1'}],
                    'Tags': [{'Key': 'Name', 'Value': 'East Instance'}]
                }]
            }]
        }
        
        mock_ec2_us_west.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-west-1',
                    'InstanceType': 't3.small',
                    'State': {'Name': 'running'},
                    'PrivateIpAddress': '10.1.1.10',
                    'VpcId': 'vpc-west-1',
                    'SubnetId': 'subnet-west-1',
                    'SecurityGroups': [{'GroupId': 'sg-west-1'}],
                    'Tags': [{'Key': 'Name', 'Value': 'West Instance'}]
                }]
            }]
        }
        
        # Configure mock session
        def get_client(service, region_name=None):
            if service == 'ec2':
                if region_name == 'us-east-1':
                    return mock_ec2_us_east
                elif region_name == 'us-west-2':
                    return mock_ec2_us_west
            elif service == 'elbv2':
                if region_name == 'us-east-1':
                    return mock_elbv2_us_east
                elif region_name == 'us-west-2':
                    return mock_elbv2_us_west
            elif service in ['route53', 'sts']:
                return MagicMock()
            return MagicMock()
        
        mock_session.return_value.client = get_client
        
        # Test discovery with multiple regions
        discovery = AWSResourceDiscovery(regions=['us-east-1', 'us-west-2'])
        
        # Discover VPCs
        vpcs = discovery.discover_vpcs()
        print(f"Found {len(vpcs)} VPCs across regions:")
        for vpc in vpcs:
            print(f"  - {vpc['vpc_id']} in {vpc['region']}: {vpc['tags'].get('Name', 'Unnamed')}")
        
        # Discover EC2 instances
        instances = discovery.discover_ec2_instances()
        print(f"\nFound {len(instances)} EC2 instances across regions:")
        for instance in instances:
            print(f"  - {instance['instance_id']} in {instance['region']}: {instance.get('name', 'Unnamed')}")
        
        # Verify results
        assert len(vpcs) == 2, f"Expected 2 VPCs, got {len(vpcs)}"
        assert len(instances) == 2, f"Expected 2 instances, got {len(instances)}"
        
        # Check regions are properly set
        regions_in_vpcs = {vpc['region'] for vpc in vpcs}
        assert regions_in_vpcs == {'us-east-1', 'us-west-2'}, f"VPC regions: {regions_in_vpcs}"
        
        regions_in_instances = {inst['region'] for inst in instances}
        assert regions_in_instances == {'us-east-1', 'us-west-2'}, f"Instance regions: {regions_in_instances}"
        
        print("\n✅ Multi-region discovery test passed!")

if __name__ == "__main__":
    test_multi_region_discovery()