"""Tests for the installer module."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest

from neo4j_mcp_installer.installer import (
    DEFAULT_BASE_URL,
    DEFAULT_REPO,
    Target,
    _download_checksums_text,
    _expected_sha_from_checksums,
    _extract_archive,
    _http_download,
    _http_get_bytes,
    _make_executable,
    _normalize_version_for_checksums,
    _sha256_file,
    archive_path,
    data_root,
    default_install_dir,
    detect_target,
    extracted_path,
    install_binary,
    latest_version,
    version_dir,
    versions_dir,
)


class TestTarget:
    """Tests for the Target dataclass."""

    def test_target_asset_name_unix(self):
        """Test asset name generation for Unix systems."""
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".tar.gz")
        assert target.asset_name == "neo4j-mcp_Linux_x86_64.tar.gz"

    def test_target_asset_name_windows(self):
        """Test asset name generation for Windows."""
        target = Target(os_name="Windows", arch="x86_64", archive_ext=".zip")
        assert target.asset_name == "neo4j-mcp_Windows_x86_64.zip"

    def test_target_extracted_binary_name_unix(self):
        """Test binary name for Unix systems."""
        target = Target(os_name="Linux", arch="arm64", archive_ext=".tar.gz")
        assert target.extracted_binary_name == "neo4j-mcp"

    def test_target_extracted_binary_name_windows(self):
        """Test binary name for Windows."""
        target = Target(os_name="Windows", arch="x86_64", archive_ext=".zip")
        assert target.extracted_binary_name == "neo4j-mcp.exe"


class TestDetectTarget:
    """Tests for the detect_target function."""

    @patch("neo4j_mcp_installer.installer.platform.system")
    @patch("neo4j_mcp_installer.installer.platform.machine")
    def test_detect_target_linux_x86_64(self, mock_machine, mock_system):
        """Test target detection for Linux x86_64."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"
        
        target = detect_target()
        
        assert target.os_name == "Linux"
        assert target.arch == "x86_64"
        assert target.archive_ext == ".tar.gz"

    @patch("neo4j_mcp_installer.installer.platform.system")
    @patch("neo4j_mcp_installer.installer.platform.machine")
    def test_detect_target_darwin_arm64(self, mock_machine, mock_system):
        """Test target detection for macOS ARM64."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"
        
        target = detect_target()
        
        assert target.os_name == "Darwin"
        assert target.arch == "arm64"
        assert target.archive_ext == ".tar.gz"

    @patch("neo4j_mcp_installer.installer.platform.system")
    @patch("neo4j_mcp_installer.installer.platform.machine")
    def test_detect_target_darwin_aarch64(self, mock_machine, mock_system):
        """Test target detection for macOS with aarch64 machine type."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "aarch64"
        
        target = detect_target()
        
        assert target.arch == "arm64"

    @patch("neo4j_mcp_installer.installer.platform.system")
    @patch("neo4j_mcp_installer.installer.platform.machine")
    def test_detect_target_windows_amd64(self, mock_machine, mock_system):
        """Test target detection for Windows AMD64."""
        mock_system.return_value = "Windows"
        mock_machine.return_value = "amd64"
        
        target = detect_target()
        
        assert target.os_name == "Windows"
        assert target.arch == "x86_64"
        assert target.archive_ext == ".zip"

    @patch("neo4j_mcp_installer.installer.platform.system")
    @patch("neo4j_mcp_installer.installer.platform.machine")
    def test_detect_target_linux_i386(self, mock_machine, mock_system):
        """Test target detection for Linux i386."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "i386"
        
        target = detect_target()
        
        assert target.arch == "i386"

    @patch("neo4j_mcp_installer.installer.platform.system")
    @patch("neo4j_mcp_installer.installer.platform.machine")
    def test_detect_target_linux_i686(self, mock_machine, mock_system):
        """Test target detection for Linux i686."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "i686"
        
        target = detect_target()
        
        assert target.arch == "i386"

    @patch("neo4j_mcp_installer.installer.platform.system")
    @patch("neo4j_mcp_installer.installer.platform.machine")
    def test_detect_target_unsupported_os(self, mock_machine, mock_system):
        """Test that unsupported OS raises RuntimeError."""
        mock_system.return_value = "FreeBSD"
        mock_machine.return_value = "x86_64"
        
        with pytest.raises(RuntimeError, match="Unsupported OS"):
            detect_target()

    @patch("neo4j_mcp_installer.installer.platform.system")
    @patch("neo4j_mcp_installer.installer.platform.machine")
    def test_detect_target_unsupported_arch(self, mock_machine, mock_system):
        """Test that unsupported architecture raises RuntimeError."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "sparc64"
        
        with pytest.raises(RuntimeError, match="Unsupported architecture"):
            detect_target()


class TestPathHelpers:
    """Tests for path helper functions."""

    @patch("neo4j_mcp_installer.installer.user_data_dir")
    def test_data_root(self, mock_user_data_dir, tmp_path):
        """Test data_root returns platformdirs path."""
        mock_user_data_dir.return_value = str(tmp_path / "data")
        
        result = data_root()
        
        assert result == tmp_path / "data"
        mock_user_data_dir.assert_called_once_with("neo4j-mcp")

    @patch("neo4j_mcp_installer.installer.data_root")
    def test_versions_dir(self, mock_data_root, tmp_path):
        """Test versions_dir returns data_root/versions."""
        mock_data_root.return_value = tmp_path
        
        result = versions_dir()
        
        assert result == tmp_path / "versions"

    @patch("neo4j_mcp_installer.installer.versions_dir")
    def test_version_dir(self, mock_versions_dir, tmp_path):
        """Test version_dir returns versions_dir/version."""
        mock_versions_dir.return_value = tmp_path
        
        result = version_dir("v1.2.3")
        
        assert result == tmp_path / "v1.2.3"

    @patch("neo4j_mcp_installer.installer.version_dir")
    def test_archive_path(self, mock_version_dir, tmp_path):
        """Test archive_path returns version_dir/asset_name."""
        mock_version_dir.return_value = tmp_path
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".tar.gz")
        
        result = archive_path("v1.2.3", target)
        
        assert result == tmp_path / "neo4j-mcp_Linux_x86_64.tar.gz"

    @patch("neo4j_mcp_installer.installer.version_dir")
    def test_extracted_path(self, mock_version_dir, tmp_path):
        """Test extracted_path returns version_dir/binary_name."""
        mock_version_dir.return_value = tmp_path
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".tar.gz")
        
        result = extracted_path("v1.2.3", target)
        
        assert result == tmp_path / "neo4j-mcp"

    @patch("neo4j_mcp_installer.installer.os.name", "posix")
    def test_default_install_dir_unix(self):
        """Test default install dir on Unix."""
        result = default_install_dir()
        
        assert result == Path.home() / ".local" / "bin"

    @patch("neo4j_mcp_installer.installer.os.name", "nt")
    def test_default_install_dir_windows_no_localappdata(self):
        """Test default install dir on Windows without LOCALAPPDATA."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="LOCALAPPDATA is not set"):
                default_install_dir()


