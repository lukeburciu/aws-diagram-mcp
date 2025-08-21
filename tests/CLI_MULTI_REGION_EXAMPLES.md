# CLI Multi-Region Usage Examples

The AWS Diagram MCP CLI now supports scanning multiple AWS regions in a single command.

## Basic Usage

### Single Region (default)
```bash
# Uses default region (us-east-1 or AWS_DEFAULT_REGION)
uv run python cli.py discover

# Specify a single region
uv run python cli.py --regions us-west-2 discover
```

### Multiple Regions
```bash
# Scan multiple regions at once
uv run python cli.py --regions us-east-1 us-west-2 eu-west-1 discover

# Generate Mermaid diagram for multiple regions
uv run python cli.py --regions us-east-1 us-west-2 mermaid -o multi-region.md

# Generate DOT diagram for multiple regions
uv run python cli.py --regions us-east-1 us-west-2 ap-southeast-1 dot -o infrastructure
```

## Examples with Options

### Discovery across regions with specific output
```bash
uv run python cli.py \
  --regions us-east-1 us-west-2 eu-west-1 \
  --profile production \
  discover \
  -o discovered-resources.json
```

### Generate comprehensive multi-region diagram
```bash
uv run python cli.py \
  --regions us-east-1 us-west-2 \
  --profile myprofile \
  --include-route53 \
  --include-acm \
  dot \
  --format png \
  -o aws-global-infrastructure
```

### Security-focused multi-region view
```bash
uv run python cli.py \
  --regions us-east-1 us-west-2 eu-west-1 \
  --sg-preset security \
  --lb-display all \
  dot \
  -o security-audit
```

## How It Works

When multiple regions are specified:

1. **Resource Discovery**: The tool queries each region in parallel for all AWS resources
2. **Region Tagging**: Each discovered resource is tagged with its source region
3. **Security Groups**: Security groups are efficiently queried per-region to minimize API calls
4. **Diagram Generation**: 
   - Resources are grouped by region in the diagram
   - Each region appears as a separate cluster/subgraph
   - Cross-region connections are clearly visible

## Benefits

- **Single Command**: Get a complete view of your multi-region infrastructure
- **Efficient**: Parallel discovery across regions
- **Clear Visualization**: Diagrams show regional boundaries and relationships
- **Cost Effective**: Minimize API calls with intelligent batching

## Migration from Single Region

If you have existing scripts using the old `--region` flag:

```bash
# Old way (still supported but deprecated)
python cli.py --region us-east-1 discover

# New way
python cli.py --regions us-east-1 discover
```

## Environment Variables

You can set a default region:
```bash
export AWS_DEFAULT_REGION=us-west-2
python cli.py discover  # Will use us-west-2 as default
```

## Performance Considerations

- Each region is queried in parallel for better performance
- Security groups are batched by region to minimize API calls
- Consider using `--vpc-id` to limit scope when dealing with many regions