"""Utility functions: logging setup, privilege checks, dependency validation."""

import logging
import ctypes
import sys
import importlib
from typing import List, Tuple


def setup_logger(
    name: str = "blox_fruits_tool",
    level: str = "INFO",
    log_to_file: bool = True,
    log_file_path: str = "blox_fruits_tool.log",
) -> logging.Logger:
    """Create and return a configured logger instance.

    Args:
        name: Logger name used throughout the application.
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_to_file: If True, also write logs to *log_file_path*.
        log_file_path: Path to the log file on disk.

    Returns:
        A ready-to-use :class:`logging.Logger` object.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_to_file:
        try:
            file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError as exc:
            logger.warning("Could not create log file: %s", exc)

    return logger


def is_admin() -> bool:
    """Check whether the current process has administrator / root privileges.

    Returns:
        True if running with elevated privileges, False otherwise.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        # Fallback for non-Windows systems
        try:
            return os.geteuid() == 0  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            return False


def check_dependencies() -> List[Tuple[str, bool, str]]:
    """Verify that required third-party packages are importable.

    Returns:
        A list of tuples: (package_name, is_available, version_or_error).
    """
    required = {
        "keyboard": "keyboard",
        "pyautogui": "pyautogui",
        "cv2": "opencv-python",
        "PIL": "pillow",
        "numpy": "numpy",
    }
    results: List[Tuple[str, bool, str]] = []
    for import_name, display_name in required.items():
        try:
            mod = importlib.import_module(import_name)
            version = getattr(mod, "__version__", "unknown")
            results.append((display_name, True, version))
        except ImportError as exc:
            results.append((display_name, False, str(exc)))
    return results


def print_dependency_report(logger: logging.Logger) -> bool:
    """Log the dependency check results and return True if all are present."""
    results = check_dependencies()
    all_ok = True
    for name, available, info in results:
        if available:
            logger.info("  [OK] %s (version %s)", name, info)
        else:
            logger.error("  [MISSING] %s – %s", name, info)
            all_ok = False
    return all_ok


# Lazy import for os (used only in the fallback branch of is_admin)
import os  # noqa: E402
