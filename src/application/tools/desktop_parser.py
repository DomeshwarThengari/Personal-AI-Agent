import os
import re
from pathlib import Path
from typing import List, Optional, Set
from src.domain.entities import InstalledApp
from src.utils.logging import get_logger

logger = get_logger("desktop_parser")

DEFAULT_DESKTOP_DIRS = [
    "/usr/share/applications",
    "/usr/local/share/applications",
    os.path.expanduser("~/.local/share/applications"),
    "/var/lib/flatpak/exports/share/applications",
    os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
]


def parse_desktop_file(filepath: Path) -> Optional[InstalledApp]:
    """Reads a Linux .desktop file and maps it to an InstalledApp entity.

    Args:
        filepath: Absolute Path object referencing the .desktop entry.

    Returns:
        An InstalledApp instance if parsed successfully, else None.
    """
    try:
        content = filepath.read_text(errors="ignore")
        if "[Desktop Entry]" not in content:
            return None

        name: Optional[str] = None
        exec_cmd: Optional[str] = None
        generic_name: Optional[str] = None
        categories: List[str] = []
        keywords: List[str] = []
        no_display: bool = False

        in_entry_section = False
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("["):
                if line == "[Desktop Entry]":
                    in_entry_section = True
                else:
                    in_entry_section = False
                continue

            if not in_entry_section:
                continue

            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()

                if key == "Name":
                    name = val
                elif key == "Exec":
                    exec_cmd = val
                elif key == "GenericName":
                    generic_name = val
                elif key == "Categories":
                    categories = [c.strip() for c in val.split(";") if c.strip()]
                elif key == "Keywords":
                    keywords = [k.strip() for k in val.split(";") if k.strip()]
                elif key == "NoDisplay":
                    no_display = val.lower() == "true"

        # Skip system shortcuts or utilities that don't display a GUI
        if no_display or not name or not exec_cmd:
            return None

        # Clean Exec line of placeholders: e.g. 'command %u' or 'command %F' -> 'command'
        clean_exec = re.sub(r"\s+%\w", "", exec_cmd).strip()

        # Remove quotes if wrapping command
        if (clean_exec.startswith('"') and clean_exec.endswith('"')) or (
            clean_exec.startswith("'") and clean_exec.endswith("'")
        ):
            clean_exec = clean_exec[1:-1].strip()

        return InstalledApp(
            name=name,
            exec_command=clean_exec,
            generic_name=generic_name,
            categories=categories,
            keywords=keywords,
        )
    except Exception as e:
        logger.debug(f"Failed to parse desktop file '{filepath}': {e}")
        return None


def scan_installed_apps(dirs: Optional[List[str]] = None) -> List[InstalledApp]:
    """Scans desktop directories and returns a de-duplicated list of installed apps.

    Args:
        dirs: Optional custom paths to search. Defaults to standard Linux paths.

    Returns:
        A List of InstalledApp entities.
    """
    if dirs is None:
        dirs = DEFAULT_DESKTOP_DIRS

    apps: List[InstalledApp] = []
    seen_names: Set[str] = set()

    for d in dirs:
        dir_path = Path(d)
        if not dir_path.is_dir():
            continue

        for filepath in dir_path.glob("*.desktop"):
            app = parse_desktop_file(filepath)
            if app:
                name_key = app.name.lower()
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    apps.append(app)

    logger.debug(
        f"Completed scanning {len(dirs)} directories. Found {len(apps)} applications."
    )
    return apps
