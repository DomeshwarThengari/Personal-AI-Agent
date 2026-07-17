from abc import ABC, abstractmethod
from typing import Any, List


class AbstractSystemService(ABC):
    """Port interface defining local system monitoring and file management capabilities."""

    @abstractmethod
    def create_folder(self, folder_path: str) -> str:
        """Creates a new folder at the specified path."""
        pass

    @abstractmethod
    def rename_file(self, old_path: str, new_path: str, confirmed: bool = False) -> str:
        """Renames a file or folder.

        If target already exists, confirmed must be True to overwrite.
        """
        pass

    @abstractmethod
    def copy_file(self, src_path: str, dest_path: str, confirmed: bool = False) -> str:
        """Copies a file or folder to the destination.

        If target already exists, confirmed must be True to overwrite.
        """
        pass

    @abstractmethod
    def move_file(self, src_path: str, dest_path: str, confirmed: bool = False) -> str:
        """Moves a file or folder to the destination.

        If target already exists, confirmed must be True to overwrite.
        """
        pass

    @abstractmethod
    def delete_file(self, path: str, confirmed: bool = False) -> str:
        """Deletes a file or directory. Requires confirmation."""
        pass

    @abstractmethod
    def search_files(self, search_dir: str, pattern: str) -> List[str]:
        """Searches files under a directory using glob/wildcard patterns."""
        pass

    @abstractmethod
    def open_downloads(self) -> str:
        """Opens the user's default Downloads folder."""
        pass

    @abstractmethod
    def open_documents(self) -> str:
        """Opens the user's default Documents folder."""
        pass

    @abstractmethod
    def read_cpu(self) -> dict[str, Any]:
        """Retrieves current CPU load statistics."""
        pass

    @abstractmethod
    def read_ram(self) -> dict[str, Any]:
        """Retrieves system memory utilization statistics."""
        pass

    @abstractmethod
    def read_disk(self) -> dict[str, Any]:
        """Retrieves partition disk usage statistics."""
        pass

    @abstractmethod
    def read_battery(self) -> dict[str, Any]:
        """Retrieves systems battery and power supply details."""
        pass

    @abstractmethod
    def monitor_processes(self, limit: int = 10) -> List[dict[str, Any]]:
        """Retrieves a list of top running system processes sorted by CPU usage."""
        pass