class TestHttpHelpers:
    """Tests for HTTP helper functions."""

    @patch("neo4j_mcp_installer.installer.urllib.request.urlopen")
    def test_http_get_bytes(self, mock_urlopen):
        """Test _http_get_bytes downloads and returns bytes."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"test data"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = mock_response
        
        result = _http_get_bytes("http://example.com/file")
        
        assert result == b"test data"

    @patch("neo4j_mcp_installer.installer.urllib.request.urlopen")
    def test_http_get_bytes_with_headers(self, mock_urlopen):
        """Test _http_get_bytes with custom headers."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"test data"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = mock_response
        
        result = _http_get_bytes("http://example.com/file", headers={"User-Agent": "test"})
        
        assert result == b"test data"

    @patch("neo4j_mcp_installer.installer.urllib.request.urlopen")
    def test_http_download(self, mock_urlopen, tmp_path):
        """Test _http_download downloads file to disk."""
        dest = tmp_path / "subdir" / "file.txt"
        mock_response = MagicMock()
        mock_response.read.side_effect = [b"chunk1", b"chunk2", b""]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = mock_response
        
        _http_download("http://example.com/file", dest)
        
        assert dest.exists()
        assert dest.read_bytes() == b"chunk1chunk2"


class TestCryptoHelpers:
    """Tests for cryptographic helper functions."""

    def test_sha256_file(self, tmp_path):
        """Test _sha256_file calculates correct hash."""
        test_file = tmp_path / "test.txt"
        test_data = b"test data for hashing"
        test_file.write_bytes(test_data)
        
        result = _sha256_file(test_file)
        
        expected = hashlib.sha256(test_data).hexdigest()
        assert result == expected

    def test_sha256_file_large(self, tmp_path):
        """Test _sha256_file handles large files in chunks."""
        test_file = tmp_path / "large.bin"
        # Create a file larger than 1MB to test chunking
        test_data = b"x" * (2 * 1024 * 1024)
        test_file.write_bytes(test_data)
        
        result = _sha256_file(test_file)
        
        expected = hashlib.sha256(test_data).hexdigest()
        assert result == expected


