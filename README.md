# AWS Infrastructure Diagram CLI

A command-line tool that generates comprehensive AWS infrastructure diagrams in both Mermaid and DOT/Graphviz formats. This tool automatically discovers AWS resources and creates hierarchical diagrams showing VPCs, subnets, EC2 instances, load balancers, RDS instances, and their security group connections.

## Features

- **Comprehensive Resource Discovery**: Automatically discovers VPCs, subnets, EC2 instances, load balancers, RDS instances, security groups, Route53 zones, and ACM certificates
- **Multi-Region Support**: Discover and visualize resources across multiple AWS regions in a single diagram
- **Hierarchical Organization**: Organizes resources by Account > Region > VPC > Subnet tiers
- **Security Group Analysis**: Maps actual connections between resources based on security group rules
- **Load Balancer Mapping**: Shows real target group connections, not assumptions
- **Dual Output Formats**: 
  - **Mermaid**: Text-based diagrams for documentation and web display
  - **DOT/Graphviz**: Professional diagrams with AWS icons (PNG, SVG, PDF output)
- **Flexible Configuration**: Supports AWS profiles, regions, and selective resource discovery

## Installation

### Using uv (Recommended)

```bash
# Clone or create the project
cd aws-diagram-cli

# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

### Using pip

```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### System Requirements

For DOT/Graphviz diagram generation, you'll need Graphviz installed on your system:

**macOS:**
```bash
brew install graphviz
```

**Ubuntu/Debian:**
```bash
sudo apt-get install graphviz
```

**Windows:**
Download from https://graphviz.org/download/ or use Chocolatey:
```bash
choco install graphviz
```

## Quick Start

### 1. Configure AWS Credentials

Choose one method:

**Option A: AWS CLI (Recommended)**
```bash
aws configure --profile myprofile
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### 2. Test the Setup

```bash
# Test AWS access
aws sts get-caller-identity --profile your-profile

# Test CLI tool
uv run python -m aws_diagram_cli --help
```

## Configuration

### Security Group Behavior Options

The CLI provides extensive customization options for how security group connections are displayed in diagrams:

#### Connection Flow Types (`--sg-flows`)
Control which types of connections are shown:
- `none`: Hide all security group connections (clean architecture view)
- `inter-subnet`: Show connections between different subnets only (default)
- `tier-crossing`: Show connections between different network tiers only
- `external-only`: Show only connections involving external/load-balanced traffic

#### Traffic Direction Filtering (`--sg-direction`)
Filter connections by traffic pattern:
- `both`: Show all traffic directions (default)
- `north-south`: Show only up/down stack traffic (web→app→db)
- `east-west`: Show only lateral traffic between same-tier resources

#### Label Detail Levels (`--sg-detail`)
Control connection label verbosity:
- `minimal`: Simple arrows with no labels
- `ports`: Show port numbers only (default)
- `protocols`: Show service names and protocols (http/tcp, mysql/tcp)
- `full`: Show complete port/protocol with security group context

#### Advanced Filters
- `--sg-filter-internal`: Hide same-subnet internal connections
- `--sg-filter-ephemeral`: Hide high ephemeral ports (>32768)
- `--sg-only-ingress`: Show only ingress rules (ignore egress)

#### Presets
Quick configuration presets for common use cases:
- `--sg-preset clean`: No security group lines (architecture focus)
- `--sg-preset network`: Cross-tier flows only (network design)
- `--sg-preset security`: Full security audit view
- `--sg-preset debug`: External traffic troubleshooting

#### Examples

```bash
# Clean architecture diagram with no security group clutter
./cli.py --sg-preset clean dot

# Show only important cross-tier traffic flows
./cli.py --sg-flows tier-crossing --sg-direction north-south --sg-detail protocols dot

# Security audit view with all connection details
./cli.py --sg-preset security --sg-detail full dot

# Troubleshoot external connectivity issues
./cli.py --sg-flows external-only --sg-filter-ephemeral --sg-detail full dot

# Network design review focusing on tier interactions
./cli.py --sg-preset network dot --output network-design.png
```

### Future Configuration Options

The configuration system is designed to support additional customization options for other AWS resources:

- **Instance Grouping**: Cluster instances by tags, auto-scaling groups, or custom criteria
- **Load Balancer Detail**: Control target group visibility and health status display
- **RDS Clustering**: Group database instances by clusters or parameter groups
- **Resource Filtering**: Include/exclude resources by tags, names, or patterns
- **Visual Styling**: Custom colors, shapes, and layouts for different resource types
- **Output Formats**: Additional export formats and rendering options

### Configuration Files

Future versions will support configuration files for persistent settings:

```yaml
# .aws-diagram-config.yaml
security_groups:
  default_flows: "tier-crossing"
  default_detail: "protocols"
  filter_ephemeral: true
  
instances:
  group_by: ["environment", "tier"]
  show_private_ips: true
  
load_balancers:
  show_target_health: true
  group_targets: false

output:
  default_format: "svg"
  include_metadata: true
