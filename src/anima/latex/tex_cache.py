from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from anima.diagnostics import logger

TEX_CACHE_FORMAT_VERSION = 1
_CACHE_PIPELINE = (
    ("lualatex", "-interaction=nonstopmode", "-output-format=dvi"),
    ("dvisvgm", "--no-fonts", "--exact-bbox", "--precision=6"),
    ("dvisvgm", "--exact-bbox", "--precision=6"),
)
_MAX_ENTRY_BYTES = 16 * 1024 * 1024
_MAX_CACHE_BYTES = 256 * 1024 * 1024
_MAX_CACHE_ENTRIES = 512
_ENTRY_NAME = re.compile(r"[0-9a-f]{64}\.json\Z")
_VERSION_DIRECTORY = re.compile(r"v[0-9]+\Z")
_TEMP_ENTRY = re.compile(r"\.[0-9a-f]{64}\..+\.tmp\Z")
_STALE_TEMP_SECONDS = 24 * 60 * 60
_CACHE_LOCK = threading.RLock()


@dataclass(frozen=True)
class CachedTexOutputs:
    """A complete cached SVG pair and the successful TeX tool output.

    Attributes:
        outline_svg: The SVG containing glyph outlines.
        text_svg: The SVG containing glyph positions and metadata.
        logs: Successful TeX tool commands and their output, in execution order.
    """

    outline_svg: bytes
    text_svg: bytes
    logs: tuple[tuple[str, str], ...]


def tex_cache_enabled() -> bool:
    """Return whether persistent TeX output caching is enabled.

    Set ``ANIMA_DISABLE_TEX_CACHE`` to a true value to disable caching.

    Raises:
        ValueError: If ``ANIMA_DISABLE_TEX_CACHE`` is not a recognized boolean value.
    """
    value = os.environ.get("ANIMA_DISABLE_TEX_CACHE", "").strip().lower()
    if value in {"", "0", "false", "no", "off"}:
        return True
    if value in {"1", "true", "yes", "on"}:
        return False
    raise ValueError("ANIMA_DISABLE_TEX_CACHE must be a boolean value.")


def tex_cache_root() -> Path:
    """Return the configured root directory for the persistent TeX output cache.

    ``ANIMA_TEX_CACHE_DIR`` overrides the platform-specific cache location.

    Raises:
        ValueError: If ``ANIMA_TEX_CACHE_DIR`` is set to an empty value.
        NotImplementedError: If the platform is unsupported and no cache directory is configured.
    """
    configured = os.environ.get("ANIMA_TEX_CACHE_DIR")
    if configured is not None:
        if not configured.strip():
            raise ValueError("ANIMA_TEX_CACHE_DIR must not be empty.")
        return Path(configured).expanduser()

    if sys.platform not in {"win32", "darwin"}:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache").expanduser()
    else:
        raise NotImplementedError(f"Unsupported platform: {sys.platform}")
    return base / "anima" / "tex"


def tex_cache_key(tex_source: str) -> str:
    """Create a versioned key from the generated TeX document and pipeline options.

    Args:
        tex_source: The full generated TeX document.

    Returns:
        The lowercase hexadecimal SHA-256 cache key.
    """
    identity = {
        "format": TEX_CACHE_FORMAT_VERSION,
        "pipeline": _CACHE_PIPELINE,
        "tex": tex_source,
    }
    serialized = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def read_tex_cache(cache_root: Path, key: str) -> CachedTexOutputs | None:
    """Read and validate a cached pair of SVG outputs.

    Missing entries are cache misses. Corrupt entries are reported and treated as misses.

    Args:
        cache_root: The root directory containing versioned cache entries.
        key: The cache key returned by :func:`tex_cache_key`.

    Returns:
        The validated outputs, or ``None`` if the entry is missing, unreadable, or invalid.
    """
    path = _entry_path(cache_root, key)
    try:
        if path.stat().st_size > _MAX_ENTRY_BYTES:
            logger.warning("Ignoring oversized TeX cache entry: {}", path)
            return None
        data = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as error:
        logger.warning("Could not read TeX cache entry {}; recompiling: {}", path, error)
        return None

    if len(data) > _MAX_ENTRY_BYTES:
        logger.warning("Ignoring oversized TeX cache entry: {}", path)
        return None

    try:
        entry = json.loads(data)
        if entry["format"] != TEX_CACHE_FORMAT_VERSION or entry["key"] != key:
            raise ValueError("cache format or key does not match")
        outline = base64.b64decode(entry["outline_svg"], validate=True)
        text = base64.b64decode(entry["text_svg"], validate=True)
        if hashlib.sha256(outline).hexdigest() != entry["outline_sha256"]:
            raise ValueError("outline SVG checksum does not match")
        if hashlib.sha256(text).hexdigest() != entry["text_sha256"]:
            raise ValueError("text SVG checksum does not match")
        if not outline or not text:
            raise ValueError("an SVG output is empty")
        raw_logs = entry["logs"]
        if not isinstance(raw_logs, list) or any(
            not isinstance(item, list)
            or len(item) != 2
            or item[0] not in {"lualatex", "dvisvgm"}
            or not isinstance(item[1], str)
            for item in raw_logs
        ):
            raise ValueError("cached TeX tool logs are invalid")
        logs = tuple((item[0], item[1]) for item in raw_logs)
    except (KeyError, TypeError, UnicodeDecodeError, ValueError) as error:
        logger.warning("Ignoring corrupt TeX cache entry {}; recompiling: {}", path, error)
        return None

    return CachedTexOutputs(outline, text, logs)