class TestMakeExecutable:
    """Tests for the _make_executable function."""

    @patch("neo4j_mcp_installer.installer.os.name", "posix")
    def test_make_executable_unix(self, tmp_path):
        """Test _make_executable sets executable bits on Unix."""
        test_file = tmp_path / "test.bin"
        test_file.touch()
        
        _make_executable(test_file)
        
        mode = test_file.stat().st_mode
        # Check that owner, group, and other execute bits are set
        import stat
        assert mode & stat.S_IXUSR
        assert mode & stat.S_IXGRP
        assert mode & stat.S_IXOTH

    @patch("neo4j_mcp_installer.installer.os.name", "nt")
    def test_make_executable_windows(self, tmp_path):
        """Test _make_executable does nothing on Windows."""
        test_file = tmp_path / "test.exe"
        test_file.touch()
        original_mode = test_file.stat().st_mode
        
        _make_executable(test_file)
        
        # Mode should be unchanged on Windows
        assert test_file.stat().st_mode == original_mode


class TestLatestVersion:
    """Tests for the latest_version function."""

    @patch("neo4j_mcp_installer.installer._http_get_bytes")
    def test_latest_version_success(self, mock_http_get):
        """Test latest_version parses GitHub API response."""
        mock_http_get.return_value = json.dumps({"tag_name": "v1.2.3"}).encode()
        
        result = latest_version()
        
        assert result == "v1.2.3"
        mock_http_get.assert_called_once()

    @patch("neo4j_mcp_installer.installer._http_get_bytes")
    def test_latest_version_custom_repo(self, mock_http_get):
        """Test latest_version with custom repo."""
        mock_http_get.return_value = json.dumps({"tag_name": "v2.0.0"}).encode()
        
        result = latest_version(repo="custom/repo")
        
        assert result == "v2.0.0"

    @patch("neo4j_mcp_installer.installer._http_get_bytes")
    def test_latest_version_no_tag_name(self, mock_http_get):
        """Test latest_version raises error when tag_name is missing."""
        mock_http_get.return_value = json.dumps({"name": "Release"}).encode()
        
        with pytest.raises(RuntimeError, match="Could not determine latest release"):
            latest_version()


class TestNormalizeVersion:
    """Tests for version normalization."""

    def test_normalize_version_with_v_prefix(self):
        """Test version normalization strips v prefix."""
        assert _normalize_version_for_checksums("v1.2.3") == "1.2.3"

    def test_normalize_version_without_v_prefix(self):
        """Test version normalization leaves version without v."""
        assert _normalize_version_for_checksums("1.2.3") == "1.2.3"


class TestDownloadChecksums:
    """Tests for checksum download."""

    @patch("neo4j_mcp_installer.installer._http_get_bytes")
    def test_download_checksums_success(self, mock_http_get):
        """Test successful checksum download."""
        mock_http_get.return_value = b"checksum data"
        
        result = _download_checksums_text("v1.2.3", "https://example.com")
        
        assert result == "checksum data"

    @patch("neo4j_mcp_installer.installer._http_get_bytes")
    def test_download_checksums_404(self, mock_http_get):
        """Test checksum download returns None on 404."""
        from urllib.error import HTTPError
        mock_http_get.side_effect = HTTPError("url", 404, "Not Found", {}, None)
        
        result = _download_checksums_text("v1.2.3", "https://example.com")
        
        assert result is None

    @patch("neo4j_mcp_installer.installer._http_get_bytes")
    def test_download_checksums_403(self, mock_http_get):
        """Test checksum download returns None on 403."""
        from urllib.error import HTTPError
        mock_http_get.side_effect = HTTPError("url", 403, "Forbidden", {}, None)
        
        result = _download_checksums_text("v1.2.3", "https://example.com")
        
        assert result is None

    @patch("neo4j_mcp_installer.installer._http_get_bytes")
    def test_download_checksums_other_http_error(self, mock_http_get):
        """Test checksum download raises on other HTTP errors."""
        from urllib.error import HTTPError
        mock_http_get.side_effect = HTTPError("url", 500, "Server Error", {}, None)
        
        with pytest.raises(HTTPError):
            _download_checksums_text("v1.2.3", "https://example.com")

    @patch("neo4j_mcp_installer.installer._http_get_bytes")
    def test_download_checksums_url_error(self, mock_http_get):
        """Test checksum download returns None on URLError."""
        from urllib.error import URLError
        mock_http_get.side_effect = URLError("Connection failed")
        
        result = _download_checksums_text("v1.2.3", "https://example.com")
        
        assert result is None


