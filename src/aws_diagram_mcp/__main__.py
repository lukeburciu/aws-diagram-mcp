"""Entry point for running the MCP server as a module."""

from .server import serve


def main():
    """Main entry point for the aws-diagram-mcp command."""
    serve()


if __name__ == "__main__":
    main()