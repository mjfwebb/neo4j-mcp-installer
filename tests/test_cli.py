"""Tests for the CLI module."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from neo4j_mcp_installer.cli import _on_path, _print_path_help, main


class TestOnPath:
    """Tests for the _on_path helper function."""

    def test_on_path_returns_true_when_dir_in_path(self, tmp_path):
        """Test that _on_path returns True when directory is in PATH."""
        test_dir = tmp_path / "bin"
        test_dir.mkdir()
        
        with patch.dict(os.environ, {"PATH": str(test_dir)}):
            assert _on_path(test_dir) is True

    def test_on_path_returns_false_when_dir_not_in_path(self, tmp_path):
        """Test that _on_path returns False when directory is not in PATH."""
        test_dir = tmp_path / "bin"
        test_dir.mkdir()
        other_dir = tmp_path / "other"
        
        with patch.dict(os.environ, {"PATH": str(other_dir)}):
            assert _on_path(test_dir) is False

    def test_on_path_handles_empty_path(self, tmp_path):
        """Test that _on_path handles empty PATH."""
        test_dir = tmp_path / "bin"
        test_dir.mkdir()
        
        with patch.dict(os.environ, {"PATH": ""}):
            assert _on_path(test_dir) is False

    def test_on_path_handles_multiple_paths(self, tmp_path):
        """Test that _on_path handles multiple directories in PATH."""
        test_dir = tmp_path / "bin"
        test_dir.mkdir()
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        
        path_value = os.pathsep.join([str(other_dir), str(test_dir)])
        with patch.dict(os.environ, {"PATH": path_value}):
            assert _on_path(test_dir) is True

    def test_on_path_handles_resolve_exception(self):
        """Test that _on_path handles exceptions from resolve()."""
        # Create a mock Path that raises an exception on resolve()
        mock_path = MagicMock(spec=Path)
        mock_path.resolve.side_effect = OSError("Cannot resolve path")
        mock_path.__str__ = MagicMock(return_value="/test/path")
        
        # Set up PATH with the same string representation
        with patch.dict(os.environ, {"PATH": "/test/path"}):
            # Should fall back to string comparison and return True
            assert _on_path(mock_path) is True
        
        # Test when not in PATH
        with patch.dict(os.environ, {"PATH": "/other/path"}):
            assert _on_path(mock_path) is False


class TestPrintPathHelp:
    """Tests for the _print_path_help function."""

    def test_print_path_help_windows(self, tmp_path, capsys):
        """Test Windows-specific PATH help."""
        with patch("neo4j_mcp_installer.cli.os.name", "nt"):
            _print_path_help(tmp_path)
            
        captured = capsys.readouterr()
        assert "Windows" in captured.out
        assert str(tmp_path) in captured.out

    def test_print_path_help_unix(self, tmp_path, capsys):
        """Test Unix-specific PATH help."""
        with patch("neo4j_mcp_installer.cli.os.name", "posix"):
            _print_path_help(tmp_path)
            
        captured = capsys.readouterr()
        assert "~/.zshrc" in captured.out or "~/.bashrc" in captured.out
        assert ".local/bin" in captured.out


class TestMainInstall:
    """Tests for the install command."""

    @patch("neo4j_mcp_installer.cli.install_binary")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli._on_path")
    def test_install_basic(self, mock_on_path, mock_default_dir, mock_install, tmp_path):
        """Test basic install command."""
        mock_default_dir.return_value = tmp_path
        mock_on_path.return_value = True
        mock_install.return_value = (tmp_path / "neo4j-mcp", "v1.0.0", tmp_path / "extracted")
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "install"]):
            main()
        
        mock_install.assert_called_once_with(
            version=None,
            verify=True,
            force_download=False,
            install_dir=tmp_path,
        )

    @patch("neo4j_mcp_installer.cli.install_binary")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli._on_path")
    def test_install_with_version(self, mock_on_path, mock_default_dir, mock_install, tmp_path):
        """Test install with specific version."""
        mock_default_dir.return_value = tmp_path
        mock_on_path.return_value = True
        mock_install.return_value = (tmp_path / "neo4j-mcp", "v1.2.0", tmp_path / "extracted")
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "install", "--version", "v1.2.0"]):
            main()
        
        mock_install.assert_called_once_with(
            version="v1.2.0",
            verify=True,
            force_download=False,
            install_dir=tmp_path,
        )

    @patch("neo4j_mcp_installer.cli.install_binary")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli._on_path")
    def test_install_with_custom_dir(self, mock_on_path, mock_default_dir, mock_install, tmp_path):
        """Test install with custom install directory."""
        custom_dir = tmp_path / "custom"
        mock_default_dir.return_value = tmp_path
        mock_on_path.return_value = True
        mock_install.return_value = (custom_dir / "neo4j-mcp", "v1.0.0", custom_dir / "extracted")
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "install", "--install-dir", str(custom_dir)]):
            main()
        
        mock_install.assert_called_once_with(
            version=None,
            verify=True,
            force_download=False,
            install_dir=custom_dir,
        )

    @patch("neo4j_mcp_installer.cli.install_binary")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli._on_path")
    def test_install_no_verify(self, mock_on_path, mock_default_dir, mock_install, tmp_path):
        """Test install with --no-verify flag."""
        mock_default_dir.return_value = tmp_path
        mock_on_path.return_value = True
        mock_install.return_value = (tmp_path / "neo4j-mcp", "v1.0.0", tmp_path / "extracted")
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "install", "--no-verify"]):
            main()
        
        mock_install.assert_called_once_with(
            version=None,
            verify=False,
            force_download=False,
            install_dir=tmp_path,
        )

    @patch("neo4j_mcp_installer.cli.install_binary")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli._on_path")
    def test_install_force(self, mock_on_path, mock_default_dir, mock_install, tmp_path):
        """Test install with --force flag."""
        mock_default_dir.return_value = tmp_path
        mock_on_path.return_value = True
        mock_install.return_value = (tmp_path / "neo4j-mcp", "v1.0.0", tmp_path / "extracted")
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "install", "--force"]):
            main()
        
        mock_install.assert_called_once_with(
            version=None,
            verify=True,
            force_download=True,
            install_dir=tmp_path,
        )

    @patch("neo4j_mcp_installer.cli.install_binary")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli._on_path")
    def test_install_all_flags(self, mock_on_path, mock_default_dir, mock_install, tmp_path):
        """Test install with all flags combined."""
        custom_dir = tmp_path / "custom"
        mock_default_dir.return_value = tmp_path
        mock_on_path.return_value = True
        mock_install.return_value = (custom_dir / "neo4j-mcp", "v1.5.0", custom_dir / "extracted")
        
        with patch.object(
            sys,
            "argv",
            ["neo4j-mcp-installer", "install", "--version", "v1.5.0", "--install-dir", str(custom_dir), "--no-verify", "--force"],
        ):
            main()
        
        mock_install.assert_called_once_with(
            version="v1.5.0",
            verify=False,
            force_download=True,
            install_dir=custom_dir,
        )

    @patch("neo4j_mcp_installer.cli.install_binary")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli._on_path")
    def test_install_shows_path_help_when_not_on_path(self, mock_on_path, mock_default_dir, mock_install, tmp_path, capsys):
        """Test that install shows PATH help when install dir is not on PATH."""
        mock_default_dir.return_value = tmp_path
        mock_on_path.return_value = False
        mock_install.return_value = (tmp_path / "neo4j-mcp", "v1.0.0", tmp_path / "extracted")
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "install"]):
            main()
        
        captured = capsys.readouterr()
        assert "PATH" in captured.out or "path" in captured.out.lower()


class TestMainUpgrade:
    """Tests for the upgrade command."""

    @patch("neo4j_mcp_installer.cli.install_binary")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli._on_path")
    def test_upgrade_basic(self, mock_on_path, mock_default_dir, mock_install, tmp_path):
        """Test basic upgrade command."""
        mock_default_dir.return_value = tmp_path
        mock_on_path.return_value = True
        mock_install.return_value = (tmp_path / "neo4j-mcp", "v2.0.0", tmp_path / "extracted")
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "upgrade"]):
            main()
        
        mock_install.assert_called_once_with(
            version=None,
            verify=True,
            force_download=True,  # upgrade always forces
            install_dir=tmp_path,
        )

    @patch("neo4j_mcp_installer.cli.install_binary")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli._on_path")
    def test_upgrade_with_version(self, mock_on_path, mock_default_dir, mock_install, tmp_path):
        """Test upgrade with specific version."""
        mock_default_dir.return_value = tmp_path
        mock_on_path.return_value = True
        mock_install.return_value = (tmp_path / "neo4j-mcp", "v2.1.0", tmp_path / "extracted")
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "upgrade", "--version", "v2.1.0"]):
            main()
        
        mock_install.assert_called_once_with(
            version="v2.1.0",
            verify=True,
            force_download=True,
            install_dir=tmp_path,
        )

    @patch("neo4j_mcp_installer.cli.install_binary")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli._on_path")
    def test_upgrade_with_custom_dir(self, mock_on_path, mock_default_dir, mock_install, tmp_path):
        """Test upgrade with custom install directory."""
        custom_dir = tmp_path / "custom"
        mock_default_dir.return_value = tmp_path
        mock_on_path.return_value = True
        mock_install.return_value = (custom_dir / "neo4j-mcp", "v2.0.0", custom_dir / "extracted")
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "upgrade", "--install-dir", str(custom_dir)]):
            main()
        
        mock_install.assert_called_once_with(
            version=None,
            verify=True,
            force_download=True,
            install_dir=custom_dir,
        )

    @patch("neo4j_mcp_installer.cli.install_binary")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli._on_path")
    def test_upgrade_no_verify(self, mock_on_path, mock_default_dir, mock_install, tmp_path):
        """Test upgrade with --no-verify flag."""
        mock_default_dir.return_value = tmp_path
        mock_on_path.return_value = True
        mock_install.return_value = (tmp_path / "neo4j-mcp", "v2.0.0", tmp_path / "extracted")
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "upgrade", "--no-verify"]):
            main()
        
        mock_install.assert_called_once_with(
            version=None,
            verify=False,
            force_download=True,
            install_dir=tmp_path,
        )


class TestMainWhere:
    """Tests for the where command."""

    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli.os.name", "posix")
    def test_where_default_unix(self, mock_default_dir, tmp_path, capsys):
        """Test where command on Unix."""
        mock_default_dir.return_value = tmp_path
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "where"]):
            main()
        
        captured = capsys.readouterr()
        assert str(tmp_path / "neo4j-mcp") == captured.out.strip()

    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli.os.name", "nt")
    def test_where_default_windows(self, mock_default_dir, tmp_path, capsys):
        """Test where command on Windows."""
        mock_default_dir.return_value = tmp_path
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "where"]):
            main()
        
        captured = capsys.readouterr()
        assert str(tmp_path / "neo4j-mcp.exe") == captured.out.strip()


class TestMainUninstall:
    """Tests for the uninstall command."""

    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli.os.name", "posix")
    def test_uninstall_existing_binary(self, mock_default_dir, tmp_path, capsys):
        """Test uninstalling an existing binary."""
        mock_default_dir.return_value = tmp_path
        binary_path = tmp_path / "neo4j-mcp"
        binary_path.touch()
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "uninstall"]):
            main()
        
        captured = capsys.readouterr()
        assert not binary_path.exists()
        assert "Removed:" in captured.out
        assert str(binary_path) in captured.out

    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli.os.name", "posix")
    def test_uninstall_nonexistent_binary(self, mock_default_dir, tmp_path, capsys):
        """Test uninstalling when binary doesn't exist."""
        mock_default_dir.return_value = tmp_path
        binary_path = tmp_path / "neo4j-mcp"
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "uninstall"]):
            main()
        
        captured = capsys.readouterr()
        assert "Not found:" in captured.out
        assert str(binary_path) in captured.out

    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli.os.name", "nt")
    def test_uninstall_windows(self, mock_default_dir, tmp_path, capsys):
        """Test uninstalling on Windows."""
        mock_default_dir.return_value = tmp_path
        binary_path = tmp_path / "neo4j-mcp.exe"
        binary_path.touch()
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "uninstall"]):
            main()
        
        captured = capsys.readouterr()
        assert not binary_path.exists()
        assert "Removed:" in captured.out

    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli.os.name", "posix")
    def test_uninstall_with_custom_dir(self, mock_default_dir, tmp_path, capsys):
        """Test uninstalling from custom directory."""
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        mock_default_dir.return_value = tmp_path
        binary_path = custom_dir / "neo4j-mcp"
        binary_path.touch()
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "uninstall", "--install-dir", str(custom_dir)]):
            main()
        
        captured = capsys.readouterr()
        assert not binary_path.exists()
        assert "Removed:" in captured.out

    @patch("neo4j_mcp_installer.cli.data_root")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli.os.name", "posix")
    def test_uninstall_with_clean_cache(self, mock_default_dir, mock_data_root, tmp_path, capsys):
        """Test uninstalling with --clean-cache flag."""
        mock_default_dir.return_value = tmp_path
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "test.txt").touch()
        mock_data_root.return_value = cache_dir
        
        binary_path = tmp_path / "neo4j-mcp"
        binary_path.touch()
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "uninstall", "--clean-cache"]):
            main()
        
        captured = capsys.readouterr()
        assert not binary_path.exists()
        assert not cache_dir.exists()
        assert "Removed cache:" in captured.out
        assert str(cache_dir) in captured.out

    @patch("neo4j_mcp_installer.cli.data_root")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli.os.name", "posix")
    def test_uninstall_clean_cache_when_cache_missing(self, mock_default_dir, mock_data_root, tmp_path, capsys):
        """Test uninstalling with --clean-cache when cache doesn't exist."""
        mock_default_dir.return_value = tmp_path
        cache_dir = tmp_path / "cache"
        mock_data_root.return_value = cache_dir
        
        binary_path = tmp_path / "neo4j-mcp"
        binary_path.touch()
        
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "uninstall", "--clean-cache"]):
            main()
        
        captured = capsys.readouterr()
        assert "Cache not found:" in captured.out
        assert str(cache_dir) in captured.out

    @patch("neo4j_mcp_installer.cli.data_root")
    @patch("neo4j_mcp_installer.cli.default_install_dir")
    @patch("neo4j_mcp_installer.cli.os.name", "posix")
    def test_uninstall_clean_cache_with_custom_dir(self, mock_default_dir, mock_data_root, tmp_path, capsys):
        """Test uninstalling with both --install-dir and --clean-cache."""
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        mock_default_dir.return_value = tmp_path
        
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "test.txt").touch()
        mock_data_root.return_value = cache_dir
        
        binary_path = custom_dir / "neo4j-mcp"
        binary_path.touch()
        
        with patch.object(
            sys, "argv", ["neo4j-mcp-installer", "uninstall", "--install-dir", str(custom_dir), "--clean-cache"]
        ):
            main()
        
        captured = capsys.readouterr()
        assert not binary_path.exists()
        assert not cache_dir.exists()
        assert "Removed:" in captured.out
        assert "Removed cache:" in captured.out


class TestMainErrors:
    """Tests for error handling."""

    def test_no_command_fails(self):
        """Test that running without a command fails."""
        with patch.object(sys, "argv", ["neo4j-mcp-installer"]):
            with pytest.raises(SystemExit):
                main()

    def test_invalid_command_fails(self):
        """Test that running with invalid command fails."""
        with patch.object(sys, "argv", ["neo4j-mcp-installer", "invalid"]):
            with pytest.raises(SystemExit):
                main()