class TestExpectedShaFromChecksums:
    """Tests for parsing checksums."""

    def test_expected_sha_block_format(self):
        """Test parsing block format checksums."""
        checksums = """
        neo4j-mcp_Linux_x86_64.tar.gz
        sha256:abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab
        """
        
        result = _expected_sha_from_checksums(checksums, "neo4j-mcp_Linux_x86_64.tar.gz")
        
        assert result == "abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"

    def test_expected_sha_traditional_format(self):
        """Test parsing traditional 'hash filename' format."""
        checksums = "abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab neo4j-mcp_Linux_x86_64.tar.gz"
        
        result = _expected_sha_from_checksums(checksums, "neo4j-mcp_Linux_x86_64.tar.gz")
        
        assert result == "abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"

    def test_expected_sha_not_found(self):
        """Test parsing returns None when file not found."""
        checksums = "other_file.tar.gz\nsha256:abcd1234"
        
        result = _expected_sha_from_checksums(checksums, "neo4j-mcp_Linux_x86_64.tar.gz")
        
        assert result is None


class TestExtractArchive:
    """Tests for archive extraction."""

    def test_extract_archive_tar_gz(self, tmp_path):
        """Test extracting from tar.gz archive."""
        # Create a test tar.gz archive
        archive_path = tmp_path / "test.tar.gz"
        binary_content = b"fake binary content"
        
        with tarfile.open(archive_path, "w:gz") as tar:
            import io
            import tarfile as tf
            
            info = tf.TarInfo(name="neo4j-mcp")
            info.size = len(binary_content)
            tar.addfile(info, io.BytesIO(binary_content))
        
        out_bin = tmp_path / "output" / "neo4j-mcp"
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".tar.gz")
        
        _extract_archive(archive_path, out_bin, target)
        
        assert out_bin.exists()
        assert out_bin.read_bytes() == binary_content

    def test_extract_archive_zip(self, tmp_path):
        """Test extracting from zip archive."""
        # Create a test zip archive
        archive_path = tmp_path / "test.zip"
        binary_content = b"fake binary content"
        
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("neo4j-mcp.exe", binary_content)
        
        out_bin = tmp_path / "output" / "neo4j-mcp.exe"
        target = Target(os_name="Windows", arch="x86_64", archive_ext=".zip")
        
        _extract_archive(archive_path, out_bin, target)
        
        assert out_bin.exists()
        assert out_bin.read_bytes() == binary_content

    def test_extract_archive_tar_gz_binary_not_found(self, tmp_path):
        """Test extraction fails when binary not found in tar.gz."""
        archive_path = tmp_path / "test.tar.gz"
        
        with tarfile.open(archive_path, "w:gz") as tar:
            import io
            import tarfile as tf
            
            content = b"test content"
            info = tf.TarInfo(name="wrong_file")
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        
        out_bin = tmp_path / "output" / "neo4j-mcp"
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".tar.gz")
        
        with pytest.raises(RuntimeError, match="Could not find neo4j-mcp binary"):
            _extract_archive(archive_path, out_bin, target)

    def test_extract_archive_zip_binary_not_found(self, tmp_path):
        """Test extraction fails when binary not found in zip."""
        archive_path = tmp_path / "test.zip"
        
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("wrong_file.exe", b"test")
        
        out_bin = tmp_path / "output" / "neo4j-mcp.exe"
        target = Target(os_name="Windows", arch="x86_64", archive_ext=".zip")
        
        with pytest.raises(RuntimeError, match="Could not find neo4j-mcp binary"):
            _extract_archive(archive_path, out_bin, target)

    def test_extract_archive_unsupported_type(self, tmp_path):
        """Test extraction fails for unsupported archive type."""
        archive_path = tmp_path / "test.rar"
        archive_path.touch()
        
        out_bin = tmp_path / "output" / "neo4j-mcp"
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".rar")
        
        with pytest.raises(RuntimeError, match="Unsupported archive type"):
            _extract_archive(archive_path, out_bin, target)


