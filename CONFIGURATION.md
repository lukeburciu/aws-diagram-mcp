# Configuration Guide

This guide covers all configuration options for the AWS Infrastructure Diagram MCP Server.

## Table of Contents

- [MCP Client Configuration](#mcp-client-configuration)
- [AWS Credentials Setup](#aws-credentials-setup)
- [Environment Variables](#environment-variables)
- [Advanced Configuration](#advanced-configuration)
- [Multiple AWS Accounts](#multiple-aws-accounts)

## MCP Client Configuration

### Claude Desktop Configuration

Add the server to your Claude Desktop configuration file:

**Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Configuration:**
```json
{
  "mcpServers": {
    "aws-diagram": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "aws_diagram_mcp"
      ],
      "cwd": "/absolute/path/to/aws-diagram-mcp",
      "env": {
        "AWS_PROFILE": "default",
        "AWS_DEFAULT_REGION": "us-east-1",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Other MCP Clients

For other MCP clients, use the standard MCP server configuration format:

```json
{
  "name": "aws-diagram",
  "command": ["uv", "run", "python", "-m", "aws_diagram_mcp"],
  "args": [],
  "env": {
    "AWS_PROFILE": "default",
    "AWS_DEFAULT_REGION": "us-east-1"
  }
}
```

## AWS Credentials Setup

### Method 1: AWS CLI Profiles (Recommended)

Create named AWS profiles for different environments:

```bash
# Configure default profile
aws configure

# Configure additional profiles
aws configure --profile production
aws configure --profile staging
aws configure --profile development
```

**Profile files location:**
- Credentials: `~/.aws/credentials`
- Config: `~/.aws/config`

**Example credentials file:**
```ini
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
region = us-east-1

[production]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
region = us-west-2

[staging]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
region = us-east-1
```

### Method 2: Environment Variables

Set AWS credentials as environment variables:

```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1
export AWS_SESSION_TOKEN=...  # For temporary credentials
```

### Method 3: IAM Roles (EC2/ECS/Lambda)

When running on AWS infrastructure, use IAM roles:

```json
{
  "env": {
    "AWS_DEFAULT_REGION": "us-east-1"
  }
}
```

### Method 4: SSO Profiles

For AWS SSO users:

```bash
aws configure sso --profile my-sso-profile
```

Then reference in MCP config:
```json
{
  "env": {
    "AWS_PROFILE": "my-sso-profile"
  }
}
```

## Environment Variables

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_PROFILE` | `default` | AWS CLI profile to use |
| `AWS_DEFAULT_REGION` | `us-east-1` | Default AWS region |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### AWS Credential Variables

| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS access key ID |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key |
| `AWS_SESSION_TOKEN` | AWS session token (for temporary credentials) |
| `AWS_ROLE_ARN` | ARN of role to assume |
| `AWS_ROLE_SESSION_NAME` | Session name for assumed role |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_CONFIG_FILE` | `~/.aws/config` | AWS config file location |
| `AWS_SHARED_CREDENTIALS_FILE` | `~/.aws/credentials` | AWS credentials file location |
| `AWS_CA_BUNDLE` | - | Path to custom CA bundle |
| `AWS_CLI_FILE_ENCODING` | `utf-8` | File encoding for AWS CLI |

## Advanced Configuration

### Custom Output Directories

Configure default output paths using environment variables:

```bash
export AWS_DIAGRAM_OUTPUT_DIR="/path/to/diagrams"
export AWS_DIAGRAM_MERMAID_DIR="/path/to/mermaid"
export AWS_DIAGRAM_DOT_DIR="/path/to/dot"
```

### Proxy Configuration

For corporate environments with proxies:

```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,.company.com
```

### Debug Configuration

Enable detailed logging for troubleshooting:

```json
{
  "env": {
    "LOG_LEVEL": "DEBUG",
    "AWS_CLI_FILE_ENCODING": "utf-8",
    "BOTO_DEBUG": "1"
  }
}
```

## Multiple AWS Accounts

### Option 1: Multiple Server Instances

Configure separate MCP server instances for each account:

```json
{
  "mcpServers": {
    "aws-diagram-prod": {
      "command": "uv",
      "args": ["run", "python", "-m", "aws_diagram_mcp"],
      "cwd": "/path/to/aws-diagram-mcp",
      "env": {
        "AWS_PROFILE": "production",
        "AWS_DEFAULT_REGION": "us-west-2"
      }
    },
    "aws-diagram-staging": {
      "command": "uv",
      "args": ["run", "python", "-m", "aws_diagram_mcp"],
      "cwd": "/path/to/aws-diagram-mcp",
      "env": {
        "AWS_PROFILE": "staging",
        "AWS_DEFAULT_REGION": "us-east-1"
      }
    }
  }
}
```

### Option 2: Profile Switching

Use a single server instance and specify profiles in tool calls:

```python
# Production account
generate_aws_diagram({
    "aws_account": "prod-account",
    "profile": "production",
    "region": "us-west-2"
})

# Staging account  
generate_aws_diagram({
    "aws_account": "staging-account",
    "profile": "staging", 
    "region": "us-east-1"
})
```

## Security Best Practices

### 1. Use Least Privilege IAM Policies

Create a dedicated IAM user/role with minimal permissions:

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

### 2. Use AWS Profiles

Avoid hardcoding credentials. Use AWS profiles instead:

```bash
# Good
aws configure --profile diagram-reader

# Bad
export AWS_ACCESS_KEY_ID=hardcoded_key
```

### 3. Rotate Credentials Regularly

Set up automatic credential rotation:
- Use AWS IAM Access Analyzer
- Set up CloudTrail monitoring
- Regular access key rotation

### 4. Monitor Usage

Track MCP server usage:
- Enable CloudTrail logging
- Monitor API call patterns
- Set up billing alerts

## Troubleshooting Configuration

### Common Configuration Issues

1. **Server not found**
   ```
   Error: Server 'aws-diagram' not found
   ```
   - Check MCP client configuration file location
   - Verify JSON syntax is valid
   - Ensure absolute paths are used

2. **Permission denied**
   ```
   Error: Permission denied when executing uv
   ```
   - Check file permissions on project directory
   - Verify uv is installed and in PATH
   - Try running manually: `uv run python -m aws_diagram_mcp`

3. **AWS credentials not found**
   ```
   Error: Unable to locate credentials
   ```
   - Verify AWS profile exists: `aws configure list`
   - Check environment variables are set correctly
   - Test AWS access: `aws sts get-caller-identity`

4. **Module not found**
   ```
   Error: No module named 'aws_diagram_mcp'
   ```
   - Install dependencies: `uv sync`
   - Check working directory in MCP config
   - Verify project structure

### Validation Commands

Test your configuration:

```bash
# Test AWS credentials
aws sts get-caller-identity --profile your-profile

# Test uv installation
uv --version

# Test Python module
uv run python -c "import aws_diagram_mcp; print('OK')"

# Test MCP server startup
uv run python -m aws_diagram_mcp --help
```

### Configuration Templates

#### Basic Configuration
```json
{
  "mcpServers": {
    "aws-diagram": {
      "command": "uv",
      "args": ["run", "python", "-m", "aws_diagram_mcp"],
      "cwd": "/path/to/aws-diagram-mcp"
    }
  }
}
```

#### Production Configuration
```json
{
  "mcpServers": {
    "aws-diagram": {
      "command": "uv",
      "args": ["run", "python", "-m", "aws_diagram_mcp"],
      "cwd": "/opt/aws-diagram-mcp",
      "env": {
        "AWS_PROFILE": "prod-readonly",
        "AWS_DEFAULT_REGION": "us-west-2",
        "LOG_LEVEL": "WARNING",
        "AWS_DIAGRAM_OUTPUT_DIR": "/var/diagrams"
      }
    }
  }
}
```

#### Development Configuration
```json
{
  "mcpServers": {
    "aws-diagram": {
      "command": "uv",
      "args": ["run", "python", "-m", "aws_diagram_mcp"],
      "cwd": "/home/dev/aws-diagram-mcp",
      "env": {
        "AWS_PROFILE": "dev",
        "AWS_DEFAULT_REGION": "us-east-1",
        "LOG_LEVEL": "DEBUG",
        "HTTP_PROXY": "http://proxy.company.com:8080"
      }
    }
  }
}
```