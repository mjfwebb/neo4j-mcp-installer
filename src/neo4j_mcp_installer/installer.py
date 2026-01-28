from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import tarfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from platformdirs import user_data_dir

DEFAULT_REPO = os.environ.get("NEO4J_MCP_REPO", "neo4j/mcp")
DEFAULT_BASE_URL = os.environ.get(
    "NEO4J_MCP_BASE_URL",
    f"https://github.com/{DEFAULT_REPO}/releases/download",
)
GITHUB_API_LATEST = lambda repo: f"https://api.github.com/repos/{repo}/releases/latest"


@dataclass(frozen=True)
class Target:
    os_name: str        # Darwin | Linux | Windows
    arch: str           # arm64 | x86_64 | i386
    archive_ext: str    # .tar.gz | .zip

    @property
    def asset_name(self) -> str:
        return f"neo4j-mcp_{self.os_name}_{self.arch}{self.archive_ext}"

    @property
    def extracted_binary_name(self) -> str:
        return "neo4j-mcp.exe" if self.os_name == "Windows" else "neo4j-mcp"


def detect_target() -> Target:
    sysname = platform.system()  # "Darwin", "Linux", "Windows"
    machine = platform.machine().lower()

    if sysname not in ("Darwin", "Linux", "Windows"):
        raise RuntimeError(f"Unsupported OS: {sysname}")

    archive_ext = ".zip" if sysname == "Windows" else ".tar.gz"

    if machine in ("arm64", "aarch64"):
        arch = "arm64"
    elif machine in ("x86_64", "amd64"):
        arch = "x86_64"
    elif machine in ("i386", "i686", "x86"):
        arch = "i386"
    else:
        raise RuntimeError(f"Unsupported architecture: {platform.machine()}")

    return Target(os_name=sysname, arch=arch, archive_ext=archive_ext)


def data_root() -> Path:
    # per-user *data* dir (not cache) because we want the installed binary to persist
    # Linux: ~/.local/share/neo4j-mcp
    # macOS: ~/Library/Application Support/neo4j-mcp
    # Windows: %APPDATA%/neo4j-mcp (platformdirs chooses appropriate roaming/local)
    return Path(user_data_dir("neo4j-mcp"))


def versions_dir() -> Path:
    return data_root() / "versions"


def version_dir(version: str) -> Path:
    return versions_dir() / version


def archive_path(version: str, target: Target) -> Path:
    return version_dir(version) / target.asset_name


def extracted_path(version: str, target: Target) -> Path:
    return version_dir(version) / target.extracted_binary_name


def default_install_dir() -> Path:
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            raise RuntimeError("LOCALAPPDATA is not set; cannot determine install dir on Windows.")
        return Path(local) / "neo4j-mcp" / "bin"
    return Path.home() / ".local" / "bin"