class TestInstallBinary:
    """Tests for the install_binary function."""

    @patch("neo4j_mcp_installer.installer.detect_target")
    @patch("neo4j_mcp_installer.installer.latest_version")
    @patch("neo4j_mcp_installer.installer.default_install_dir")
    @patch("neo4j_mcp_installer.installer.extracted_path")
    @patch("neo4j_mcp_installer.installer.archive_path")
    @patch("neo4j_mcp_installer.installer._http_download")
    @patch("neo4j_mcp_installer.installer._download_checksums_text")
    @patch("neo4j_mcp_installer.installer._extract_archive")
    @patch("neo4j_mcp_installer.installer._make_executable")
    def test_install_binary_basic(
        self, mock_make_exec, mock_extract, mock_checksums,
        mock_download, mock_archive_path, mock_extracted_path, mock_default_dir,
        mock_latest, mock_detect, tmp_path
    ):
        """Test basic install_binary flow."""
        # Setup mocks
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".tar.gz")
        mock_detect.return_value = target
        mock_latest.return_value = "v1.0.0"
        
        install_dir = tmp_path / "install"
        install_dir.mkdir(parents=True, exist_ok=True)
        mock_default_dir.return_value = install_dir
        
        # Setup archive path
        archive = tmp_path / "archive" / "test.tar.gz"
        archive.parent.mkdir(parents=True, exist_ok=True)
        mock_archive_path.return_value = archive
        
        extracted = tmp_path / "extracted" / "neo4j-mcp"
        extracted.parent.mkdir(parents=True)
        # Don't create extracted yet - let the test flow create it
        mock_extracted_path.return_value = extracted
        
        mock_checksums.return_value = None  # No checksums available
        
        # Make download create the temp archive file
        def create_archive(url, dest, **kwargs):
            dest.write_bytes(b"fake archive")
        mock_download.side_effect = create_archive
        
        # Make extract create the extracted file
        def create_extracted(*args, **kwargs):
            extracted.write_bytes(b"fake binary")
        mock_extract.side_effect = create_extracted
        
        # Run install
        final_path, version, extracted_bin = install_binary()
        
        # Verify
        assert version == "v1.0.0"
        assert extracted_bin == extracted
        assert final_path.exists()
        mock_download.assert_called_once()
        mock_extract.assert_called_once()

    @patch("neo4j_mcp_installer.installer.detect_target")
    @patch("neo4j_mcp_installer.installer.default_install_dir")
    @patch("neo4j_mcp_installer.installer.extracted_path")
    @patch("neo4j_mcp_installer.installer._http_download")
    @patch("neo4j_mcp_installer.installer._download_checksums_text")
    @patch("neo4j_mcp_installer.installer._extract_archive")
    @patch("neo4j_mcp_installer.installer._make_executable")
    def test_install_binary_with_version(
        self, mock_make_exec, mock_extract, mock_checksums,
        mock_download, mock_extracted_path, mock_default_dir,
        mock_detect, tmp_path
    ):
        """Test install_binary with specific version."""
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".tar.gz")
        mock_detect.return_value = target
        
        install_dir = tmp_path / "install"
        install_dir.mkdir(parents=True, exist_ok=True)
        mock_default_dir.return_value = install_dir
        
        extracted = tmp_path / "extracted" / "neo4j-mcp"
        extracted.parent.mkdir(parents=True)
        extracted.write_bytes(b"fake binary")
        mock_extracted_path.return_value = extracted
        mock_checksums.return_value = None
        
        final_path, version, extracted_bin = install_binary(version="v2.5.0")
        
        assert version == "v2.5.0"
        assert final_path.exists()

    @patch("neo4j_mcp_installer.installer.detect_target")
    @patch("neo4j_mcp_installer.installer.latest_version")
    @patch("neo4j_mcp_installer.installer.default_install_dir")
    @patch("neo4j_mcp_installer.installer.extracted_path")
    def test_install_binary_uses_env_version(
        self, mock_extracted_path, mock_default_dir, mock_latest, mock_detect, tmp_path
    ):
        """Test install_binary uses NEO4J_MCP_VERSION environment variable."""
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".tar.gz")
        mock_detect.return_value = target
        
        install_dir = tmp_path / "install"
        install_dir.mkdir(parents=True, exist_ok=True)
        mock_default_dir.return_value = install_dir
        
        extracted = tmp_path / "extracted" / "neo4j-mcp"
        extracted.parent.mkdir(parents=True)
        extracted.write_bytes(b"fake binary")
        mock_extracted_path.return_value = extracted
        
        with patch.dict(os.environ, {"NEO4J_MCP_VERSION": "v3.0.0"}):
            with patch("neo4j_mcp_installer.installer._http_download"):
                with patch("neo4j_mcp_installer.installer._extract_archive"):
                    with patch("neo4j_mcp_installer.installer._make_executable"):
                        with patch("neo4j_mcp_installer.installer._download_checksums_text", return_value=None):
                            final_path, version, extracted_bin = install_binary()
        
        assert version == "v3.0.0"
        # latest_version should not be called when env var is set
        mock_latest.assert_not_called()

    @patch("neo4j_mcp_installer.installer.detect_target")
    @patch("neo4j_mcp_installer.installer.latest_version")
    @patch("neo4j_mcp_installer.installer.default_install_dir")
    @patch("neo4j_mcp_installer.installer.extracted_path")
    @patch("neo4j_mcp_installer.installer.archive_path")
    @patch("neo4j_mcp_installer.installer._http_download")
    @patch("neo4j_mcp_installer.installer._download_checksums_text")
    @patch("neo4j_mcp_installer.installer._expected_sha_from_checksums")
    @patch("neo4j_mcp_installer.installer._sha256_file")
    @patch("neo4j_mcp_installer.installer._extract_archive")
    @patch("neo4j_mcp_installer.installer._make_executable")
    def test_install_binary_with_verification(
        self, mock_make_exec, mock_extract, mock_sha, mock_expected_sha,
        mock_checksums, mock_download, mock_archive_path, mock_extracted_path, mock_default_dir,
        mock_latest, mock_detect, tmp_path
    ):
        """Test install_binary with checksum verification."""
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".tar.gz")
        mock_detect.return_value = target
        mock_latest.return_value = "v1.0.0"
        
        install_dir = tmp_path / "install"
        install_dir.mkdir(parents=True, exist_ok=True)
        mock_default_dir.return_value = install_dir
        
        # Setup archive path
        archive = tmp_path / "archive" / "test.tar.gz"
        archive.parent.mkdir(parents=True, exist_ok=True)
        mock_archive_path.return_value = archive
        
        extracted = tmp_path / "extracted" / "neo4j-mcp"
        extracted.parent.mkdir(parents=True)
        # Don't create extracted yet - let the test flow create it
        mock_extracted_path.return_value = extracted
        
        # Make download create the temp archive file
        def create_archive(url, dest, **kwargs):
            dest.write_bytes(b"fake archive")
        mock_download.side_effect = create_archive
        
        # Make extract create the file
        def create_extracted(*args, **kwargs):
            extracted.write_bytes(b"fake binary")
        mock_extract.side_effect = create_extracted
        
        mock_checksums.return_value = "checksum data"
        expected_hash = "abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"
        mock_expected_sha.return_value = expected_hash
        mock_sha.return_value = expected_hash
        
        final_path, version, extracted_bin = install_binary(verify=True)
        
        mock_sha.assert_called_once()
        mock_expected_sha.assert_called_once()
        assert final_path.exists()

    @patch("neo4j_mcp_installer.installer.detect_target")
    @patch("neo4j_mcp_installer.installer.latest_version")
    @patch("neo4j_mcp_installer.installer.default_install_dir")
    @patch("neo4j_mcp_installer.installer.extracted_path")
    @patch("neo4j_mcp_installer.installer._http_download")
    @patch("neo4j_mcp_installer.installer._download_checksums_text")
    @patch("neo4j_mcp_installer.installer._expected_sha_from_checksums")
    @patch("neo4j_mcp_installer.installer._sha256_file")
    def test_install_binary_verification_fails(
        self, mock_sha, mock_expected_sha, mock_checksums, mock_download,
        mock_extracted_path, mock_default_dir, mock_latest, mock_detect, tmp_path
    ):
        """Test install_binary fails when checksum doesn't match."""
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".tar.gz")
        mock_detect.return_value = target
        mock_latest.return_value = "v1.0.0"
        mock_default_dir.return_value = tmp_path / "install"
        
        extracted = tmp_path / "extracted" / "neo4j-mcp"
        mock_extracted_path.return_value = extracted
        
        mock_checksums.return_value = "checksum data"
        mock_expected_sha.return_value = "expected_hash_12345"
        mock_sha.return_value = "actual_hash_67890"
        
        with pytest.raises(RuntimeError, match="Checksum verification failed"):
            install_binary(verify=True)

    @patch("neo4j_mcp_installer.installer.detect_target")
    @patch("neo4j_mcp_installer.installer.latest_version")
    @patch("neo4j_mcp_installer.installer.default_install_dir")
    @patch("neo4j_mcp_installer.installer.extracted_path")
    @patch("neo4j_mcp_installer.installer._http_download")
    @patch("neo4j_mcp_installer.installer._download_checksums_text")
    @patch("neo4j_mcp_installer.installer._extract_archive")
    @patch("neo4j_mcp_installer.installer._make_executable")
    def test_install_binary_skip_verification_with_env(
        self, mock_make_exec, mock_extract, mock_checksums,
        mock_download, mock_extracted_path, mock_default_dir,
        mock_latest, mock_detect, tmp_path
    ):
        """Test install_binary skips verification with NEO4J_MCP_SKIP_VERIFY."""
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".tar.gz")
        mock_detect.return_value = target
        mock_latest.return_value = "v1.0.0"
        
        install_dir = tmp_path / "install"
        install_dir.mkdir(parents=True, exist_ok=True)
        mock_default_dir.return_value = install_dir
        
        extracted = tmp_path / "extracted" / "neo4j-mcp"
        extracted.parent.mkdir(parents=True)
        extracted.write_bytes(b"fake binary")
        mock_extracted_path.return_value = extracted
        
        mock_checksums.return_value = "checksum data"
        
        with patch.dict(os.environ, {"NEO4J_MCP_SKIP_VERIFY": "1"}):
            final_path, version, extracted_bin = install_binary(verify=True)
        
        # Checksums should not be downloaded when skip verify is set
        mock_checksums.assert_not_called()
        assert final_path.exists()

    @patch("neo4j_mcp_installer.installer.detect_target")
    @patch("neo4j_mcp_installer.installer.latest_version")
    @patch("neo4j_mcp_installer.installer.default_install_dir")
    @patch("neo4j_mcp_installer.installer.extracted_path")
    @patch("neo4j_mcp_installer.installer._http_download")
    @patch("neo4j_mcp_installer.installer._extract_archive")
    @patch("neo4j_mcp_installer.installer._make_executable")
    def test_install_binary_reuses_extracted(
        self, mock_make_exec, mock_extract, mock_download,
        mock_extracted_path, mock_default_dir, mock_latest, mock_detect, tmp_path
    ):
        """Test install_binary reuses already extracted binary."""
        target = Target(os_name="Linux", arch="x86_64", archive_ext=".tar.gz")
        mock_detect.return_value = target
        mock_latest.return_value = "v1.0.0"
        
        install_dir = tmp_path / "install"
        install_dir.mkdir(parents=True, exist_ok=True)
        mock_default_dir.return_value = install_dir
        
        # Simulate already extracted binary
        extracted = tmp_path / "extracted" / "neo4j-mcp"
        extracted.parent.mkdir(parents=True)
        extracted.write_bytes(b"existing binary")
        mock_extracted_path.return_value = extracted
        
        final_path, version, extracted_bin = install_binary(force_download=False)
        
        # Should not download or extract again
        mock_download.assert_not_called()
        mock_extract.assert_not_called()
        # But final path should exist
        assert final_path.exists()
