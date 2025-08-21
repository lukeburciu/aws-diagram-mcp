# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Setup
```bash
# Install dependencies with uv (recommended)
uv sync

# Install in development mode
uv pip install -e .

# Run tests
uv run pytest

# Code formatting and linting
uv run ruff check .
uv run black .
```

### CLI Usage
```bash
# Run CLI tool for AWS diagram generation
uv run python -m aws_diagram_cli [OPTIONS] COMMAND

# Or if installed via pip:
aws-diagram [OPTIONS] COMMAND

# Available commands:
aws-diagram discover    # Discover AWS resources and output JSON
aws-diagram mermaid     # Generate Mermaid diagram
aws-diagram dot         # Generate DOT/Graphviz diagram

# Example: Generate architecture diagram for multiple regions
uv run python -m aws_diagram_cli --regions us-east-1 us-west-2 --sg-preset clean dot --output architecture.png
```

## Architecture Overview

### Core Components

1. **AWS Discovery Module** (`src/aws_diagram_cli/aws_discovery.py`)
   - Handles all AWS API interactions using boto3
   - Supports multi-region resource discovery
   - Discovers VPCs, EC2 instances, load balancers, RDS, security groups, Route53, and ACM certificates

2. **Diagram Generators** (`src/aws_diagram_cli/generators/`)
   - `mermaid.py`: Creates text-based Mermaid diagrams for documentation
   - `diagrams.py`: Creates DOT/Graphviz diagrams with AWS icons

3. **CLI Tool** (`src/aws_diagram_cli/cli.py`)
   - Primary command-line interface for diagram generation
   - Supports security group configuration presets and filters
   - Multi-region support with consolidated output

### Key Design Patterns

- **Multi-Region Support**: All discovery methods accept a list of regions and aggregate results
- **Hierarchical Organization**: Resources organized as Account > Region > VPC > Subnet
- **Security Group Mapping**: Analyzes actual connections based on security group rules
- **Flexible Output**: Supports multiple formats (Mermaid, DOT, PNG, SVG, PDF)

### Configuration System

Security group visualization is highly configurable through CLI options:
- **Connection flows**: `none`, `inter-subnet`, `tier-crossing`, `external-only`
- **Traffic direction**: `both`, `north-south`, `east-west`
- **Label detail**: `minimal`, `ports`, `protocols`, `full`
- **Presets**: `clean`, `network`, `security`, `debug`

## AWS Requirements

### Required IAM Permissions
```json
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
```

### AWS Credential Configuration
- Use AWS CLI profiles: `aws configure --profile myprofile`
- Or set environment variables: `AWS_PROFILE`, `AWS_DEFAULT_REGION`
- Configure in MCP client config or `.mcp.json`

## Testing Strategy

- Unit tests for individual discovery methods
- Integration tests for multi-region functionality (`tests/test_multi_region_cli.py`)
- CLI tests for command-line interface (`tests/test_cli_regions.py`)