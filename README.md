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

## Install from Source

To install locally from the git repository:

```bash
git clone https://github.com/mjfwebb/neo4j-mcp-installer.git
cd neo4j-mcp-installer
pipx install -e .
```

## Use

```bash
# Basic commands
neo4j-mcp-installer install                      # Install the latest version
neo4j-mcp-installer upgrade                      # Upgrade to the latest version
neo4j-mcp-installer where                        # Show installation location
neo4j-mcp-installer uninstall                    # Remove the installed binary

# Install options
neo4j-mcp-installer install --version v1.2.0     # Install specific version
neo4j-mcp-installer install --install-dir ~/bin  # Install to custom directory
neo4j-mcp-installer install --force              # Force re-download
neo4j-mcp-installer install --no-verify          # Skip checksum verification

# Uninstall options
neo4j-mcp-installer uninstall --clean-cache      # Remove binary and all cached files
neo4j-mcp-installer uninstall --install-dir ~/bin # Uninstall from custom directory

# Show help
neo4j-mcp-installer --help                       # General help
neo4j-mcp-installer install --help               # Help for install command
```

## Configure

Environment variables:

- `NEO4J_MCP_REPO="neo4j/mcp"` - GitHub repository (owner/repo)
- `NEO4J_MCP_VERSION="v1.2.3"` - Force specific version
- `NEO4J_MCP_BASE_URL="https://github.com/<repo>/releases/download"` - Custom download URL
- `NEO4J_MCP_SKIP_VERIFY="1"` - Skip SHA256 verification
