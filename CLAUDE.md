# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a modular multi-cloud infrastructure diagram generation tool. It supports generating diagrams for AWS (with future support for Azure, GCP, etc.) using a provider-based architecture.

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

### Important: Always use uv for Python commands
Always use `uv run` when executing Python commands in this project.

### CLI Usage
```bash
# Run CLI tool for cloud diagram generation
uv run python -m cloud_diagram [OPTIONS] COMMAND

# Or if installed via pip:
cloud-diagram [OPTIONS] COMMAND

# Available commands:
cloud-diagram discover    # Discover cloud resources and output JSON
cloud-diagram diagram     # Generate infrastructure diagram

# Example: Generate AWS architecture diagram for multiple regions
uv run python -m cloud_diagram --provider aws --regions us-east-1 us-west-2 --sg-preset clean diagram --output architecture.png

# Example: Use custom configuration file
uv run python -m cloud_diagram --provider aws --config my-config.yaml diagram
```

## Architecture Overview

### Modular Provider Architecture

The tool uses a modular provider-based architecture that supports multiple cloud platforms:

```
src/cloud_diagram/
├── __init__.py           # Main package
├── cli.py               # Provider-agnostic CLI
├── config/              # Configuration system
│   ├── loader.py        # YAML config loader
│   └── schema.py        # Config validation
└── providers/           # Cloud provider modules
    ├── __init__.py      # Provider registry
    └── aws/             # AWS provider implementation
        ├── discovery.py # AWS resource discovery
        ├── diagram.py   # AWS diagram generation
        └── config.yaml  # AWS default configuration
```

### Core Components

1. **Provider Registry** (`src/cloud_diagram/providers/__init__.py`)
   - Dynamic loading of cloud provider modules
   - Standardized interface for different cloud platforms
   - Currently supports: AWS (future: Azure, GCP)

2. **Configuration System** (`src/cloud_diagram/config/`)
   - YAML-based configuration with validation
   - Hierarchical config loading (defaults → user config → CLI overrides)
   - Provider-specific configuration templates

3. **AWS Provider** (`src/cloud_diagram/providers/aws/`)
   - AWS API interactions using boto3
   - Multi-region resource discovery
   - DOT/Graphviz diagram generation with AWS icons

4. **CLI Tool** (`src/cloud_diagram/cli.py`)
   - Provider-agnostic command-line interface
   - Configuration file support
   - Security group configuration presets and filters

### Key Design Patterns

- **Provider Isolation**: Each cloud provider is completely independent
- **Configuration-Driven**: Behavior controlled through YAML configuration files
- **Multi-Region Support**: All discovery methods accept a list of regions and aggregate results
- **Hierarchical Organization**: Resources organized as Account > Region > VPC > Subnet
- **Security Group Mapping**: Analyzes actual connections based on security group rules
- **Flexible Output**: Supports multiple formats (DOT, PNG, SVG, PDF)
- **Enterprise Features**: Naming conventions, resource filters, visual customization

### Configuration System

The tool supports comprehensive configuration through YAML files:

#### YAML Configuration Structure
```yaml
diagram:
  output_format: png
  layout: hierarchical

naming_conventions:
  vpc_format: "{name} ({cidr})"
  instance_format: "{name}\n{type}\n{ip}"

resource_filters:
  exclude_tags:
    - Environment: test
  include_only_regions:
    - us-east-1
    - us-west-2

hierarchy_rules:
  group_by: [region, vpc, subnet_tier]
  subnet_tiers:
    public: ["*public*", "*dmz*"]
    private: ["*private*", "*app*"]
    restricted: ["*db*", "*data*"]

visual_rules:
  icon_size: medium
  show_connections: true
  connection_labels: ports
  color_scheme: aws_official
```

#### CLI Configuration Options
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