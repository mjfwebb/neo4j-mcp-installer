from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from .installer import data_root, default_install_dir, install_binary


def _on_path(dir_: Path) -> bool:
    path = os.environ.get("PATH", "")
    parts = [p.strip() for p in path.split(os.pathsep) if p.strip()]
    norm = {str(Path(p).resolve()) for p in parts}
    try:
        return str(dir_.resolve()) in norm
    except Exception:
        return str(dir_) in parts


def _print_path_help(install_dir: Path) -> None:
    if os.name == "nt":
        print("\nTo add to PATH on Windows:")
        print(f"  Add this folder to your PATH environment variable:\n  {install_dir}\n")
    else:
        print("\nIf `neo4j-mcp` is not found, add this to your shell config (~/.zshrc / ~/.bashrc):")
        print('  export PATH="$HOME/.local/bin:$PATH"\n')


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="neo4j-mcp-installer",
        description="Installer for the Neo4j MCP server binary (no launcher shim).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_install = sub.add_parser("install", help="Install the neo4j-mcp binary.")
    p_install.add_argument("--version", help="Release tag (e.g., v1.2.0). Default: latest.")
    p_install.add_argument("--install-dir", help="Custom install directory. Default: ~/.local/bin (Linux/macOS) or %%LOCALAPPDATA%% (Windows).")
    p_install.add_argument("--no-verify", action="store_true", help="Skip SHA256 checksum verification.")
    p_install.add_argument("--force", action="store_true", help="Force re-download and re-extract even if already installed.")

    p_upgrade = sub.add_parser("upgrade", help="Upgrade to the latest (or specified) version, always re-downloading.")
    p_upgrade.add_argument("--version", help="Release tag (e.g., v1.2.0). Default: latest.")
    p_upgrade.add_argument("--install-dir", help="Custom install directory. Default: ~/.local/bin (Linux/macOS) or %%LOCALAPPDATA%% (Windows).")
    p_upgrade.add_argument("--no-verify", action="store_true", help="Skip checksum verification.")

    p_where = sub.add_parser("where", help="Print where the neo4j-mcp binary is (or will be) installed.")

    p_uninstall = sub.add_parser("uninstall", help="Remove the installed neo4j-mcp binary.")
    p_uninstall.add_argument("--install-dir", help="Custom install directory where the binary was placed.")
    p_uninstall.add_argument("--clean-cache", action="store_true", help="Also remove downloaded archives and cached versions.")

    args = parser.parse_args()
    install_dir = Path(args.install_dir) if getattr(args, "install_dir", None) else default_install_dir()

    if args.cmd == "where":
        name = "neo4j-mcp.exe" if os.name == "nt" else "neo4j-mcp"
        print(str(install_dir / name))
        return

    if args.cmd == "uninstall":
        name = "neo4j-mcp.exe" if os.name == "nt" else "neo4j-mcp"
        path = install_dir / name
        if path.exists():
            path.unlink()
            print(f"Removed: {path}")
        else:
            print(f"Not found: {path}")
        
        if args.clean_cache:
            cache_dir = data_root()
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                print(f"Removed cache: {cache_dir}")
            else:
                print(f"Cache not found: {cache_dir}")
        return

    # install/upgrade
    verify = not getattr(args, "no_verify", False)
    force = bool(getattr(args, "force", False)) or args.cmd == "upgrade"

    final_path, resolved_version, extracted = install_binary(
        version=getattr(args, "version", None),
        verify=verify,
        force_download=force,
        install_dir=install_dir,
    )

    print(f"Installed: {final_path}")
    print(f"Version:   {resolved_version}")
    # Quick sanity hint if install dir isn't on PATH
    if not _on_path(install_dir):
        _print_path_help(install_dir)
    else:
        print("\nYou can now run:")
        print("  neo4j-mcp --help")
