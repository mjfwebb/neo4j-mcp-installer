# neo4j-mcp-installer

Cross-platform installer for the Neo4j MCP server binary.

## Install

```bash
pipx install neo4j-mcp-installer
```

If you don't have pipx:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
pipx install neo4j-mcp-installer
```

## Use

```bash
neo4j-mcp-installer install                # Install the MCP binary
neo4j-mcp-installer --help                 # Show help
neo4j-mcp-installer upgrade                # Upgrade to latest version
neo4j-mcp-installer where                  # Show installation location
neo4j-mcp-installer uninstall              # Remove the installed binary
```

## Configure

Environment variables:

- `NEO4J_MCP_REPO="neo4j/mcp"` - GitHub repository (owner/repo)
- `NEO4J_MCP_VERSION="v1.2.3"` - Force specific version
- `NEO4J_MCP_BASE_URL="https://github.com/<repo>/releases/download"` - Custom download URL
- `NEO4J_MCP_SKIP_VERIFY="1"` - Skip SHA256 verification
