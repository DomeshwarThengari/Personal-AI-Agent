from typing import Any, Dict
from src.domain.interfaces.tool import AbstractTool
from src.domain.interfaces.system_service import AbstractSystemService


class SystemCreateFolderTool(AbstractTool):
    """Creates a new directory folder."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_create_folder"

    @property
    def description(self) -> str:
        return "Create a new folder or directory at the specified path."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "folder_path": {
                    "type": "string",
                    "description": "The destination path where the folder should be created.",
                }
            },
            "required": ["folder_path"],
        }

    def execute(self, **kwargs: Any) -> str:
        folder_path = kwargs.get("folder_path")
        if not folder_path:
            return "Error: Parameter 'folder_path' is required."
        return self.system_service.create_folder(folder_path)


class SystemRenameFileTool(AbstractTool):
    """Renames a file or directory."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_rename_file"

    @property
    def description(self) -> str:
        return "Rename a file or folder from an old path to a new path. Can overwrite destination if confirmed=True."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "old_path": {
                    "type": "string",
                    "description": "The current path of the file or folder.",
                },
                "new_path": {
                    "type": "string",
                    "description": "The new target path of the file or folder.",
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Explicit confirmation to overwrite destination if it already exists.",
                    "default": False,
                },
            },
            "required": ["old_path", "new_path"],
        }

    def execute(self, **kwargs: Any) -> str:
        old_path = kwargs.get("old_path")
        new_path = kwargs.get("new_path")
        confirmed = bool(kwargs.get("confirmed", False))
        if not old_path or not new_path:
            return "Error: Both 'old_path' and 'new_path' parameters are required."
        return self.system_service.rename_file(old_path, new_path, confirmed)


class SystemCopyFileTool(AbstractTool):
    """Copies files or directories."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_copy_file"

    @property
    def description(self) -> str:
        return "Copy a file or directory to a destination path. Can overwrite destination if confirmed=True."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "src_path": {
                    "type": "string",
                    "description": "The source file or directory path to copy.",
                },
                "dest_path": {
                    "type": "string",
                    "description": "The target path where the copy should be placed.",
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Explicit confirmation to overwrite destination if it already exists.",
                    "default": False,
                },
            },
            "required": ["src_path", "dest_path"],
        }

    def execute(self, **kwargs: Any) -> str:
        src_path = kwargs.get("src_path")
        dest_path = kwargs.get("dest_path")
        confirmed = bool(kwargs.get("confirmed", False))
        if not src_path or not dest_path:
            return "Error: Both 'src_path' and 'dest_path' parameters are required."
        return self.system_service.copy_file(src_path, dest_path, confirmed)


class SystemMoveFileTool(AbstractTool):
    """Moves files or directories."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_move_file"

    @property
    def description(self) -> str:
        return "Move a file or directory to a target path. Can overwrite destination if confirmed=True."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "src_path": {
                    "type": "string",
                    "description": "The source file or directory path to move.",
                },
                "dest_path": {
                    "type": "string",
                    "description": "The target path where it should be moved.",
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Explicit confirmation to overwrite destination if it already exists.",
                    "default": False,
                },
            },
            "required": ["src_path", "dest_path"],
        }

    def execute(self, **kwargs: Any) -> str:
        src_path = kwargs.get("src_path")
        dest_path = kwargs.get("dest_path")
        confirmed = bool(kwargs.get("confirmed", False))
        if not src_path or not dest_path:
            return "Error: Both 'src_path' and 'dest_path' parameters are required."
        return self.system_service.move_file(src_path, dest_path, confirmed)


class SystemDeleteFileTool(AbstractTool):
    """Deletes files or directories safely."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_delete_file"

    @property
    def description(self) -> str:
        return (
            "Delete a file or directory. WARNING: This is a dangerous action. "
            "Requires setting confirmed=True to skip interactive prompts or prevent failures."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file or directory to delete.",
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Explicit confirmation to delete the file/folder.",
                    "default": False,
                },
            },
            "required": ["path"],
        }

    def execute(self, **kwargs: Any) -> str:
        path = kwargs.get("path")
        confirmed = bool(kwargs.get("confirmed", False))
        if not path:
            return "Error: Parameter 'path' is required."
        return self.system_service.delete_file(path, confirmed)


class SystemSearchFilesTool(AbstractTool):
    """Searches for files matching pattern."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_search_files"

    @property
    def description(self) -> str:
        return "Search for files under a directory using glob/wildcard patterns (e.g. '*.txt' or 'report*')."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "search_dir": {
                    "type": "string",
                    "description": "The directory root where search should begin.",
                },
                "pattern": {
                    "type": "string",
                    "description": "The pattern matching wildcard string.",
                },
            },
            "required": ["search_dir", "pattern"],
        }

    def execute(self, **kwargs: Any) -> str:
        search_dir = kwargs.get("search_dir")
        pattern = kwargs.get("pattern")
        if not search_dir or not pattern:
            return "Error: Both 'search_dir' and 'pattern' parameters are required."
        results = self.system_service.search_files(search_dir, pattern)
        if not results:
            return (
                f"No matching files found under '{search_dir}' for pattern '{pattern}'."
            )
        return "Matching files:\n" + "\n".join(results)


