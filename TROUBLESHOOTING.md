# Troubleshooting Guide

This guide helps resolve common issues when using the AWS Infrastructure Diagram MCP Server.

## Table of Contents

- [Installation Issues](#installation-issues)
- [AWS Authentication Problems](#aws-authentication-problems)
- [MCP Server Issues](#mcp-server-issues)
- [Diagram Generation Errors](#diagram-generation-errors)
- [Performance Issues](#performance-issues)
- [Output Problems](#output-problems)
- [Debug Tools](#debug-tools)

## Installation Issues

### 1. Python Version Compatibility

**Problem:**
```
ERROR: This package requires Python >=3.10
```

**Solution:**
```bash
# Check Python version
python --version
python3 --version

# Install Python 3.10+ using pyenv (recommended)
curl https://pyenv.run | bash
pyenv install 3.11.7
pyenv global 3.11.7

# Or use system package manager
# macOS:
brew install python@3.11

# Ubuntu:
sudo apt update
sudo apt install python3.11 python3.11-venv
```

### 2. uv Installation Issues

**Problem:**
```
Command 'uv' not found
```

**Solution:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv

# Or using brew (macOS)
brew install uv

# Verify installation
uv --version
```

### 3. Graphviz System Dependency

**Problem:**
```
ExecutableNotFound: failed to execute ['dot', '-Tpng'], make sure the Graphviz executables are on your system PATH
```

**Solution:**
```bash
# macOS
brew install graphviz

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install graphviz graphviz-dev

# CentOS/RHEL
sudo yum install graphviz graphviz-devel

# Windows (using Chocolatey)
choco install graphviz

# Windows (using Scoop)
scoop install graphviz

# Verify installation
dot -V
```

### 4. Permission Issues

**Problem:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Fix directory permissions
chmod -R 755 /path/to/aws-diagram-mcp

# Install in user directory instead of system-wide
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Check file ownership
ls -la /path/to/aws-diagram-mcp
```

### 5. Dependency Conflicts

**Problem:**
```
ERROR: Cannot install aws-diagram-mcp because these package versions have conflicting dependencies
```

**Solution:**
```bash
# Create clean virtual environment
uv venv --python 3.11
source .venv/bin/activate

# Install with specific versions
uv pip install boto3==1.35.0 pydantic==2.5.0 fastmcp==0.1.0

# Or reset and reinstall
rm -rf .venv
uv venv
uv sync --no-cache
```

## AWS Authentication Problems

### 1. Credentials Not Found

**Problem:**
```
NoCredentialsError: Unable to locate credentials
```

**Diagnosis:**
```bash
# Check AWS CLI installation
aws --version

# Check credentials configuration
aws configure list

# Test basic AWS access
aws sts get-caller-identity
```

**Solutions:**
```bash
# Option 1: Configure AWS CLI
aws configure
# Enter: Access Key ID, Secret Access Key, Region, Output format

# Option 2: Use environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Option 3: Use AWS profiles
aws configure --profile myprofile
export AWS_PROFILE=myprofile

# Option 4: Use IAM roles (on EC2)
# Attach IAM role to EC2 instance, no credentials needed
```

### 2. Invalid Credentials

**Problem:**
```
ClientError: The security token included in the request is invalid
```

**Diagnosis:**
```bash
# Test credentials
aws sts get-caller-identity --profile your-profile

# Check credential expiration
aws sts get-session-token --profile your-profile
```

**Solutions:**
```bash
# Refresh credentials
aws configure --profile your-profile

# For SSO users
aws sso login --profile your-profile

# For assumed roles, re-assume the role
aws sts assume-role --role-arn arn:aws:iam::123456789012:role/YourRole --role-session-name YourSession
```

### 3. Insufficient Permissions

**Problem:**
```
ClientError: User is not authorized to perform: ec2:DescribeInstances
```

**Solution:**
Ensure your AWS user/role has these minimum permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:Describe*",
                "elasticloadbalancing:Describe*",
                "rds:Describe*",
                "route53:List*",
                "route53:Get*",
                "acm:List*",
                "acm:Describe*",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

**Verify permissions:**
```bash
# Test specific permissions
aws ec2 describe-vpcs --region us-east-1
aws ec2 describe-instances --region us-east-1
aws elbv2 describe-load-balancers --region us-east-1
aws rds describe-db-instances --region us-east-1
```

### 4. Region Issues

**Problem:**
```
ClientError: The specified region does not exist
```

**Solution:**
```bash
# List available regions
aws ec2 describe-regions --query "Regions[].RegionName" --output table

# Set correct region
export AWS_DEFAULT_REGION=us-east-1

# Or specify in tool call
generate_aws_diagram({"aws_account": "test", "region": "us-east-1"})
```

## MCP Server Issues

### 1. Server Not Starting

**Problem:**
```
Error: MCP server failed to start
```

**Diagnosis:**
```bash
# Test server manually
cd /path/to/aws-diagram-mcp
uv run python -m aws_diagram_mcp

# Check for import errors
uv run python -c "import aws_diagram_mcp; print('OK')"
```

**Solutions:**
```bash
# Install missing dependencies
uv sync

# Check Python path
uv run python -c "import sys; print('\n'.join(sys.path))"

# Run with debug logging
LOG_LEVEL=DEBUG uv run python -m aws_diagram_mcp
```

### 2. MCP Client Configuration

**Problem:**
```
Error: Server 'aws-diagram' not found in configuration
```

**Solution:**
```json
// Check MCP client config file location
// macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
// Windows: %APPDATA%\Claude\claude_desktop_config.json  
// Linux: ~/.config/Claude/claude_desktop_config.json

{
  "mcpServers": {
    "aws-diagram": {
      "command": "uv",
      "args": ["run", "python", "-m", "aws_diagram_mcp"],
      "cwd": "/absolute/path/to/aws-diagram-mcp",
      "env": {
        "AWS_PROFILE": "default",
        "AWS_DEFAULT_REGION": "us-east-1"
      }
    }
  }
}
```

**Validation:**
```bash
# Validate JSON syntax
python -m json.tool < claude_desktop_config.json

# Check file permissions
ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### 3. Working Directory Issues

**Problem:**
```
FileNotFoundError: [Errno 2] No such file or directory
```

**Solution:**
```bash
# Use absolute paths in MCP config
"cwd": "/home/user/aws-diagram-mcp"  # Good
"cwd": "~/aws-diagram-mcp"           # Bad (tilde not expanded)
"cwd": "./aws-diagram-mcp"           # Bad (relative path)

# Verify directory exists
ls -la /absolute/path/to/aws-diagram-mcp
```

### 4. Environment Variables

**Problem:**
```
Error: Environment variable not set
```

**Solution:**
```json
// Add all required environment variables to MCP config
{
  "mcpServers": {
    "aws-diagram": {
      "command": "uv",
      "args": ["run", "python", "-m", "aws_diagram_mcp"],
      "cwd": "/path/to/aws-diagram-mcp",
      "env": {
        "AWS_PROFILE": "your-profile",
        "AWS_DEFAULT_REGION": "us-east-1",
        "LOG_LEVEL": "INFO",
        "PATH": "/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

## Diagram Generation Errors

### 1. No Resources Found

**Problem:**
```
Error: No VPCs found
```

**Diagnosis:**
```bash
# Check if resources exist in the region
aws ec2 describe-vpcs --region us-east-1
aws ec2 describe-instances --region us-east-1

# Check if using correct profile/account
aws sts get-caller-identity --profile your-profile
```

**Solutions:**
```python
# Try different region
generate_aws_diagram({
    "aws_account": "test",
    "region": "us-west-2"  # Different region
})

# Use resource discovery first
resources = discover_aws_resources({
    "region": "us-east-1",
    "resource_types": ["vpcs"]
})
print("Found VPCs:", resources['resources']['vpcs'])
```

### 2. Memory Issues with Large Accounts

**Problem:**
```
MemoryError: Unable to allocate memory
```

**Solutions:**
```python
# Generate diagrams for specific VPCs
resources = discover_aws_resources({"resource_types": ["vpcs"]})
for vpc in resources['resources']['vpcs']:
    generate_aws_diagram({
        "aws_account": f"vpc-{vpc['vpc_id']}",
        "vpc_id": vpc['vpc_id']
    })

# Disable optional components
generate_aws_diagram({
    "aws_account": "large-account",
    "include_route53": False,
    "include_acm": False
})
```

### 3. Timeout Issues

**Problem:**
```
TimeoutError: Operation timed out
```

**Solutions:**
```python
# Use resource-specific discovery
resources = discover_aws_resources({
    "resource_types": ["instances", "load_balancers"]  # Skip slow operations
})

# Process regions separately
for region in ["us-east-1", "us-west-2"]:
    generate_aws_diagram({
        "aws_account": f"region-{region}",
        "region": region
    })
```

### 4. Mermaid Syntax Errors

**Problem:**
```
Error: Invalid Mermaid syntax
```

**Diagnosis:**
```python
# Validate generated diagram
diagram = generate_aws_diagram({"aws_account": "test"})["diagram"]
validation = validate_mermaid_syntax(diagram)

if not validation["valid"]:
    print("Syntax error:", validation["error"])
```

**Solutions:**
```python
# Check for special characters in resource names
resources = discover_aws_resources({})
for instance in resources['resources']['instances']:
    name = instance.get('name', '')
    if any(char in name for char in ['[', ']', '(', ')', '"', "'"]):
        print(f"Warning: Special characters in instance name: {name}")
```

### 5. DOT/Graphviz Rendering Issues

**Problem:**
```
Error: dot terminated with exit code 1
```

**Diagnosis:**
```bash
# Test Graphviz directly
echo 'digraph { A -> B }' | dot -Tpng -o test.png

# Check dot version
dot -V
```

**Solutions:**
```bash
# Reinstall Graphviz
brew reinstall graphviz  # macOS
sudo apt-get reinstall graphviz  # Ubuntu

# Check PATH
echo $PATH | grep -o '[^:]*graphviz[^:]*'

# Use different output format
generate_aws_diagram_dot({
    "aws_account": "test",
    "output_format": "svg"  # Try SVG instead of PNG
})
```

## Performance Issues

### 1. Slow Resource Discovery

**Problem:**
Discovery takes more than 5 minutes

**Solutions:**
```python
# Use incremental discovery
def fast_discovery(region):
    # Start with core resources
    core = discover_aws_resources({
        "region": region,
        "resource_types": ["vpcs", "instances"]
    })
    
    # Only get security groups if we have instances
    if core['resources']['instances']:
        sg_ids = []
        for instance in core['resources']['instances']:
            sg_ids.extend(instance.get('security_groups', []))
        
        # Discover security groups separately
        sgs = discover_aws_resources({
            "region": region,
            "resource_types": ["security_groups"]
        })
        
        core['resources']['security_groups'] = sgs['resources']['security_groups']
    
    return core
```

### 2. Large Diagram Generation

**Problem:**
Diagram generation is very slow or fails

**Solutions:**
```python
# Split by VPC
def generate_vpc_diagrams(account_name, region):
    vpcs = discover_aws_resources({
        "region": region,
        "resource_types": ["vpcs"]
    })
    
    for vpc in vpcs['resources']['vpcs']:
        vpc_name = vpc['tags'].get('Name', vpc['vpc_id'])
        generate_aws_diagram({
            "aws_account": f"{account_name}-{vpc_name}",
            "vpc_id": vpc['vpc_id'],
            "region": region
        })

# Use caching
import functools
import pickle
from pathlib import Path

@functools.lru_cache(maxsize=10)
def cached_discover_resources(region, resource_types_tuple):
    return discover_aws_resources({
        "region": region,
        "resource_types": list(resource_types_tuple)
    })
```

### 3. Memory Usage

**Problem:**
High memory usage during generation

**Solutions:**
```python
# Process resources in batches
def batch_diagram_generation(account_name, batch_size=50):
    all_instances = discover_aws_resources({
        "resource_types": ["instances"]
    })['resources']['instances']
    
    for i in range(0, len(all_instances), batch_size):
        batch = all_instances[i:i+batch_size]
        # Process batch...
        
# Clear variables after use
result = generate_aws_diagram({"aws_account": "test"})
del result  # Free memory
import gc; gc.collect()  # Force garbage collection
```

## Output Problems

### 1. File Permission Errors

**Problem:**
```
PermissionError: [Errno 13] Permission denied: '/path/to/output.md'
```

**Solutions:**
```bash
# Check directory permissions
ls -la docs/as-built/
chmod 755 docs/as-built/

# Create directory if it doesn't exist
mkdir -p docs/as-built/my-account

# Use different output location
generate_aws_diagram({
    "aws_account": "test",
    "output_path": "/tmp/aws-diagram.md"
})
```

### 2. File Already Exists

**Problem:**
```
FileExistsError: Output file already exists
```

**Solutions:**
```python
import os
from datetime import datetime

# Add timestamp to filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = f"docs/infrastructure_{timestamp}.md"

# Or remove existing file
output_path = "docs/infrastructure.md"
if os.path.exists(output_path):
    os.remove(output_path)

generate_aws_diagram({
    "aws_account": "test",
    "output_path": output_path
})
```

### 3. Invalid Output Path

**Problem:**
```
OSError: Invalid file path
```

**Solutions:**
```python
from pathlib import Path

def safe_output_path(base_path, account_name):
    # Sanitize account name
    safe_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in account_name)
    
    # Create directory structure
    output_dir = Path(base_path) / safe_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return output_dir / f"{safe_name}_infrastructure.md"

# Usage
safe_path = safe_output_path("docs", "my-account")
generate_aws_diagram({
    "aws_account": "my-account",
    "output_path": str(safe_path)
})
```

## Debug Tools

### 1. Enable Debug Logging

```python
import logging

# Enable debug logging for the MCP server
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Or set environment variable
import os
os.environ['LOG_LEVEL'] = 'DEBUG'
```

### 2. AWS SDK Debug Mode

```bash
# Enable boto3 debug logging
export BOTO_DEBUG=1

# Enable HTTP debugging
export AWS_CLI_FILE_ENCODING=utf-8
```

### 3. Manual Testing

```python
def debug_aws_access():
    """Debug AWS access step by step"""
    
    print("=== AWS Access Debug ===")
    
    # 1. Test STS access
    try:
        from aws_diagram_mcp.aws_discovery import AWSResourceDiscovery
        discovery = AWSResourceDiscovery()
        account_info = discovery.get_account_info()
        print(f"✓ Account: {account_info.get('account_id', 'Unknown')}")
    except Exception as e:
        print(f"✗ STS Error: {e}")
        return False
    
    # 2. Test VPC access
    try:
        vpcs = discovery.discover_vpcs()
        print(f"✓ VPCs: Found {len(vpcs)}")
    except Exception as e:
        print(f"✗ VPC Error: {e}")
        return False
    
    # 3. Test EC2 access
    try:
        instances = discovery.discover_ec2_instances()
        print(f"✓ EC2: Found {len(instances)} instances")
    except Exception as e:
        print(f"✗ EC2 Error: {e}")
        return False
    
    print("✓ All AWS access tests passed")
    return True

# Run debug
if __name__ == "__main__":
    debug_aws_access()
```

### 4. Configuration Validation

```python
def validate_configuration():
    """Validate MCP server configuration"""
    
    import json
    from pathlib import Path
    
    # Check MCP config file
    config_paths = [
        Path.home() / "Library/Application Support/Claude/claude_desktop_config.json",  # macOS
        Path.home() / ".config/Claude/claude_desktop_config.json",  # Linux
        Path(os.getenv('APPDATA', '')) / "Claude/claude_desktop_config.json"  # Windows
    ]
    
    config_file = None
    for path in config_paths:
        if path.exists():
            config_file = path
            break
    
    if not config_file:
        print("✗ MCP config file not found")
        return False
    
    try:
        with open(config_file) as f:
            config = json.load(f)
        
        if "aws-diagram" in config.get("mcpServers", {}):
            print("✓ MCP server configured")
            server_config = config["mcpServers"]["aws-diagram"]
            
            # Check working directory
            cwd = server_config.get("cwd")
            if cwd and Path(cwd).exists():
                print(f"✓ Working directory exists: {cwd}")
            else:
                print(f"✗ Working directory not found: {cwd}")
                
            return True
        else:
            print("✗ aws-diagram server not in MCP config")
            return False
            
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in MCP config: {e}")
        return False

# Run validation
validate_configuration()
```

### 5. Performance Profiling

```python
import time
import cProfile
import pstats

def profile_diagram_generation():
    """Profile diagram generation performance"""
    
    profiler = cProfile.Profile()
    
    profiler.enable()
    
    # Your diagram generation code
    result = generate_aws_diagram({
        "aws_account": "performance-test"
    })
    
    profiler.disable()
    
    # Print top time-consuming functions
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions
    
    return result
```

## Getting Help

### 1. Collect Debug Information

Before seeking help, collect this information:

```bash
# System information
uv --version
python --version
aws --version
dot -V

# AWS configuration
aws configure list
aws sts get-caller-identity

# Project status
cd /path/to/aws-diagram-mcp
uv run python -c "import aws_diagram_mcp; print('Import OK')"
ls -la src/aws_diagram_mcp/

# MCP configuration
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | jq .mcpServers.\"aws-diagram\"
```

### 2. Create Minimal Reproduction

```python
# Minimal test case
def minimal_reproduction():
    try:
        result = discover_aws_resources({
            "region": "us-east-1",
            "resource_types": ["vpcs"]
        })
        
        if result["success"]:
            print("✓ Resource discovery works")
            
            diagram_result = generate_aws_diagram({
                "aws_account": "test-minimal",
                "region": "us-east-1"
            })
            
            if diagram_result["success"]:
                print("✓ Diagram generation works")
            else:
                print(f"✗ Diagram failed: {diagram_result['error']}")
        else:
            print(f"✗ Discovery failed: {result['error']}")
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")
        import traceback
        traceback.print_exc()

minimal_reproduction()
```

### 3. Log Collection

```bash
# Enable comprehensive logging
export LOG_LEVEL=DEBUG
export BOTO_DEBUG=1

# Run with logging
uv run python -m aws_diagram_mcp 2>&1 | tee debug.log

# Collect logs
grep -i error debug.log
grep -i warning debug.log
```

This troubleshooting guide should help resolve most common issues. If you're still experiencing problems, please provide the debug information collected above when seeking help.