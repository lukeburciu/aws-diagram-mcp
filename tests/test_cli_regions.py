#!/usr/bin/env python3
"""Test CLI region argument parsing."""

import sys
import argparse
import os

# Simulate the CLI argument parsing
def test_regions():
    default_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    
    parser = argparse.ArgumentParser(description="AWS Infrastructure Diagram Generator")
    parser.add_argument("--regions", nargs="+", default=[default_region], 
                       help=f"AWS regions to scan (default: {default_region}). Can specify multiple: --regions us-east-1 us-west-2")
    parser.add_argument("--region", dest="regions", action="append", 
                       help="Single region (deprecated, use --regions instead)")
    
    # Test cases
    test_cases = [
        ["--regions", "us-east-1", "us-west-2"],
        ["--regions", "eu-west-1"],
        ["--region", "ap-southeast-1"],
        [],  # Default case
    ]
    
    for i, test_args in enumerate(test_cases):
        print(f"\nTest case {i+1}: {test_args or 'default'}")
        args = parser.parse_args(test_args)
        
        # Handle legacy --region argument
        if hasattr(args, 'region') and args.region and args.regions == [default_region]:
            args.regions = [args.region]
        
        print(f"  Parsed regions: {args.regions}")

if __name__ == "__main__":
    test_regions()