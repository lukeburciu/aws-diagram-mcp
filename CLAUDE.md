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

# Example: Generate AWS architecture diagram
uv run python -m cloud_diagram --provider aws --region us-east-1 diagram --output architecture --format png

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
        ├── discovery_v2.py # AWS resource discovery
        ├── diagram.py   # AWS diagram generation
        ├── config.yaml  # AWS default configuration
        └── snippets/    # Resource-specific rendering snippets
            ├── registry.py     # Snippet management
            ├── base.py         # Base snippet class
            ├── ec2/            # EC2 resource snippets
            ├── rds/            # RDS resource snippets
            ├── elb/            # Load balancer snippets
            ├── route53/        # Route53 snippets
            └── acm/            # Certificate Manager snippets
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

4. **Snippet System** (`src/cloud_diagram/providers/aws/snippets/`)
   - Modular resource-specific rendering logic
   - Registry-based snippet management
   - Extensible architecture for new AWS services

5. **CLI Tool** (`src/cloud_diagram/cli.py`)
   - Provider-agnostic command-line interface
   - Configuration file support
   - Security group configuration presets and filters

### Key Design Patterns

- **Provider Isolation**: Each cloud provider is completely independent
- **Configuration-Driven**: Behavior controlled through YAML configuration files
- **Single-Region Support**: Discovery operates in a single AWS region
- **Hierarchical Organization**: Resources organized as Region > VPC > Subnet
- **Security Group Mapping**: Analyzes actual connections based on security group rules
- **Flexible Output**: Supports multiple formats (DOT, PNG, SVG, PDF)
- **Enterprise Features**: Naming conventions, resource filters, visual customization
- **Snippet-Based Rendering**: Modular approach to resource visualization with service-specific logic

### Configuration System

The tool supports comprehensive configuration through YAML files:

#### YAML Configuration Structure
```yaml
diagram:
  output_format: png
  layout: hierarchical

naming_conventions:
  vpc_format: "{name} ({cidr})"
  instance_format: "{name}\\n{type}\\n{ip}"

resource_filters:
  exclude_tags:
    - Environment: test
  max_resources_per_type: 100

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
- **Region Selection**: Uses `--region` flag or `$AWS_DEFAULT_REGION` environment variable (defaults to us-east-1)
- **Diagram Presets**: `clean`, `network`, `security`
- **Output Formats**: `png`, `svg`, `pdf`, `dot`
- **Service Filtering**: Specify specific services with `--services ec2,rds`

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
- when running python scripts, files, handling any python based actions - use uv always