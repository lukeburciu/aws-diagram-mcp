# Changelog
All notable changes to the AWS Infrastructure Diagram MCP Server will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
## [0.2.0] - 2024-12-28
### Added
- **DOT/Graphviz Support**: New `generate_aws_diagram_dot` tool for professional diagrams
- **AWS Icons**: Authentic AWS service icons in DOT diagrams (EC2, RDS, ALB, Route53, etc.)
- **Multiple Output Formats**: Support for PNG, SVG, PDF, and DOT output formats
- **Enhanced Documentation**: Comprehensive guides for configuration, usage, and troubleshooting
  - `CONFIGURATION.md` - Complete setup and configuration guide
  - `USAGE.md` - Detailed usage examples and workflows
  - `EXAMPLES.md` - Real-world usage scenarios and integrations
  - `TROUBLESHOOTING.md` - Common issues and solutions
- **Professional Styling**: Hierarchical clustering with proper VPC/subnet organization
- **Connection Styling**: Different arrow styles and colors for different connection types
- **Metadata Generation**: Diagram metadata files for tracking generation details
- **Performance Optimizations**: Improved resource discovery and diagram generation
- **Error Handling**: Enhanced error handling and validation
### Enhanced
- **Resource Discovery**: More comprehensive AWS resource discovery
- **Security Group Analysis**: Better security group rule processing and visualization  
- **Load Balancer Mapping**: Improved target group and listener discovery
- **Subnet Classification**: Automatic subnet tier detection (presentation/application/restricted)
- **Node Identification**: Better resource naming and identification
- **Documentation**: Significantly expanded and improved documentation
### Dependencies
- Added `diagrams>=0.23.0` for professional diagram generation
- Added `graphviz>=0.20.0` for DOT format support
### Configuration
- Updated MCP configuration examples
- Added environment variable documentation
- Enhanced AWS credential setup instructions
## [0.1.0] - 2024-12-27
### Added
- **Initial Release**: Basic MCP server for AWS infrastructure diagrams
- ** Support**: Generate  format diagrams
- **Core Tools**:
  - `generate_aws_diagram` - Generate  diagrams
  - `discover_aws_resources` - Explore AWS resources
  - `validate__syntax` - Validate diagram syntax
- **AWS Integration**: Complete AWS resource discovery
  - VPC and subnet discovery
  - EC2 instance enumeration
  - Load balancer mapping
  - RDS instance discovery
  - Security group analysis
  - Route53 zone discovery
  - ACM certificate listing
- **Resource Organization**: Hierarchical diagram structure
  - Account level organization
  - VPC-based grouping
  - Regional separation
  - Subnet tier classification
- **Connection Mapping**: Security group based connections
- **FastMCP Framework**: Built on FastMCP for robust MCP integration
- **AWS SDK Integration**: boto3-based AWS resource discovery
- **Flexible Configuration**: Support for AWS profiles and regions
### Dependencies
- `fastmcp>=0.1.0` - MCP server framework
- `boto3>=1.35.0` - AWS SDK for Python
- `pydantic>=2.0.0` - Data validation
- `typing-extensions>=4.0.0` - Enhanced type hints
### Configuration
- Basic MCP server configuration
- AWS credential setup
- Environment variable support
---
## Planned Features
### [0.3.0] - Future
- **Additional AWS Services**:
  - Lambda functions
  - API Gateway
  - CloudFront distributions
  - S3 buckets (when referenced by other resources)
  - NAT Gateways and Internet Gateways
  - VPC Endpoints
- **Enhanced Visualizations**:
  - Cost information overlay
  - Performance metrics integration
  - Compliance status indicators
- **Interactive Features**:
  - Diagram filtering and customization
  - Resource highlighting
  - Zoom and navigation controls
- **Export Options**:
  - Draw.io format export
  - PlantUML format export
  - Visio format export
### [0.4.0] - Future
- **Multi-Region Support**: Cross-region infrastructure visualization
- **Real-Time Updates**: Live diagram updates with resource changes
- **Template Generation**: CloudFormation/Terraform template generation from diagrams
- **Compliance Checking**: Built-in security and compliance validation
- **Cost Analysis**: Resource cost visualization and optimization suggestions
---
## Contributing
We welcome contributions! Please see our contributing guidelines for more information.
## Support
- **Documentation**: See the comprehensive guides in the repository
- **Issues**: Report bugs and request features on GitHub
- **Community**: Join discussions and get help from other users