def _http_get_bytes(url: str, headers: Optional[dict[str, str]] = None) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _http_download(url: str, dest: Path, headers: Optional[dict[str, str]] = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_executable(path: Path) -> None:
    if os.name == "nt":
        return
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def latest_version(repo: str = DEFAULT_REPO) -> str:
    data = _http_get_bytes(GITHUB_API_LATEST(repo), headers={"User-Agent": "neo4j-mcp-installer"})
    obj = json.loads(data.decode("utf-8"))
    tag = obj.get("tag_name")
    if not tag:
        raise RuntimeError("Could not determine latest release tag_name from GitHub API.")
    return str(tag)


def _normalize_version_for_checksums(version: str) -> str:
    # checksum asset: neo4j-mcp_1.2.0_checksums.txt (no leading v)
    return version[1:] if version.startswith("v") else version


def _download_checksums_text(version: str, base_url: str) -> Optional[str]:
    ver = _normalize_version_for_checksums(version)
    url = f"{base_url}/{version}/neo4j-mcp_{ver}_checksums.txt"
    try:
        b = _http_get_bytes(url, headers={"User-Agent": "neo4j-mcp-installer"})
        return b.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code in (404, 403):
            return None
        raise
    except urllib.error.URLError:
        return None


def _expected_sha_from_checksums(checksums_text: str, filename: str) -> Optional[str]:
    """
    Parses the block format you showed:

      neo4j-mcp_Darwin_arm64.tar.gz
      sha256:<hash>
    """
    lines = [ln.strip() for ln in checksums_text.splitlines() if ln.strip()]
    for i in range(len(lines) - 1):
        if lines[i] == filename and lines[i + 1].startswith("sha256:"):
            return lines[i + 1].split("sha256:", 1)[1].strip().lower()

    # tolerate "<sha> <filename>" if it ever changes
    for ln in lines:
        parts = ln.split()
        if len(parts) >= 2 and parts[-1] == filename and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            return parts[0].lower()

    return None


def _extract_archive(archive: Path, out_bin: Path, target: Target) -> None:
    out_bin.parent.mkdir(parents=True, exist_ok=True)
    wanted = target.extracted_binary_name

    if target.archive_ext == ".tar.gz":
        with tarfile.open(archive, "r:gz") as tf:
            members = [m for m in tf.getmembers() if m.isfile()]
            candidate = next((m for m in members if Path(m.name).name == wanted), None)
            if candidate is None:
                candidate = next((m for m in members if Path(m.name).name in ("neo4j-mcp", "neo4j-mcp.exe")), None)
            if candidate is None:
                raise RuntimeError(f"Could not find neo4j-mcp binary inside {archive.name}")

            fobj = tf.extractfile(candidate)
            if fobj is None:
                raise RuntimeError(f"Failed to extract {candidate.name} from {archive.name}")

            tmp = out_bin.with_suffix(out_bin.suffix + ".tmp")
            with open(tmp, "wb") as f:
                f.write(fobj.read())
            if out_bin.exists():
                out_bin.unlink()
            tmp.replace(out_bin)

    elif target.archive_ext == ".zip":
        with zipfile.ZipFile(archive, "r") as zf:
            names = zf.namelist()
            match = next((n for n in names if Path(n).name == wanted), None)
            if match is None:
                match = next((n for n in names if Path(n).name in ("neo4j-mcp.exe", "neo4j-mcp")), None)
            if match is None:
                raise RuntimeError(f"Could not find neo4j-mcp binary inside {archive.name}")

            tmp = out_bin.with_suffix(out_bin.suffix + ".tmp")
            with open(tmp, "wb") as f:
                f.write(zf.read(match))
            if out_bin.exists():
                out_bin.unlink()
            tmp.replace(out_bin)

    else:
        raise RuntimeError(f"Unsupported archive type: {target.archive_ext}")

    _make_executable(out_bin)


def install_binary(
    *,
    version: Optional[str] = None,
    repo: str = DEFAULT_REPO,
    base_url: str = DEFAULT_BASE_URL,
    verify: bool = True,
    force_download: bool = False,
    install_dir: Optional[Path] = None,
) -> tuple[Path, str, Path]:
    """
    Downloads (if needed), verifies, extracts, and installs the neo4j-mcp binary.

    Returns:
      (installed_binary_path, resolved_version, extracted_versioned_binary_path)
    """
    target = detect_target()

    env_version = os.environ.get("NEO4J_MCP_VERSION")
    if env_version:
        version = env_version
    if not version:
        version = latest_version(repo=repo)

    install_dir = install_dir or default_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)

    # versioned extracted binary location
    extracted = extracted_path(version, target)

    # If we already extracted it and don't force re-download, we can reuse
    if not extracted.exists() or force_download:
        asset = target.asset_name
        url = f"{base_url}/{version}/{asset}"

        archive = archive_path(version, target)
        tmp_archive = archive.with_suffix(archive.suffix + ".tmp")
        if tmp_archive.exists():
            tmp_archive.unlink(missing_ok=True)

        _http_download(url, tmp_archive, headers={"User-Agent": "neo4j-mcp-installer"})

        if verify and not os.environ.get("NEO4J_MCP_SKIP_VERIFY"):
            checksums = _download_checksums_text(version=version, base_url=base_url)
            if checksums:
                expected = _expected_sha_from_checksums(checksums, asset)
                if expected:
                    actual = _sha256_file(tmp_archive)
                    if actual.lower() != expected.lower():
                        tmp_archive.unlink(missing_ok=True)
                        raise RuntimeError(
                            "Checksum verification failed.\n"
                            f"Expected: {expected}\n"
                            f"Actual:   {actual}\n"
                            f"Asset:    {asset}\n"
                            f"URL:      {url}"
                        )

        archive.parent.mkdir(parents=True, exist_ok=True)
        if archive.exists():
            archive.unlink()
        tmp_archive.replace(archive)

        _extract_archive(archive=archive, out_bin=extracted, target=target)

    # Install final binary into install_dir (copy, atomic replace)
    final_name = target.extracted_binary_name
    final_path = install_dir / final_name
    tmp_final = install_dir / (final_name + ".tmp")

    shutil.copy2(extracted, tmp_final)
    _make_executable(tmp_final)

    if final_path.exists():
        final_path.unlink()
    tmp_final.replace(final_path)

    return final_path, version, extracted