def write_tex_cache(
    cache_root: Path,
    key: str,
    outline: bytes,
    text: bytes,
    logs: tuple[tuple[str, str], ...] = (),
) -> None:
    """Atomically store a pair of SVG outputs and prune old entries.

    Entries larger than the configured limit are not cached.

    Args:
        cache_root: The root directory in which to store versioned cache entries.
        key: The cache key returned by :func:`tex_cache_key`.
        outline: The SVG containing glyph outlines.
        text: The SVG containing glyph positions and metadata.
        logs: Successful TeX tool commands and their output, in execution order.
    """
    estimated_size = (
        4 * ((len(outline) + 2) // 3)
        + 4 * ((len(text) + 2) // 3)
        + sum(6 * (len(command.encode("utf-8")) + len(output.encode("utf-8"))) for command, output in logs)
        + 1024
    )
    if estimated_size > _MAX_ENTRY_BYTES:
        logger.warning(
            "Not caching TeX output because the paired SVG entry exceeds the {} byte limit.",
            _MAX_ENTRY_BYTES,
        )
        return

    entry = {
        "format": TEX_CACHE_FORMAT_VERSION,
        "key": key,
        "outline_sha256": hashlib.sha256(outline).hexdigest(),
        "text_sha256": hashlib.sha256(text).hexdigest(),
        "outline_svg": base64.b64encode(outline).decode("ascii"),
        "text_svg": base64.b64encode(text).decode("ascii"),
        "logs": logs,
    }
    data = json.dumps(entry, separators=(",", ":")).encode("utf-8")
    if len(data) > _MAX_ENTRY_BYTES:
        logger.warning(
            "Not caching TeX output because the paired SVG entry exceeds the {} byte limit.",
            _MAX_ENTRY_BYTES,
        )
        return

    directory = cache_root / f"v{TEX_CACHE_FORMAT_VERSION}"
    path = _entry_path(cache_root, key)
    with _CACHE_LOCK:
        directory.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{key}.",
                suffix=".tmp",
                dir=directory,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(data)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        _prune_tex_cache(cache_root)


def clear_tex_cache(cache_root: Path | str | None = None) -> None:
    """Remove Anima TeX cache entries from the selected cache root.

    Args:
        cache_root: Optional cache root. Defaults to the configured cache location.
    """
    root = Path(cache_root).expanduser() if cache_root is not None else tex_cache_root()
    with _CACHE_LOCK:
        if not root.is_dir():
            return
        for directory in root.iterdir():
            if directory.is_symlink() or not directory.is_dir() or not _VERSION_DIRECTORY.fullmatch(directory.name):
                continue
            for path in directory.iterdir():
                if _ENTRY_NAME.fullmatch(path.name) or (path.name.startswith(".") and path.suffix == ".tmp"):
                    if path.is_file():
                        path.unlink()


def _entry_path(cache_root: Path, key: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{64}", key):
        raise ValueError("TeX cache keys must be 64-character lowercase SHA-256 digests.")
    return cache_root / f"v{TEX_CACHE_FORMAT_VERSION}" / f"{key}.json"


def _prune_tex_cache(cache_root: Path) -> None:
    entries: list[tuple[int, int, Path]] = []
    total_bytes = 0
    for directory in cache_root.iterdir():
        if directory.is_symlink() or not directory.is_dir() or not _VERSION_DIRECTORY.fullmatch(directory.name):
            continue
        for path in directory.iterdir():
            if not _ENTRY_NAME.fullmatch(path.name):
                if _TEMP_ENTRY.fullmatch(path.name):
                    try:
                        if time.time() - path.stat().st_mtime > _STALE_TEMP_SECONDS:
                            path.unlink()
                    except FileNotFoundError:
                        continue
                    except OSError as error:
                        logger.warning("Could not remove stale TeX cache temporary file {}: {}", path, error)
                continue
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            entries.append((stat.st_mtime_ns, stat.st_size, path))
            total_bytes += stat.st_size

    entries.sort()
    while entries and (total_bytes > _MAX_CACHE_BYTES or len(entries) > _MAX_CACHE_ENTRIES):
        _, size, path = entries.pop(0)
        try:
            path.unlink()
            total_bytes -= size
        except FileNotFoundError:
            total_bytes -= size
        except OSError as error:
            logger.warning("Could not evict TeX cache entry {}: {}", path, error)