```

For detailed configuration instructions, see:
- **[CONFIGURATION.md](CONFIGURATION.md)** - Complete setup guide
- **[USAGE.md](USAGE.md)** - Usage examples and workflows  
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

## Usage

### Standalone CLI

The project includes a standalone CLI tool for generating diagrams without MCP:

```bash
# Generate diagrams using the CLI
./cli.py [OPTIONS] COMMAND

# Available commands:
./cli.py discover    # Discover AWS resources and output JSON
./cli.py mermaid     # Generate Mermaid diagram
./cli.py dot         # Generate DOT/Graphviz diagram

# Global options:
--regions REGIONS         # AWS regions to scan (can specify multiple)
--profile PROFILE         # AWS profile to use
--vpc-id VPC_ID          # Specific VPC to diagram
--output PATH            # Output file path
--include-route53        # Include Route53 zones (default: true)
--include-acm            # Include ACM certificates (default: true)

# Security group options (see Configuration section above)
--sg-flows {none,inter-subnet,tier-crossing,external-only}
--sg-direction {both,north-south,east-west}
--sg-detail {minimal,ports,protocols,full}
--sg-filter-internal
--sg-filter-ephemeral
--sg-only-ingress
--sg-preset {clean,network,security,debug}
```

#### CLI Examples

```bash
# Discover all resources in a single region and save to JSON
uv run python -m aws_diagram_cli --regions us-west-2 --output resources.json discover

# Discover resources across multiple regions
uv run python -m aws_diagram_cli --regions us-east-1 us-west-2 eu-west-1 discover

# Generate clean architecture diagram for multiple regions
uv run python -m aws_diagram_cli --regions us-east-1 us-west-2 --sg-preset clean dot --output architecture.png

# Generate Mermaid diagram for specific VPC across regions
uv run python -m aws_diagram_cli --regions us-east-1 us-west-2 --vpc-id vpc-12345678 --output vpc-diagram.md mermaid

# Generate detailed security audit diagram
uv run python -m aws_diagram_cli --sg-preset security --sg-detail full dot --format svg

# Generate network design diagram focusing on cross-tier traffic
uv run python -m aws_diagram_cli --sg-flows tier-crossing --sg-direction north-south dot --output network-design
```

## CLI Commands

### discover

Discover AWS resources across multiple regions and output as JSON.

```bash
# Discover all resources in multiple regions
uv run python -m aws_diagram_cli --regions us-east-1 us-west-2 discover

# Save discovery results to file
uv run python -m aws_diagram_cli --regions us-east-1 --output resources.json discover

# Discover resources for specific VPC
uv run python -m aws_diagram_cli --vpc-id vpc-12345678 discover
```

### mermaid

Generate Mermaid text-based diagrams for documentation.

```bash
# Generate Mermaid diagram for multiple regions
uv run python -m aws_diagram_cli --regions us-east-1 us-west-2 mermaid

# Save Mermaid diagram to file
uv run python -m aws_diagram_cli --output diagram.md mermaid

# Generate diagram with specific security group settings
uv run python -m aws_diagram_cli --sg-preset clean mermaid
```

### dot

Generate DOT/Graphviz diagrams with AWS icons in multiple formats.

```bash
# Generate PNG diagram (default)
uv run python -m aws_diagram_cli --regions us-east-1 us-west-2 dot

# Generate SVG diagram
uv run python -m aws_diagram_cli dot --format svg

# Generate PDF with custom output path
uv run python -m aws_diagram_cli --output architecture dot --format pdf

# Generate detailed security audit diagram
uv run python -m aws_diagram_cli --sg-preset security --sg-detail full dot
```

## Diagram Structure

### Hierarchical Organization

The generated diagrams follow this structure:

```
Account
├── Region (us-east-1, us-west-2, etc.)
    ├── VPC
        ├── Presentation Subnet (Public)
        │   ├── Application Load Balancers
        │   └── Network Load Balancers
        ├── Application Subnet (Private)
        │   ├── EC2 Instances
        │   └── Auto Scaling Groups
        └── Restricted Subnet (Database)
            └── RDS Instances
```

### Visual Elements

- **Route53**: Stadium shape `([Route53])`
- **Load Balancers**: Trapezoid `/[ALB]\`
- **EC2 Instances**: Rectangle `[EC2]`
- **RDS Instances**: Cylinder `[(RDS)]`

### Connection Types

- **Route53 → Load Balancers**: `-->`  (53/tcp)
- **Load Balancers → EC2**: `==>` (443/tcp, 80/tcp)
- **EC2 → RDS**: `-.->` (3306/tcp, 5432/tcp)
- **EC2 → EC2**: `-->` (22/tcp, custom ports)

## Example Output

### Mermaid Format

```mermaid
graph TD
    subgraph Account["Account: 123456789012"]
        subgraph VPC_vpc_12345678["VPC: Production"]
            subgraph Region_us_east_1["Region: us-east-1"]
                subgraph Subnet_subnet_public["Public Subnet"]
                    alb_prod[/"ALB: prod-alb<br/>10.0.1.10<br/>10.0.2.10"/]
                end
                subgraph Subnet_subnet_app["Application Subnet"]
                    ec2_web1["EC2: web-01<br/>10.0.3.10"]
                    ec2_web2["EC2: web-02<br/>10.0.3.20"]
                end
                subgraph Subnet_subnet_db["Restricted Subnet"]
                    rds_main[("RDS: main-db<br/>mysql")]
                end
            end
        end
    end
    
    route53_prod(["Route53: example.com"]) 
    route53_prod -->|"53/tcp"| alb_prod
    alb_prod ==>|"443/tcp"| ec2_web1
    alb_prod ==>|"443/tcp"| ec2_web2
    ec2_web1 -.->|"3306/tcp"| rds_main
    ec2_web2 -.->|"3306/tcp"| rds_main
