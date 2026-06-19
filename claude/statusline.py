#!/usr/bin/env python3
"""
Claude Code Statusline Hook
Displays status line and sends context usage to VibeMon
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================================
# Configuration Loading
# ============================================================================


def load_config() -> None:
    """Load configuration from config.json and set as environment variables."""
    config_file = Path.home() / ".vibemon" / "config.json"
    if not config_file.exists():
        return

    try:
        with open(config_file) as f:
            config = json.load(f)
    except (json.JSONDecodeError, IOError):
        return

    # Map config keys to environment variables
    key_mapping = {
        "debug": ("DEBUG", lambda v: "1" if v else "0"),
        "cache_path": ("VIBEMON_CACHE_PATH", str),
        "auto_launch": ("VIBEMON_AUTO_LAUNCH", lambda v: "1" if v else "0"),
        "http_urls": (
            "VIBEMON_HTTP_URLS",
            lambda v: ",".join(v) if isinstance(v, list) else str(v),
        ),
        "serial_port": ("VIBEMON_SERIAL_PORT", str),
        "vibemon_url": ("VIBEMON_URL", str),
        "vibemon_token": ("VIBEMON_TOKEN", str),
        "token_reset_hours": ("VIBEMON_TOKEN_RESET_HOURS", str),
        "usage_enabled": ("VIBEMON_USAGE_ENABLED", lambda v: "1" if v else "0"),
        "usage_refresh_seconds": ("VIBEMON_USAGE_REFRESH", str),
        "show_project": ("VIBEMON_SHOW_PROJECT", lambda v: "1" if v else "0"),
        "show_git": ("VIBEMON_SHOW_GIT", lambda v: "1" if v else "0"),
        "show_model": ("VIBEMON_SHOW_MODEL", lambda v: "1" if v else "0"),
        "show_tokens": ("VIBEMON_SHOW_TOKENS", lambda v: "1" if v else "0"),
        "show_cost": ("VIBEMON_SHOW_COST", lambda v: "1" if v else "0"),
        "show_duration": ("VIBEMON_SHOW_DURATION", lambda v: "1" if v else "0"),
        "show_lines": ("VIBEMON_SHOW_LINES", lambda v: "1" if v else "0"),
        "show_memory": ("VIBEMON_SHOW_MEMORY", lambda v: "1" if v else "0"),
        "show_usage": ("VIBEMON_SHOW_USAGE", lambda v: "1" if v else "0"),
        "show_usage_reset": ("VIBEMON_SHOW_USAGE_RESET", lambda v: "1" if v else "0"),
        "show_version": ("VIBEMON_SHOW_VERSION", lambda v: "1" if v else "0"),
        "show_statusline": ("VIBEMON_SHOW_STATUSLINE", lambda v: "1" if v else "0"),
    }

    for config_key, (env_key, converter) in key_mapping.items():
        if config_key in config and config[config_key] is not None:
            value = converter(config[config_key])
            if value:
                os.environ.setdefault(env_key, value)


load_config()

VIBE_MONITOR_MAX_PROJECTS = 10

# Token reset window: 5h for Pro/Max, 0 to disable (Enterprise)
TOKEN_RESET_HOURS = int(os.environ.get("VIBEMON_TOKEN_RESET_HOURS", "5") or "5")
TOKEN_RESET_MS = TOKEN_RESET_HOURS * 3600 * 1000

# Plan usage (`claude -p "/usage"`): poll in the background at most this often,
# since the call is slow and not free. Set usage_enabled=false to disable.
USAGE_ENABLED = os.environ.get("VIBEMON_USAGE_ENABLED", "1") != "0"
USAGE_REFRESH_SECONDS = int(os.environ.get("VIBEMON_USAGE_REFRESH", "600") or "600")


def _show_flag(env_key: str, default: bool) -> bool:
    """Resolve a statusline segment toggle from env (backed by config show_*)."""
    val = os.environ.get(env_key)
    if val is None:
        return default
    return val != "0"


# Statusline segment toggles (config keys: show_*). Defaults match the curated
# layout — every segment on except the work-duration timer.
SHOW_PROJECT = _show_flag("VIBEMON_SHOW_PROJECT", True)
SHOW_GIT = _show_flag("VIBEMON_SHOW_GIT", True)
SHOW_MODEL = _show_flag("VIBEMON_SHOW_MODEL", True)
SHOW_TOKENS = _show_flag("VIBEMON_SHOW_TOKENS", True)
SHOW_COST = _show_flag("VIBEMON_SHOW_COST", True)
SHOW_DURATION = _show_flag("VIBEMON_SHOW_DURATION", False)
SHOW_LINES = _show_flag("VIBEMON_SHOW_LINES", True)
SHOW_MEMORY = _show_flag("VIBEMON_SHOW_MEMORY", True)
SHOW_USAGE = _show_flag("VIBEMON_SHOW_USAGE", True)
SHOW_USAGE_RESET = _show_flag("VIBEMON_SHOW_USAGE_RESET", True)
SHOW_VERSION = _show_flag("VIBEMON_SHOW_VERSION", True)

# Master display toggle: gates only the statusline output. Data collection
# (cache save, plan-usage refresh) still runs when this is off.
SHOW_STATUSLINE = _show_flag("VIBEMON_SHOW_STATUSLINE", True)

# Lock file timeout constants
LOCK_TIMEOUT_SECONDS = 5
LOCK_RETRY_INTERVAL = 0.05

# ============================================================================
# Utility Functions
# ============================================================================


def read_input() -> str:
    """Read input from stdin."""
    return sys.stdin.read()


def parse_json(data: str) -> dict[str, Any]:
    """Parse JSON string to dictionary."""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return {}


# ============================================================================
# Git Functions
# ============================================================================

# Branch emoji mapping based on branch name prefix
BRANCH_EMOJIS = {
    "main": "🌿",
    "master": "🌿",
    "develop": "🌱",
    "development": "🌱",
    "dev": "🌱",
    "feature": "✨",
    "feat": "✨",
    "fix": "🐛",
    "bugfix": "🐛",
    "hotfix": "🔥",
    "release": "📦",
    "chore": "🧹",
    "refactor": "♻️",
    "docs": "📝",
    "doc": "📝",
    "test": "🧪",
    "experiment": "🧪",
    "exp": "🧪",
}


def get_branch_emoji(branch: str) -> str:
    """Get emoji for branch based on name or prefix."""
    if not branch:
        return "🌿"

    branch_lower = branch.lower()

    # Check exact match first (main, master, develop, etc.)
    if branch_lower in BRANCH_EMOJIS:
        return BRANCH_EMOJIS[branch_lower]

    # Check prefix match (feature/xxx, fix/xxx, etc.)
    if "/" in branch_lower:
        prefix = branch_lower.split("/", 1)[0]
        if prefix in BRANCH_EMOJIS:
            return BRANCH_EMOJIS[prefix]

    # Default emoji
    return "🌿"


def get_git_root(directory: str) -> str | None:
    """Get git repository root directory."""
    if not directory:
        return None
    try:
        result = subprocess.run(
            ["git", "-C", directory, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def get_project_name(directory: str) -> str:
    """Get project name from git root or directory basename."""
    if not directory:
        return ""

    # Try git root first (handles subdirectory cases)
    git_root = get_git_root(directory)
    if git_root:
        name = os.path.basename(git_root)
        if name:
            return name

    # Fallback to directory basename
    return os.path.basename(directory)


def get_git_info(directory: str) -> str:
    """Get git branch and status information.

    Optimized to use single git command with status --porcelain --branch
    which provides both branch name and change status in one call.
    """
    if not directory:
        return ""

    try:
        # Single git command: get branch and status in one call
        # --porcelain=v1 --branch gives: "## branch...tracking" as first line
        # followed by changed files (if any)
        result = subprocess.run(
            [
                "git",
                "--no-optional-locks",
                "-C",
                directory,
                "status",
                "--porcelain=v1",
                "--branch",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode != 0:
            return ""

        lines = result.stdout.splitlines()
        if not lines:
            return ""

        # Parse branch from first line: "## branch" or "## branch...origin/branch"
        header = lines[0]
        if not header.startswith("## "):
            return ""

        branch_part = header[3:]  # Remove "## "
        # Handle "branch...origin/branch [ahead 1]" format
        branch = branch_part.split("...")[0].split()[0]

        if not branch or branch == "HEAD":
            # Detached HEAD state
            return ""

        # Check if there are any changes (lines after the header)
        has_changes = len(lines) > 1

        if has_changes:
            return f" git:({branch} *)"
        return f" git:({branch})"

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


# ============================================================================
# Context Window Functions
# ============================================================================


def get_context_usage(data: dict[str, Any]) -> str:
    """Calculate context window usage percentage.

    Args:
        data: Pre-parsed JSON dictionary
    """
    context_window = data.get("context_window", {})
    if not isinstance(context_window, dict):
        return ""

    # Try pre-calculated percentage first
    used_pct = context_window.get("used_percentage", 0)

    if used_pct and used_pct != "null":
        try:
            pct = float(used_pct)
            if pct > 0:
                return f"{int(pct)}%"
        except (ValueError, TypeError):
            pass

    # Fallback: calculate from current_usage
    try:
        context_size = int(context_window.get("context_window_size", 0) or 0)
        if context_size <= 0:
            return ""

        current_usage = context_window.get("current_usage", {})
        if not isinstance(current_usage, dict):
            return ""

        input_tokens = int(current_usage.get("input_tokens", 0) or 0)
        cache_creation = int(current_usage.get("cache_creation_input_tokens", 0) or 0)
        cache_read = int(current_usage.get("cache_read_input_tokens", 0) or 0)

        current_tokens = input_tokens + cache_creation + cache_read
        if current_tokens > 0:
            return f"{current_tokens * 100 // context_size}%"
    except (ValueError, TypeError):
        pass

    return ""


# ============================================================================
# VibeMon Cache Functions
# ============================================================================


def get_cache_path() -> str:
    """Get the cache file path."""
    cache_path = os.environ.get(
        "VIBEMON_CACHE_PATH", "~/.vibemon/cache/projects.json"
    )
    return os.path.expanduser(cache_path)


def save_to_cache(project: str, model: str, memory: int) -> None:
    """Save project metadata to cache file.

    Uses fcntl for proper file locking to avoid race conditions.
    """
    if not project:
        return

    cache_path = get_cache_path()
    cache_dir = os.path.dirname(cache_path)

    # Ensure cache directory exists
    os.makedirs(cache_dir, exist_ok=True)

    lockfile = f"{cache_path}.lock"
    timestamp = int(time.time())
    lock_fd = None

    try:
        # Use fcntl for proper file locking (atomic, no race condition)
        lock_fd = os.open(lockfile, os.O_CREAT | os.O_WRONLY, 0o644)

        # Try to acquire lock with timeout
        start_time = time.monotonic()
        while True:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break  # Lock acquired
            except (IOError, OSError):
                if time.monotonic() - start_time > LOCK_TIMEOUT_SECONDS:
                    return  # Timeout - skip cache update
                time.sleep(LOCK_RETRY_INTERVAL)

        # Read existing cache or create empty object
        cache: dict[str, Any] = {}
        if os.path.exists(cache_path):
            try:
                with open(cache_path) as f:
                    cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                cache = {}

        # If new project and cache is full, remove oldest to make room
        if project not in cache and len(cache) >= VIBE_MONITOR_MAX_PROJECTS:
            # Sort by timestamp and remove oldest
            sorted_items = sorted(
                cache.items(),
                key=lambda x: x[1].get("ts", 0) if isinstance(x[1], dict) else 0,
                reverse=True,
            )
            cache = dict(sorted_items[: VIBE_MONITOR_MAX_PROJECTS - 1])

        # Update cache with new project data
        cache[project] = {"model": model, "memory": memory, "ts": timestamp}

        # Atomic write: write to temp file, then rename
        tmpfile = f"{cache_path}.tmp.{os.getpid()}"
        with open(tmpfile, "w") as f:
            json.dump(cache, f)
        os.replace(tmpfile, cache_path)  # os.replace is atomic on POSIX

    except (IOError, OSError):
        pass
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            except OSError:
                pass


# ============================================================================
# ANSI Colors
# ============================================================================

C_RESET = "\033[0m"
C_DIM = "\033[2m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_MAGENTA = "\033[35m"
C_BLUE = "\033[34m"
C_ORANGE = "\033[38;5;208m"

# ============================================================================
# Formatting Functions
# ============================================================================


def format_number(num: int | float | str | None) -> str:
    """Format number with K/M suffix."""
    if num is None or num == "null" or num == 0:
        return "0"

    try:
        num_float = float(num)
        int_num = int(num_float)

        if int_num >= 1_000_000:
            return f"{num_float / 1_000_000:.1f}M"
        if int_num >= 1_000:
            return f"{num_float / 1_000:.1f}K"
        return str(int_num)
    except (ValueError, TypeError):
        return "0"


def format_duration(ms: int | float | str | None) -> str:
    """Format duration in milliseconds to human readable format."""
    if ms is None or ms == "null" or ms == 0:
        return "0s"

    try:
        total_seconds = int(ms) // 1000
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h{minutes}m"
        if minutes > 0:
            return f"{minutes}m{seconds}s"
        return f"{seconds}s"
    except (ValueError, TypeError):
        return "0s"


def format_cost(cost: float | str | None) -> str:
    """Format cost in USD."""
    if cost is None or cost == "null":
        return "$0.00"

    try:
        return f"${float(cost):.2f}"
    except (ValueError, TypeError):
        return "$0.00"


# ============================================================================
# Token Reset Functions
# ============================================================================


def get_token_window_path() -> str:
    """Get the token window state file path."""
    cache_dir = os.path.dirname(get_cache_path())
    return os.path.join(cache_dir, "token_window.json")


def load_window_start() -> float | None:
    """Load the token window start time from persistent file."""
    try:
        with open(get_token_window_path()) as f:
            data = json.load(f)
            return data.get("window_start")
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return None


def save_window_start(window_start: float) -> None:
    """Save the token window start time to persistent file (atomic write)."""
    window_file = get_token_window_path()
    try:
        os.makedirs(os.path.dirname(window_file), exist_ok=True)
        tmpfile = f"{window_file}.tmp.{os.getpid()}"
        with open(tmpfile, "w") as f:
            json.dump({"window_start": window_start}, f)
        os.replace(tmpfile, window_file)
    except (IOError, OSError):
        pass


def get_token_reset_info(duration_ms: int | float | str | None) -> tuple[int, str]:
    """Calculate token reset remaining time and local reset clock time.

    Tracks the 5-hour token window using a persisted start time,
    so the reset countdown stays accurate across multiple sessions.

    Returns:
        (remaining_ms, reset_time_str) e.g. (180000, "17:00")
        (0, "") if disabled or unavailable
    """
    if TOKEN_RESET_MS <= 0:
        return (0, "")

    if duration_ms is None or duration_ms == "null" or duration_ms == 0:
        return (0, "")

    try:
        now = time.time()
        token_reset_seconds = TOKEN_RESET_MS // 1000

        # Load persisted window start (survives across sessions)
        window_start = load_window_start()

        # Snap to the hour floor: Anthropic resets on the hour boundary
        if window_start is not None:
            window_start = window_start - (window_start % 3600)

        # If window expired or doesn't exist, start a new one
        if window_start is None or (now - window_start) >= token_reset_seconds:
            window_start = now - (now % 3600)
            save_window_start(window_start)

        # Calculate remaining time in window
        remaining_seconds = int(token_reset_seconds - (now - window_start))

        if remaining_seconds <= 0:
            return (0, "")

        remaining_ms = remaining_seconds * 1000

        # Calculate actual local reset time
        reset_timestamp = now + remaining_seconds
        reset_local = time.localtime(reset_timestamp)
        reset_time_str = time.strftime("%H:%M", reset_local)

        return (remaining_ms, reset_time_str)
    except (ValueError, TypeError):
        return (0, "")


def format_token_reset(remaining_ms: int, reset_time_str: str) -> str:
    """Format token reset display with color based on urgency.

    Shows remaining time until token reset (e.g. "⏳ 4h35m").
    Color indicates urgency: dim > 33%, orange 10-33%, red < 10%.
    """
    if remaining_ms <= 0:
        return ""

    # Format remaining time as hours/minutes
    total_minutes = remaining_ms // 60000
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours > 0:
        remaining_display = f"{hours}h{minutes}m"
    else:
        remaining_display = f"{minutes}m"

    # Color based on remaining percentage of window
    if TOKEN_RESET_MS > 0:
        remaining_pct = remaining_ms * 100 // TOKEN_RESET_MS
    else:
        remaining_pct = 100

    if remaining_pct <= 10:
        color = C_RED
    elif remaining_pct <= 33:
        color = C_ORANGE
    else:
        color = C_DIM

    return f"{color}⏳ {remaining_display}{C_RESET}"


# ============================================================================
# Progress Bar Functions
# ============================================================================


def build_progress_bar(percent_str: str | int | float, width: int = 10) -> str:
    """Build a colored progress bar.

    Args:
        percent_str: Percentage value (can be "85%", "85", 85, or 85.5)
        width: Bar width in characters
    """
    # Remove % sign if present and convert to string
    cleaned = str(percent_str).rstrip("%").strip()

    if not cleaned:
        return ""

    # Parse as float first to handle "12.5"
    try:
        percent_value = float(cleaned)
    except (ValueError, TypeError):
        return ""

    # Clamp to valid range
    percent_value = max(0.0, min(100.0, percent_value))
    percent = int(percent_value)

    if percent_value <= 0:
        filled = 0
    elif percent_value >= 100:
        filled = width
    else:
        filled = max(1, min(width - 1, round(percent_value * width / 100)))
    empty = width - filled

    # Build the bar - filled segments use one color by total ratio, empty in dim
    if percent > 90:
        color = C_RED
    elif percent > 70:
        color = C_ORANGE
    elif percent > 50:
        color = C_YELLOW
    else:
        color = C_GREEN

    filled_bar = f"{color}{'━' * filled}" if filled else ""
    empty_bar = "╌" * empty

    bar = f"{filled_bar}{C_RESET}" if filled_bar else ""
    if empty_bar:
        bar += f"{C_DIM}{empty_bar}{C_RESET}"

    return f"{bar} {percent}%"


# ============================================================================
# Plan Usage Functions (claude -p "/usage")
# ============================================================================


def get_usage_cache_path() -> str:
    """Get the plan-usage cache file path (next to the statusline cache)."""
    cache_dir = os.path.dirname(get_cache_path())
    return os.path.join(cache_dir, "usage.json")


def load_usage_cache() -> dict[str, Any] | None:
    """Load cached plan usage, or None if missing/unreadable."""
    try:
        with open(get_usage_cache_path()) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return None


def parse_usage_output(text: str) -> dict[str, Any]:
    """Parse `claude -p "/usage"` output into a usage dict.

    Matches lines by keyword so format tweaks degrade gracefully:

        Current session: 36% used · resets Jun 12 at 3:20pm (Asia/Seoul)
        Current week (all models): 37% used · resets ...
        Current week (Sonnet only): 0% used

    Returns {} if nothing parseable is found.
    """
    result: dict[str, Any] = {}
    if not text:
        return result

    def _pct(line: str) -> int | None:
        m = re.search(r"(\d+)%\s+used", line)
        return int(m.group(1)) if m else None

    def _resets(line: str) -> str:
        m = re.search(r"resets\s+(.+?)\s*$", line)
        return m.group(1).strip() if m else ""

    for raw in text.splitlines():
        line = raw.strip()
        low = line.lower()
        if "current session:" in low:
            pct = _pct(line)
            if pct is not None:
                entry: dict[str, Any] = {"pct": pct}
                resets = _resets(line)
                if resets:
                    entry["resets"] = resets
                result["session"] = entry
        elif "current week (all models):" in low:
            pct = _pct(line)
            if pct is not None:
                entry = {"pct": pct}
                resets = _resets(line)
                if resets:
                    entry["resets"] = resets
                result["week_all"] = entry
        elif "current week (sonnet only):" in low:
            pct = _pct(line)
            if pct is not None:
                result["week_sonnet"] = {"pct": pct}

    return result


def save_usage_cache(usage: dict[str, Any]) -> None:
    """Atomically write the usage cache (stamps a fresh `ts`)."""
    cache_path = get_usage_cache_path()
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        payload = dict(usage)
        payload["ts"] = int(time.time())
        tmpfile = f"{cache_path}.tmp.{os.getpid()}"
        with open(tmpfile, "w") as f:
            json.dump(payload, f)
        os.replace(tmpfile, cache_path)
    except (IOError, OSError):
        pass


def refresh_usage() -> None:
    """Fetch `claude -p "/usage"` and refresh the cache (runs in a child proc).

    A non-blocking lock ensures only one refresh runs at a time; concurrent
    callers exit immediately instead of spawning duplicate `claude` processes.
    """
    lockfile = f"{get_usage_cache_path()}.lock"
    lock_fd = None
    try:
        os.makedirs(os.path.dirname(lockfile), exist_ok=True)
        lock_fd = os.open(lockfile, os.O_CREAT | os.O_WRONLY, 0o644)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            return  # Another refresh is in flight

        try:
            result = subprocess.run(
                ["claude", "-p", "/usage"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return

        usage = parse_usage_output(result.stdout)
        if usage:
            save_usage_cache(usage)
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            except OSError:
                pass


def maybe_refresh_usage_background(cache: dict[str, Any] | None) -> None:
    """Spawn a background refresh when the usage cache is missing or stale."""
    if not USAGE_ENABLED:
        return
    if shutil.which("claude") is None:
        return

    ts = cache.get("ts", 0) if isinstance(cache, dict) else 0
    try:
        is_stale = (time.time() - float(ts)) > USAGE_REFRESH_SECONDS
    except (ValueError, TypeError):
        is_stale = True
    if not is_stale:
        return

    # Fork so the slow `claude -p` call never blocks the status line.
    if not hasattr(os, "fork"):
        return  # No safe non-blocking path; skip rather than stall rendering
    try:
        pid = os.fork()
        if pid == 0:
            try:
                refresh_usage()
            except Exception:
                pass
            os._exit(0)
    except OSError:
        pass


def build_usage_segment(cache: dict[str, Any] | None) -> str:
    """Render the plan-usage segment: 📊 S <bar> W <bar>."""
    if not isinstance(cache, dict):
        return ""

    seg: list[str] = []
    for label, key in (("S", "session"), ("W", "week_all")):
        entry = cache.get(key)
        if isinstance(entry, dict) and entry.get("pct") is not None:
            bar = build_progress_bar(entry["pct"], width=6)
            if bar:
                seg.append(f"{label} {bar}")

    if not seg:
        return ""
    return f"{C_CYAN}📊{C_RESET} " + " ".join(seg)


_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_reset_time(resets: str) -> float | None:
    """Parse a `/usage` reset string into a local epoch timestamp.

    Handles forms like "Jun 12 at 3:20pm (Asia/Seoul)" and "Jun 13 at 2am ...".
    The trailing timezone label is ignored: `/usage` already renders the clock
    in the user's local zone, so a naive local datetime is correct. The year is
    inferred (rolled forward across a year boundary). Returns None if
    unparseable.
    """
    if not resets:
        return None

    m = re.search(
        r"([A-Za-z]{3})[a-z]*\s+(\d{1,2})\s+at\s+(\d{1,2})(?::(\d{2}))?\s*([AaPp][Mm])",
        resets,
    )
    if not m:
        return None

    month = _MONTHS.get(m.group(1).lower())
    if not month:
        return None

    day = int(m.group(2))
    hour = int(m.group(3))
    minute = int(m.group(4) or 0)
    meridiem = m.group(5).lower()
    if meridiem == "pm" and hour != 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0

    now = datetime.now()
    for year in (now.year, now.year + 1):
        try:
            dt = datetime(year, month, day, hour, minute)
        except ValueError:
            return None
        # Use this year's date unless it's well in the past (year rollover).
        if (dt - now).total_seconds() >= -86400:
            return dt.timestamp()
    return None


def format_usage_reset(cache: dict[str, Any] | None) -> str:
    """Render time remaining until the session usage window resets (⏳).

    Color by urgency: red < 30m, orange < 1h, dim otherwise.
    """
    if not isinstance(cache, dict):
        return ""
    session = cache.get("session")
    if not isinstance(session, dict):
        return ""

    target = parse_reset_time(session.get("resets", ""))
    if target is None:
        return ""

    remaining = int(target - time.time())
    # Reset windows are at most days away; a far-future value means the date
    # was misparsed (e.g. an unexpected year rollover) — don't show it.
    if remaining <= 0 or remaining > 30 * 86400:
        return ""

    total_minutes = remaining // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60
    display = f"{hours}h{minutes}m" if hours > 0 else f"{minutes}m"

    if remaining <= 1800:
        color = C_RED
    elif remaining <= 3600:
        color = C_ORANGE
    else:
        color = C_DIM

    return f"{color}⏳ {display}{C_RESET}"


# ============================================================================
# Statusline Output
# ============================================================================


def build_statusline(
    model: str,
    dir_name: str,
    git_info: str,
    context_usage: str,
    input_tokens: int | str,
    output_tokens: int | str,
    cost: float | str,
    duration: int | str,
    lines_added: int | str,
    lines_removed: int | str,
    usage_segment: str = "",
    usage_reset: str = "",
    version: str = "",
) -> str:
    """Build the status line string.

    Each segment is gated by a SHOW_* toggle (config keys: show_*), so users
    can curate which fields appear. Default layout:
    📂 project │ 🌿 branch │ 🤖 model │ 📥📤 tokens │ 💰 cost │ +/- lines │
    🧠 memory │ 📊 usage │ ⏳ reset │ version  (work-duration ⏱️ off by default)
    """
    SEP = " │ "
    parts: list[str] = []

    # Directory (📂 icon)
    if SHOW_PROJECT:
        parts.append(f"{C_BLUE}📂 {dir_name}{C_RESET}")

    # Git info (emoji based on branch type)
    if SHOW_GIT and git_info:
        # Extract branch and status from " git:(branch *)" format
        branch_info = git_info.replace(" git:(", "").rstrip(")")
        # Get branch name without status indicator for emoji lookup
        branch_name = branch_info.rstrip(" *")
        emoji = get_branch_emoji(branch_name)
        parts.append(f"{C_GREEN}{emoji} {branch_info}{C_RESET}")

    # Model (🤖 icon) - remove "Claude " prefix
    if SHOW_MODEL:
        short_model = model.removeprefix("Claude ")
        parts.append(f"{C_MAGENTA}🤖 {short_model}{C_RESET}")

    # Token usage (📥 in / 📤 out)
    if SHOW_TOKENS and input_tokens and str(input_tokens) != "0":
        in_fmt = format_number(input_tokens)
        out_fmt = format_number(output_tokens)
        parts.append(f"{C_CYAN}📥 {in_fmt} 📤 {out_fmt}{C_RESET}")

    # Cost (💰 icon)
    if SHOW_COST and cost and str(cost) != "0" and cost != "null":
        cost_fmt = format_cost(cost)
        parts.append(f"{C_YELLOW}💰 {cost_fmt}{C_RESET}")

    # Duration (⏱️ icon)
    if SHOW_DURATION and duration and str(duration) != "0" and duration != "null":
        duration_fmt = format_duration(duration)
        parts.append(f"{C_DIM}⏱️ {duration_fmt}{C_RESET}")

    # Lines changed (+/-)
    if SHOW_LINES and lines_added and str(lines_added) != "0":
        lines_part = f"{C_GREEN}+{lines_added}{C_RESET}"
        if lines_removed and str(lines_removed) != "0":
            lines_part += f" {C_RED}-{lines_removed}{C_RESET}"
        parts.append(lines_part)

    # Context usage with progress bar (🧠 icon)
    if SHOW_MEMORY and context_usage:
        progress_bar = build_progress_bar(context_usage)
        if progress_bar:
            parts.append(f"🧠 {progress_bar}")

    # Plan usage with progress bars (📊 icon)
    if SHOW_USAGE and usage_segment:
        parts.append(usage_segment)

    # Session usage reset countdown (⏳ icon)
    if SHOW_USAGE_RESET and usage_reset:
        parts.append(usage_reset)

    # Claude Code version - always last
    if SHOW_VERSION and version:
        parts.append(f"{C_DIM}v{version}{C_RESET}")

    return SEP.join(parts)


# ============================================================================
# Background Cache Save
# ============================================================================


def save_cache_background(project: str, model: str, memory: int) -> None:
    """Save to cache in background process.

    Uses fork on POSIX systems for efficiency, falls back to synchronous
    save on Windows or if fork fails.
    """
    # Check if fork is available (not on Windows)
    if not hasattr(os, "fork"):
        save_to_cache(project, model, memory)
        return

    try:
        pid = os.fork()
        if pid == 0:
            # Child process - save cache and exit
            try:
                save_to_cache(project, model, memory)
            except Exception:
                pass
            os._exit(0)
        # Parent process continues immediately
    except OSError:
        # Fork failed - save synchronously
        save_to_cache(project, model, memory)


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    """Main entry point."""
    # Disable statusline for team sub-agents spawned via Task tool
    # Task tool agents run with CLAUDE_CODE_ENTRYPOINT=local-agent
    # STATUSLINE_DISABLED=1 allows manual override
    entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "cli")
    if entrypoint == "local-agent" or os.environ.get("STATUSLINE_DISABLED") == "1":
        return

    input_raw = read_input()

    # Parse JSON once and reuse
    data = parse_json(input_raw)

    # Extract model info
    model_data = data.get("model", {})
    model_display = (
        model_data.get("display_name", "Claude")
        if isinstance(model_data, dict)
        else "Claude"
    )

    # Extract workspace info
    workspace_data = data.get("workspace", {})
    current_dir = (
        workspace_data.get("current_dir", "")
        if isinstance(workspace_data, dict)
        else ""
    )
    dir_name = get_project_name(current_dir) if current_dir else ""

    # Get additional info
    git_info = get_git_info(current_dir)
    context_usage = get_context_usage(data)

    # Extract context window data
    context_window = data.get("context_window", {})
    if isinstance(context_window, dict):
        input_tokens = context_window.get("total_input_tokens", 0)
        output_tokens = context_window.get("total_output_tokens", 0)
    else:
        input_tokens = output_tokens = 0

    # Extract cost data
    cost_data = data.get("cost", {})
    if isinstance(cost_data, dict):
        cost = cost_data.get("total_cost_usd", 0)
        duration = cost_data.get("total_duration_ms", 0)
        lines_added = cost_data.get("total_lines_added", 0)
        lines_removed = cost_data.get("total_lines_removed", 0)
    else:
        cost = duration = lines_added = lines_removed = 0

    # Plan usage (cached; refreshed in background when stale)
    usage_cache = load_usage_cache()
    maybe_refresh_usage_background(usage_cache)
    usage_segment = build_usage_segment(usage_cache)

    # Session reset countdown: prefer the real /usage reset time; fall back to
    # the duration-based 5h-window heuristic when usage data isn't available.
    usage_reset = format_usage_reset(usage_cache)
    if not usage_reset:
        remaining_ms, reset_time_str = get_token_reset_info(duration)
        usage_reset = format_token_reset(remaining_ms, reset_time_str)

    # Extract Claude Code version
    version = data.get("version", "") or ""
    if not isinstance(version, str):
        version = str(version)

    # Save project metadata to cache in background
    # Convert "85%" to 85, "" to 0
    memory_int = int(context_usage.rstrip("%")) if context_usage else 0
    save_cache_background(dir_name, model_display, memory_int)

    # Display toggle: data was collected above; only the rendered line is gated.
    if not SHOW_STATUSLINE:
        return

    # Output statusline
    print(
        build_statusline(
            model_display,
            dir_name,
            git_info,
            context_usage,
            input_tokens,
            output_tokens,
            cost,
            duration,
            lines_added,
            lines_removed,
            usage_segment,
            usage_reset,
            version,
        ),
        end="",
    )


if __name__ == "__main__":
    main()
