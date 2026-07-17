import glob
import os
import shutil
import subprocess
import sys
from typing import Any, List
import psutil
from src.domain.interfaces.system_service import AbstractSystemService
from src.utils.logging import get_logger

logger = get_logger("local_system_service")


class LocalSystemService(AbstractSystemService):
    """Local OS implementation of AbstractSystemService.

    Wraps standard shutil/os and psutil utilities to manage files, monitor hardware resources,
    list active tasks, and open directories natively on Linux.
    """

    def _resolve_path(self, path: str) -> str:
        """Helper to cleanly expand user home directory and return an absolute path."""
        return os.path.abspath(os.path.expanduser(path.strip()))

    def create_folder(self, folder_path: str) -> str:
        target = self._resolve_path(folder_path)
        try:
            os.makedirs(target, exist_ok=True)
            logger.info(f"Created folder at: {target}")
            return f"Successfully created folder: '{target}'."
        except Exception as e:
            logger.error(f"Failed to create folder '{target}': {e}")
            return f"Error: Failed to create folder. Reason: {e}"

    def rename_file(self, old_path: str, new_path: str, confirmed: bool = False) -> str:
        src = self._resolve_path(old_path)
        dest = self._resolve_path(new_path)

        if not os.path.exists(src):
            return f"Error: Source path '{src}' does not exist."

        if os.path.exists(dest):
            if not confirmed:
                return (
                    f"Warning: Destination path '{dest}' already exists. "
                    "Please confirm replacement by setting the 'confirmed' parameter to True."
                )
            # Remove target dest to overwrite
            try:
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                else:
                    os.remove(dest)
            except Exception as e:
                return f"Error: Failed to clear destination path '{dest}'. Reason: {e}"

        try:
            os.rename(src, dest)
            logger.info(f"Renamed '{src}' to '{dest}'")
            return f"Successfully renamed '{src}' to '{dest}'."
        except Exception as e:
            logger.error(f"Failed to rename '{src}' to '{dest}': {e}")
            return f"Error: Failed to rename. Reason: {e}"

    def copy_file(self, src_path: str, dest_path: str, confirmed: bool = False) -> str:
        src = self._resolve_path(src_path)
        dest = self._resolve_path(dest_path)

        if not os.path.exists(src):
            return f"Error: Source path '{src}' does not exist."

        if os.path.exists(dest):
            if not confirmed:
                return (
                    f"Warning: Destination path '{dest}' already exists. "
                    "Please confirm replacement by setting the 'confirmed' parameter to True."
                )
            try:
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                else:
                    os.remove(dest)
            except Exception as e:
                return f"Error: Failed to clear destination path '{dest}'. Reason: {e}"

        try:
            if os.path.isdir(src):
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
            logger.info(f"Copied '{src}' to '{dest}'")
            return f"Successfully copied '{src}' to '{dest}'."
        except Exception as e:
            logger.error(f"Failed to copy '{src}' to '{dest}': {e}")
            return f"Error: Failed to copy. Reason: {e}"

    def move_file(self, src_path: str, dest_path: str, confirmed: bool = False) -> str:
        src = self._resolve_path(src_path)
        dest = self._resolve_path(dest_path)

        if not os.path.exists(src):
            return f"Error: Source path '{src}' does not exist."

        if os.path.exists(dest):
            if not confirmed:
                return (
                    f"Warning: Destination path '{dest}' already exists. "
                    "Please confirm replacement by setting the 'confirmed' parameter to True."
                )
            try:
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                else:
                    os.remove(dest)
            except Exception as e:
                return f"Error: Failed to clear destination path '{dest}'. Reason: {e}"

        try:
            shutil.move(src, dest)
            logger.info(f"Moved '{src}' to '{dest}'")
            return f"Successfully moved '{src}' to '{dest}'."
        except Exception as e:
            logger.error(f"Failed to move '{src}' to '{dest}': {e}")
            return f"Error: Failed to move. Reason: {e}"

    def delete_file(self, path: str, confirmed: bool = False) -> str:
        target = self._resolve_path(path)

        if not os.path.exists(target):
            return f"Error: Path '{target}' does not exist."

        # Safety Check: If not confirmed via parameter, attempt terminal TTY query
        if not confirmed:
            if sys.stdin.isatty():
                try:
                    ans = (
                        input(f"Are you sure you want to delete '{target}'? (y/N): ")
                        .strip()
                        .lower()
                    )
                    if ans in ("y", "yes"):
                        confirmed = True
                except Exception:
                    pass

        if not confirmed:
            return (
                f"Warning: Deletion of '{target}' requires explicit user confirmation. "
                "Set the 'confirmed' parameter to True to proceed."
            )

        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
            logger.info(f"Deleted path: {target}")
            return f"Successfully deleted '{target}'."
        except Exception as e:
            logger.error(f"Failed to delete '{target}': {e}")
            return f"Error: Failed to delete. Reason: {e}"

    def search_files(self, search_dir: str, pattern: str) -> List[str]:
        directory = self._resolve_path(search_dir)
        if not os.path.exists(directory):
            logger.warning(f"Search directory '{directory}' does not exist.")
            return []

        # Recursively search for pattern using glob
        glob_pattern = os.path.join(directory, "**", pattern)
        try:
            results = glob.glob(glob_pattern, recursive=True)
            return [os.path.abspath(r) for r in results]
        except Exception as e:
            logger.error(f"Error during glob search in '{directory}': {e}")
            return []

    def _open_native_folder(self, folder_path: str) -> str:
        target = self._resolve_path(folder_path)
        if not os.path.exists(target):
            # Attempt to create the folder if it's Downloads or Documents
            try:
                os.makedirs(target, exist_ok=True)
            except Exception:
                return f"Error: Path '{target}' does not exist and cannot be created."

        try:
            # Native folder opening on Linux using xdg-open
            subprocess.Popen(
                ["xdg-open", target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Opened native folder: '{target}'")
            return f"Successfully opened folder: '{target}'"
        except Exception as e:
            logger.error(f"Failed to open native folder '{target}': {e}")
            return f"Error: Failed to open native folder. Reason: {e}"

    def open_downloads(self) -> str:
        return self._open_native_folder("~/Downloads")

    def open_documents(self) -> str:
        return self._open_native_folder("~/Documents")

    # --- System Monitoring ---

    def read_cpu(self) -> dict[str, Any]:
        try:
            # Querying cpu percentage (non-blocking)
            usage = psutil.cpu_percent(interval=0.1)
            cores_physical = psutil.cpu_count(logical=False) or 1
            cores_logical = psutil.cpu_count(logical=True) or 1
            freq = psutil.cpu_freq()
            freq_mhz = freq.current if freq else 0.0

            return {
                "usage_percent": usage,
                "cores_physical": cores_physical,
                "cores_logical": cores_logical,
                "frequency_mhz": freq_mhz,
            }
        except Exception as e:
            logger.error(f"Failed to read CPU info: {e}")
            return {"error": str(e)}

    def read_ram(self) -> dict[str, Any]:
        try:
            mem = psutil.virtual_memory()
            return {
                "total_bytes": mem.total,
                "available_bytes": mem.available,
                "used_bytes": mem.used,
                "free_bytes": mem.free,
                "percent": mem.percent,
            }
        except Exception as e:
            logger.error(f"Failed to read RAM info: {e}")
            return {"error": str(e)}

    def read_disk(self) -> dict[str, Any]:
        try:
            disk = psutil.disk_usage("/")
            return {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "percent": disk.percent,
            }
        except Exception as e:
            logger.error(f"Failed to read Disk info: {e}")
            return {"error": str(e)}

    def read_battery(self) -> dict[str, Any]:
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return {
                    "percent": 100,
                    "secsleft": -1,
                    "power_plugged": True,
                    "status": "No battery detected (Desktop / VM / Wall-powered)",
                }

            secs = battery.secsleft
            # psutil returns negative values if charging or unknown
            secs_left = secs if secs >= 0 else -1

            return {
                "percent": battery.percent,
                "secsleft": secs_left,
                "power_plugged": battery.power_plugged,
                "status": (
                    "Charging / Plugged in" if battery.power_plugged else "On Battery"
                ),
            }
        except Exception as e:
            logger.error(f"Failed to read Battery info: {e}")
            return {"error": str(e)}

    def monitor_processes(self, limit: int = 10) -> List[dict[str, Any]]:
        processes = []
        try:
            for proc in psutil.process_iter(
                ["pid", "name", "username", "cpu_percent", "memory_percent"]
            ):
                try:
                    info = proc.info
                    # Skip processes with invalid info
                    if info["pid"] is None:
                        continue
                    processes.append(
                        {
                            "pid": info["pid"],
                            "name": info["name"] or "unknown",
                            "username": info["username"] or "system",
                            "cpu_percent": info["cpu_percent"] or 0.0,
                            "memory_percent": info["memory_percent"] or 0.0,
                        }
                    )
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    pass

            # Sort by CPU usage descending
            processes.sort(key=lambda p: p["cpu_percent"], reverse=True)
            return processes[:limit]
        except Exception as e:
            logger.error(f"Failed to monitor processes: {e}")
            return []