class SystemOpenDownloadsTool(AbstractTool):
    """Opens OS Downloads folder."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_open_downloads"

    @property
    def description(self) -> str:
        return "Open the system's default Downloads folder in the file manager view."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self, **kwargs: Any) -> str:
        return self.system_service.open_downloads()


class SystemOpenDocumentsTool(AbstractTool):
    """Opens OS Documents folder."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_open_documents"

    @property
    def description(self) -> str:
        return "Open the system's default Documents folder in the file manager view."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self, **kwargs: Any) -> str:
        return self.system_service.open_documents()


class SystemReadCpuTool(AbstractTool):
    """Reads system CPU stats."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_read_cpu"

    @property
    def description(self) -> str:
        return "Retrieve information about current CPU utilization, frequency, and core counts."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self, **kwargs: Any) -> str:
        cpu = self.system_service.read_cpu()
        if "error" in cpu:
            return f"Error reading CPU: {cpu['error']}"
        return (
            f"CPU Utilization: {cpu['usage_percent']:.1f}%\n"
            f"Physical Cores: {cpu['cores_physical']}\n"
            f"Logical Cores: {cpu['cores_logical']}\n"
            f"Current Frequency: {cpu['frequency_mhz']:.1f} MHz"
        )


class SystemReadRamTool(AbstractTool):
    """Reads system RAM stats."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_read_ram"

    @property
    def description(self) -> str:
        return "Retrieve virtual memory statistics including total capacity, used size, and free size."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self, **kwargs: Any) -> str:
        ram = self.system_service.read_ram()
        if "error" in ram:
            return f"Error reading RAM: {ram['error']}"

        to_gb = 1024**3
        return (
            f"RAM Usage: {ram['percent']}%\n"
            f"Total Memory: {ram['total_bytes'] / to_gb:.2f} GB\n"
            f"Used Memory: {ram['used_bytes'] / to_gb:.2f} GB\n"
            f"Available Memory: {ram['available_bytes'] / to_gb:.2f} GB\n"
            f"Free Memory: {ram['free_bytes'] / to_gb:.2f} GB"
        )


class SystemReadDiskTool(AbstractTool):
    """Reads system Disk stats."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_read_disk"

    @property
    def description(self) -> str:
        return "Retrieve disk storage statistics (capacity, free storage space, percentage)."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self, **kwargs: Any) -> str:
        disk = self.system_service.read_disk()
        if "error" in disk:
            return f"Error reading Disk: {disk['error']}"

        to_gb = 1024**3
        return (
            f"Disk Usage: {disk['percent']}%\n"
            f"Total Capacity: {disk['total_bytes'] / to_gb:.2f} GB\n"
            f"Used Space: {disk['used_bytes'] / to_gb:.2f} GB\n"
            f"Free Space: {disk['free_bytes'] / to_gb:.2f} GB"
        )


class SystemReadBatteryTool(AbstractTool):
    """Reads system Battery status."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_read_battery"

    @property
    def description(self) -> str:
        return "Retrieve battery charges and power connection details."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self, **kwargs: Any) -> str:
        bat = self.system_service.read_battery()
        if "error" in bat:
            return f"Error reading battery status: {bat['error']}"

        secs = bat["secsleft"]
        time_left = "Calculating..."
        if secs > 0:
            hrs = secs // 3600
            mins = (secs % 3600) // 60
            time_left = f"{hrs}h {mins}m"
        elif secs == -1:
            time_left = "N/A (Plugged in or unknown)"

        return (
            f"Battery Level: {bat['percent']}%\n"
            f"Status: {bat['status']}\n"
            f"Plugged In: {bat['power_plugged']}\n"
            f"Estimated Time Remaining: {time_left}"
        )


class SystemMonitorProcessesTool(AbstractTool):
    """Monitors running OS processes."""

    def __init__(self, system_service: AbstractSystemService) -> None:
        self.system_service = system_service

    @property
    def name(self) -> str:
        return "system_monitor_processes"

    @property
    def description(self) -> str:
        return "List active running processes sorted by highest CPU resource usage percentage."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of process items to retrieve (default: 10).",
                }
            },
            "required": [],
        }

    def execute(self, **kwargs: Any) -> str:
        limit = kwargs.get("limit", 10)
        try:
            limit_val = int(limit)
        except ValueError:
            limit_val = 10

        processes = self.system_service.monitor_processes(limit=limit_val)
        if not processes:
            return "No active processes could be queried."

        res = [
            f"{'PID':<8} | {'Process Name':<25} | {'CPU%':<6} | {'MEM%':<6} | {'User':<12}"
        ]
        res.append("-" * 65)
        for p in processes:
            res.append(
                f"{p['pid']:<8} | {p['name'][:25]:<25} | {p['cpu_percent']:<6.1f} | {p['memory_percent']:<6.1f} | {p['username'][:12]:<12}"
            )
        return "\n".join(res)