```

### DOT/Graphviz Format

The DOT format generates professional diagrams with:
- **AWS Service Icons**: Authentic AWS icons for EC2, RDS, ALB, Route53
- **Hierarchical Clustering**: VPC, Region, and Subnet groupings with colored backgrounds
- **Styled Connections**: Different arrow styles and colors for different connection types
- **Multiple Output Formats**: PNG, SVG, PDF, and raw DOT files
- **High Resolution**: Vector graphics suitable for documentation and presentations

Example output files:
- `aws_infrastructure.dot` - DOT source file
- `aws_infrastructure.png` - High-resolution PNG image
- `aws_infrastructure.svg` - Scalable vector graphic
- `aws_infrastructure_metadata.json` - Generation metadata

## Security Considerations

- **Read-Only Access**: The server only requires read permissions
- **No Resource Modification**: No AWS resources are created or modified
- **Credential Security**: Uses standard AWS credential handling
- **Local Processing**: All diagram generation happens locally

### Required AWS Permissions

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

## Development

### Running Tests

```bash
uv run pytest
```

### Linting and Formatting

```bash
uv run ruff check .
uv run black .
```

### Running the Server Directly

```bash
# Run as module
uv run python -m aws_diagram_mcp

# Or run the server function
uv run python -c "from aws_diagram_mcp import serve; serve()"
```

## Troubleshooting

### Common Issues

1. **AWS Credentials Not Found**
   ```
   Error: Unable to locate credentials
   ```
   Solution: Configure AWS credentials using `aws configure` or environment variables

2. **No Resources Found**
   ```
   Error: No VPCs found
   ```
   Solution: Check the region and ensure resources exist in the specified region

3. **Permission Denied**
   ```
   Error: User is not authorized to perform: ec2:DescribeInstances
   ```
   Solution: Ensure your AWS credentials have the required read permissions

4. **Mermaid Syntax Errors**
   ```
   Error: Unclosed subgraph
   ```
   Solution: Use the `validate_mermaid_syntax` tool to check for syntax issues

5. **Graphviz Not Found**
   ```
   Error: dot not found in path
   ```
   Solution: Install Graphviz system package (see Installation section)

### Debug Mode

Set `LOG_LEVEL=DEBUG` in your environment to enable verbose logging:

```bash
export LOG_LEVEL=DEBUG
uv run python -m aws_diagram_mcp
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run tests and linting
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Documentation

📚 **Comprehensive Guides:**
- **[CONFIGURATION.md](CONFIGURATION.md)** - Detailed setup and configuration
- **[USAGE.md](USAGE.md)** - Usage examples and best practices
- **[EXAMPLES.md](EXAMPLES.md)** - Real-world scenarios and integrations
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and updates

## Support

For issues and questions:

1. **Check Documentation**: Review the guides above for detailed help
2. **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
3. **Examples**: Check [EXAMPLES.md](EXAMPLES.md) for usage patterns
4. **GitHub Issues**: Search existing issues or create a new one with detailed information

## Roadmap

### Completed Features
- [x] Support for DOT/Graphviz output with AWS icons
- [x] Professional diagram formatting with proper clustering
- [x] **Advanced Security Group Configuration**: Comprehensive filtering and display options
- [x] **Comprehensive CLI Tool**: Full-featured command-line interface
- [x] **Smart Connection Filtering**: Traffic flow analysis and behavioral filtering
- [x] **Preset Configurations**: Quick setup for common use cases

### Completed Features
- [x] **Multi-Region Support**: Cross-region resource discovery and visualization

### Planned Features
- [ ] **Additional AWS Services**: Lambda, API Gateway, CloudFront, ECS, EKS
- [ ] **Enhanced Resource Grouping**: Tag-based clustering and auto-scaling group visualization
- [ ] **Configuration Files**: YAML/JSON-based persistent configuration
- [ ] **Load Balancer Enhancements**: Target health status and detailed target group visualization
- [ ] **RDS Clustering**: Cluster grouping and parameter group relationships
- [ ] **Resource Filtering**: Include/exclude by tags, names, or patterns
- [ ] **Visual Styling**: Custom colors, shapes, and layouts
- [ ] **Export Formats**: draw.io, PlantUML, Visio compatibility
- [ ] **Cost Analysis Integration**: Resource cost annotations
- [ ] **Real-time Updates**: Dynamic diagram refresh capabilities
- [ ] **Interactive Filtering**: Web-based diagram manipulation