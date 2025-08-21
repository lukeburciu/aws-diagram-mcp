# Usage Guide

This comprehensive guide covers all aspects of using the AWS Infrastructure Diagram MCP Server.

## Table of Contents

- [Quick Start](#quick-start)
- [Tool Reference](#tool-reference)
- [Best Practices](#best-practices)
- [Common Workflows](#common-workflows)
- [Performance Optimization](#performance-optimization)
- [Output Management](#output-management)

## Quick Start

### 1. Basic Infrastructure Discovery

Start by exploring what resources exist in your AWS account:

```python
# Discover all resources in the default region
result = discover_aws_resources({
    "region": "us-east-1"
})

print(f"Found {len(result['resources']['vpcs'])} VPCs")
print(f"Found {len(result['resources']['instances'])} EC2 instances")
print(f"Found {len(result['resources']['load_balancers'])} load balancers")
```

### 2. Generate Your First Diagram

Once you know what resources exist, generate a diagram:

```python
# Generate a simple Mermaid diagram
result = generate_aws_diagram({
    "aws_account": "my-company",
    "region": "us-east-1"
})

if result["success"]:
    print(f"Diagram saved to: {result['output_path']}")
else:
    print(f"Error: {result['error']}")
```

### 3. Professional Diagrams with AWS Icons

For presentations and formal documentation:

```python
# Generate a DOT diagram with AWS icons
result = generate_aws_diagram_dot({
    "aws_account": "my-company",
    "region": "us-east-1",
    "output_format": "png"
})

print(f"PNG diagram: {result['output_files']['png_file']}")
```

## Tool Reference

### `discover_aws_resources`

**Purpose:** Explore AWS resources without generating diagrams

**Parameters:**
- `region` (str): AWS region to scan (default: "us-east-1")
- `profile` (str, optional): AWS CLI profile name
- `resource_types` (list): Resource types to discover (default: ["all"])

**Resource Types:**
- `"all"` - All supported resource types
- `"vpcs"` - Virtual Private Clouds
- `"subnets"` - Subnets within VPCs
- `"instances"` - EC2 instances
- `"load_balancers"` - Application and Network Load Balancers
- `"rds"` - RDS database instances
- `"security_groups"` - Security group rules
- `"route53"` - Route53 hosted zones and records
- `"acm"` - ACM SSL certificates

**Example Usage:**
```python
# Discover only EC2 and RDS resources
result = discover_aws_resources({
    "region": "us-west-2",
    "profile": "production",
    "resource_types": ["instances", "rds"]
})
```

### `generate_aws_diagram`

**Purpose:** Generate Mermaid format diagrams for documentation

**Parameters:**
- `aws_account` (str, required): Account identifier for diagram title
- `region` (str): AWS region (default: "us-east-1")
- `profile` (str, optional): AWS CLI profile
- `output_path` (str, optional): Custom output file path
- `vpc_id` (str, optional): Generate diagram for specific VPC only
- `include_route53` (bool): Include Route53 zones (default: true)
- `include_acm` (bool): Include ACM certificates (default: true)

**Output Structure:**
```python
{
    "success": True,
    "message": "Diagram generated successfully",
    "output_path": "docs/as-built/my-account/my-account_mermaid.md",
    "statistics": {
        "vpcs": 2,
        "subnets": 6,
        "instances": 8,
        "load_balancers": 2,
        "rds_instances": 1,
        "security_groups": 12,
        "route53_zones": 3,
        "acm_certificates": 2
    },
    "diagram": "graph TD\n    subgraph Account..."
}
```

**Best For:**
- GitHub/GitLab documentation
- Wiki pages and README files
- Version-controlled documentation
- Quick sharing and collaboration

### `generate_aws_diagram_dot`

**Purpose:** Generate DOT/Graphviz format diagrams with AWS icons

**Parameters:**
- `aws_account` (str, required): Account identifier
- `region` (str): AWS region (default: "us-east-1")
- `profile` (str, optional): AWS CLI profile
- `output_path` (str, optional): Output file path (without extension)
- `vpc_id` (str, optional): Generate diagram for specific VPC
- `include_route53` (bool): Include Route53 zones (default: true)
- `include_acm` (bool): Include ACM certificates (default: true)
- `output_format` (str): Output format - "png", "svg", "pdf", or "dot" (default: "png")

**Output Structure:**
```python
{
    "success": True,
    "message": "DOT diagram generated successfully",
    "output_files": {
        "dot_file": "path/to/diagram.dot",
        "png_file": "path/to/diagram.png",
        "svg_file": "path/to/diagram.svg"
    },
    "output_format": "png",
    "statistics": {...}
}
```

**Best For:**
- Executive presentations
- Architecture review meetings
- High-quality documentation
- Print materials

### `validate_mermaid_syntax`

**Purpose:** Validate Mermaid diagram syntax

**Parameters:**
- `diagram` (str, required): Mermaid diagram text

**Example Usage:**
```python
# Validate a diagram before using it
diagram_text = """
graph TD
    A --> B
    B --> C
"""

result = validate_mermaid_syntax(diagram_text)
if result["valid"]:
    print("Diagram syntax is valid")
else:
    print(f"Syntax error: {result['error']}")
```

## Best Practices

### 1. Resource Organization

**Start with Discovery:**
```python
# Always discover resources first to understand scope
resources = discover_aws_resources({
    "region": "us-east-1",
    "resource_types": ["vpcs", "instances"]
})

# Choose appropriate VPC for focused diagrams
if len(resources['resources']['vpcs']) > 1:
    # Generate separate diagrams for each VPC
    for vpc in resources['resources']['vpcs']:
        generate_aws_diagram({
            "aws_account": f"vpc-{vpc['tags'].get('Name', vpc['vpc_id'])}",
            "vpc_id": vpc['vpc_id']
        })
```

**Use Meaningful Account Names:**
```python
# Good: descriptive names
generate_aws_diagram({"aws_account": "web-app-production"})
generate_aws_diagram({"aws_account": "data-pipeline-staging"})

# Avoid: generic names
generate_aws_diagram({"aws_account": "account1"})
```

### 2. Output Management

**Organize Output Files:**
```python
import datetime

timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
environment = "production"

# Organized file structure
generate_aws_diagram({
    "aws_account": environment,
    "output_path": f"docs/infrastructure/{environment}/{timestamp}-infrastructure.md"
})

generate_aws_diagram_dot({
    "aws_account": environment,
    "output_path": f"diagrams/{environment}/{timestamp}-architecture",
    "output_format": "svg"
})
```

**Version Control Integration:**
```python
# Use consistent naming for version control
def generate_versioned_diagrams(environment, git_commit):
    base_path = f"docs/{environment}"
    
    # Always generate latest
    generate_aws_diagram({
        "aws_account": environment,
        "output_path": f"{base_path}/current-infrastructure.md"
    })
    
    # Archive with version
    generate_aws_diagram({
        "aws_account": environment,
        "output_path": f"{base_path}/archive/{git_commit}-infrastructure.md"
    })
```

### 3. Performance Optimization

**Selective Resource Discovery:**
```python
# For large accounts, discover incrementally
core_resources = discover_aws_resources({
    "resource_types": ["vpcs", "instances", "load_balancers"]
})

# Only get security groups for discovered instances
if core_resources['resources']['instances']:
    full_resources = discover_aws_resources({
        "resource_types": ["security_groups"]
    })
```

**Regional Optimization:**
```python
# Process multiple regions efficiently
regions = ["us-east-1", "us-west-2", "eu-west-1"]
results = {}

for region in regions:
    # Quick check if region has resources
    vpc_check = discover_aws_resources({
        "region": region,
        "resource_types": ["vpcs"]
    })
    
    if vpc_check['resources']['vpcs']:
        results[region] = generate_aws_diagram({
            "aws_account": f"global-{region}",
            "region": region
        })
```

### 4. Error Handling

**Robust Error Handling:**
```python
def safe_diagram_generation(account_name, **kwargs):
    try:
        result = generate_aws_diagram({
            "aws_account": account_name,
            **kwargs
        })
        
        if result["success"]:
            print(f"✓ Generated diagram: {result['output_path']}")
            return result
        else:
            print(f"✗ Failed: {result['error']}")
            return None
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")
        return None

# Usage
result = safe_diagram_generation("my-app", region="us-east-1")
if result:
    print(f"Found {result['statistics']['instances']} instances")
```

**Credential Validation:**
```python
def validate_aws_access(profile=None):
    """Validate AWS access before generating diagrams"""
    try:
        # Test AWS connectivity
        test_result = discover_aws_resources({
            "profile": profile,
            "resource_types": ["account"]
        })
        
        if test_result["success"]:
            account_info = test_result["resources"]["account"]
            print(f"✓ Connected to AWS account: {account_info['account_id']}")
            return True
        else:
            print(f"✗ AWS access failed: {test_result['error']}")
            return False
            
    except Exception as e:
        print(f"✗ AWS validation error: {str(e)}")
        return False

# Validate before generating diagrams
if validate_aws_access("production"):
    generate_aws_diagram({"aws_account": "prod", "profile": "production"})
```

## Common Workflows

### 1. Infrastructure Documentation Workflow

```python
def document_infrastructure(environment, git_branch="main"):
    """Complete infrastructure documentation workflow"""
    
    print(f"📋 Documenting {environment} infrastructure...")
    
    # 1. Discover resources
    print("🔍 Discovering resources...")
    resources = discover_aws_resources({
        "profile": environment,
        "resource_types": ["all"]
    })
    
    if not resources["success"]:
        print(f"❌ Discovery failed: {resources['error']}")
        return False
    
    stats = {
        "vpcs": len(resources['resources'].get('vpcs', [])),
        "instances": len(resources['resources'].get('instances', [])),
        "load_balancers": len(resources['resources'].get('load_balancers', []))
    }
    
    print(f"📊 Found: {stats['vpcs']} VPCs, {stats['instances']} instances, {stats['load_balancers']} LBs")
    
    # 2. Generate Mermaid for documentation
    print("📝 Generating Mermaid diagram...")
    mermaid_result = generate_aws_diagram({
        "aws_account": environment,
        "profile": environment,
        "output_path": f"docs/{environment}/README.md"
    })
    
    # 3. Generate PNG for presentations
    print("🎨 Generating PNG diagram...")
    png_result = generate_aws_diagram_dot({
        "aws_account": environment,
        "profile": environment,
        "output_path": f"diagrams/{environment}/architecture",
        "output_format": "png"
    })
    
    # 4. Generate SVG for web
    print("🌐 Generating SVG diagram...")
    svg_result = generate_aws_diagram_dot({
        "aws_account": environment,
        "profile": environment,
        "output_path": f"diagrams/{environment}/architecture-web",
        "output_format": "svg"
    })
    
    if all([mermaid_result["success"], png_result["success"], svg_result["success"]]):
        print(f"✅ Successfully documented {environment} infrastructure")
        return {
            "mermaid": mermaid_result["output_path"],
            "png": png_result["output_files"]["png_file"],
            "svg": svg_result["output_files"]["svg_file"],
            "statistics": mermaid_result["statistics"]
        }
    else:
        print("❌ Some diagram generation failed")
        return False

# Usage
result = document_infrastructure("production")
if result:
    print(f"📁 Documentation files created:")
    print(f"  - README: {result['mermaid']}")
    print(f"  - PNG: {result['png']}")
    print(f"  - SVG: {result['svg']}")
```

### 2. Multi-Environment Comparison

```python
def compare_environments():
    """Generate diagrams for multiple environments for comparison"""
    
    environments = [
        {"name": "development", "profile": "dev", "region": "us-east-1"},
        {"name": "staging", "profile": "staging", "region": "us-east-1"},
        {"name": "production", "profile": "prod", "region": "us-west-2"}
    ]
    
    results = {}
    
    for env in environments:
        print(f"🏗️ Processing {env['name']} environment...")
        
        # Generate diagrams for each environment
        mermaid_result = generate_aws_diagram({
            "aws_account": env["name"],
            "profile": env["profile"],
            "region": env["region"],
            "output_path": f"docs/environments/{env['name']}-infrastructure.md"
        })
        
        dot_result = generate_aws_diagram_dot({
            "aws_account": env["name"],
            "profile": env["profile"], 
            "region": env["region"],
            "output_path": f"diagrams/environments/{env['name']}-comparison",
            "output_format": "png"
        })
        
        if mermaid_result["success"] and dot_result["success"]:
            results[env["name"]] = {
                "statistics": mermaid_result["statistics"],
                "mermaid_path": mermaid_result["output_path"],
                "png_path": dot_result["output_files"]["png_file"]
            }
        else:
            print(f"❌ Failed to process {env['name']}")
    
    # Generate comparison report
    print("\n📊 Environment Comparison:")
    for env_name, data in results.items():
        stats = data["statistics"]
        print(f"  {env_name:12}: {stats['instances']:2d} instances, {stats['load_balancers']:2d} LBs, {stats['rds_instances']:2d} RDS")
    
    return results
```

### 3. Security Audit Workflow

```python
def security_audit_diagrams():
    """Generate diagrams focused on security analysis"""
    
    print("🔒 Starting security audit documentation...")
    
    # 1. Discover security-relevant resources
    resources = discover_aws_resources({
        "resource_types": ["instances", "load_balancers", "rds", "security_groups"]
    })
    
    if not resources["success"]:
        print(f"❌ Resource discovery failed: {resources['error']}")
        return
    
    # 2. Analyze security groups for potential issues
    security_issues = []
    sg_data = resources['resources'].get('security_groups', {})
    
    for sg_id, sg_info in sg_data.items():
        for rule in sg_info.get('rules', {}).get('ingress', []):
            for source in rule.get('sources', []):
                # Check for overly permissive rules
                if source.get('type') == 'cidr' and source.get('value') == '0.0.0.0/0':
                    security_issues.append({
                        "security_group": sg_info['name'],
                        "issue": "Open to internet",
                        "protocol": rule.get('protocol', 'unknown'),
                        "port": rule.get('to_port', 'all')
                    })
    
    print(f"⚠️ Found {len(security_issues)} potential security issues")
    
    # 3. Generate focused security diagram
    result = generate_aws_diagram_dot({
        "aws_account": "security-audit",
        "include_route53": False,  # Focus on internal architecture
        "include_acm": False,
        "output_path": "security/current-architecture",
        "output_format": "svg"
    })
    
    if result["success"]:
        print(f"✅ Security diagram generated: {result['output_files']['svg_file']}")
        
        # Create security report
        report_path = "security/security-analysis.md"
        with open(report_path, 'w') as f:
            f.write("# Security Analysis Report\n\n")
            f.write("## Architecture Diagram\n\n")
            f.write(f"![Security Architecture]({result['output_files']['svg_file']})\n\n")
            f.write("## Security Issues Found\n\n")
            
            for issue in security_issues:
                f.write(f"- **{issue['security_group']}**: {issue['issue']} on {issue['protocol']}:{issue['port']}\n")
        
        print(f"📄 Security report generated: {report_path}")
        return result
    else:
        print(f"❌ Security diagram failed: {result['error']}")
```

## Performance Optimization

### 1. Caching Resource Discovery

```python
import pickle
import time
from pathlib import Path

def cached_resource_discovery(region, profile=None, cache_duration=300):
    """Cache resource discovery results for performance"""
    
    cache_file = Path(f".cache/resources_{region}_{profile or 'default'}.pkl")
    cache_file.parent.mkdir(exist_ok=True)
    
    # Check if cache exists and is recent
    if cache_file.exists():
        cache_age = time.time() - cache_file.stat().st_mtime
        if cache_age < cache_duration:
            print(f"📦 Using cached resources (age: {cache_age:.0f}s)")
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
    
    # Discover resources
    print("🔍 Discovering resources...")
    resources = discover_aws_resources({
        "region": region,
        "profile": profile
    })
    
    # Cache results
    if resources["success"]:
        with open(cache_file, 'wb') as f:
            pickle.dump(resources, f)
        print(f"💾 Cached resources to {cache_file}")
    
    return resources
```

### 2. Parallel Processing

```python
import concurrent.futures
from typing import List, Dict

def parallel_diagram_generation(environments: List[Dict]) -> Dict:
    """Generate diagrams for multiple environments in parallel"""
    
    def generate_env_diagrams(env_config):
        """Generate diagrams for a single environment"""
        env_name = env_config["name"]
        
        try:
            # Generate Mermaid diagram
            mermaid_result = generate_aws_diagram({
                "aws_account": env_name,
                "profile": env_config.get("profile"),
                "region": env_config.get("region", "us-east-1"),
                "output_path": f"docs/{env_name}/infrastructure.md"
            })
            
            # Generate DOT diagram
            dot_result = generate_aws_diagram_dot({
                "aws_account": env_name,
                "profile": env_config.get("profile"),
                "region": env_config.get("region", "us-east-1"),
                "output_path": f"diagrams/{env_name}/architecture",
                "output_format": "png"
            })
            
            return {
                "environment": env_name,
                "success": mermaid_result["success"] and dot_result["success"],
                "mermaid": mermaid_result,
                "dot": dot_result
            }
            
        except Exception as e:
            return {
                "environment": env_name,
                "success": False,
                "error": str(e)
            }
    
    # Execute in parallel
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_env = {
            executor.submit(generate_env_diagrams, env): env["name"] 
            for env in environments
        }
        
        for future in concurrent.futures.as_completed(future_to_env):
            env_name = future_to_env[future]
            try:
                result = future.result()
                results[env_name] = result
                
                if result["success"]:
                    print(f"✅ {env_name} completed")
                else:
                    print(f"❌ {env_name} failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ {env_name} exception: {str(e)}")
                results[env_name] = {"success": False, "error": str(e)}
    
    return results

# Usage
environments = [
    {"name": "dev", "profile": "development", "region": "us-east-1"},
    {"name": "staging", "profile": "staging", "region": "us-east-1"}, 
    {"name": "prod", "profile": "production", "region": "us-west-2"}
]

results = parallel_diagram_generation(environments)
```

## Output Management

### 1. Automated Cleanup

```python
import os
import glob
from datetime import datetime, timedelta

def cleanup_old_diagrams(base_path="docs", days_to_keep=30):
    """Clean up old diagram files"""
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    # Find all diagram files
    patterns = [
        f"{base_path}/**/*_mermaid.md",
        f"{base_path}/**/*.dot",
        f"{base_path}/**/*.png",
        f"{base_path}/**/*.svg"
    ]
    
    cleaned_files = []
    
    for pattern in patterns:
        for file_path in glob.glob(pattern, recursive=True):
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_date:
                    os.remove(file_path)
                    cleaned_files.append(file_path)
            except OSError as e:
                print(f"Warning: Could not remove {file_path}: {e}")
    
    print(f"🧹 Cleaned up {len(cleaned_files)} old diagram files")
    return cleaned_files
```

### 2. Archive Management

```python
def archive_diagrams(source_dir="docs", archive_dir="archive"):
    """Archive current diagrams before generating new ones"""
    
    import shutil
    from pathlib import Path
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archive_path = Path(archive_dir) / timestamp
    
    if Path(source_dir).exists():
        shutil.copytree(source_dir, archive_path)
        print(f"📦 Archived diagrams to {archive_path}")
        return str(archive_path)
    
    return None
```

This usage guide provides comprehensive coverage of all the tools and best practices for effectively using the AWS Infrastructure Diagram MCP Server.