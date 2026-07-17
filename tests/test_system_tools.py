from unittest.mock import MagicMock
from src.domain.interfaces.system_service import AbstractSystemService
from src.application.tools.system_tools import (
    SystemCreateFolderTool,
    SystemRenameFileTool,
    SystemCopyFileTool,
    SystemMoveFileTool,
    SystemDeleteFileTool,
    SystemSearchFilesTool,
    SystemOpenDownloadsTool,
    SystemOpenDocumentsTool,
    SystemReadCpuTool,
    SystemReadRamTool,
    SystemReadDiskTool,
    SystemReadBatteryTool,
    SystemMonitorProcessesTool,
)


def test_system_create_folder_tool() -> None:
    mock_service = MagicMock(spec=AbstractSystemService)
    tool = SystemCreateFolderTool(mock_service)
    assert tool.name == "system_create_folder"

    tool.execute(folder_path="~/test")
    mock_service.create_folder.assert_called_once_with("~/test")


def test_system_rename_file_tool() -> None:
    mock_service = MagicMock(spec=AbstractSystemService)
    tool = SystemRenameFileTool(mock_service)
    assert tool.name == "system_rename_file"

    tool.execute(old_path="old.txt", new_path="new.txt", confirmed=True)
    mock_service.rename_file.assert_called_once_with("old.txt", "new.txt", True)


def test_system_copy_file_tool() -> None:
    mock_service = MagicMock(spec=AbstractSystemService)
    tool = SystemCopyFileTool(mock_service)
    assert tool.name == "system_copy_file"

    tool.execute(src_path="src.txt", dest_path="dest.txt", confirmed=False)
    mock_service.copy_file.assert_called_once_with("src.txt", "dest.txt", False)


def test_system_move_file_tool() -> None:
    mock_service = MagicMock(spec=AbstractSystemService)
    tool = SystemMoveFileTool(mock_service)
    assert tool.name == "system_move_file"

    tool.execute(src_path="src.txt", dest_path="dest.txt", confirmed=True)
    mock_service.move_file.assert_called_once_with("src.txt", "dest.txt", True)


def test_system_delete_file_tool() -> None:
    mock_service = MagicMock(spec=AbstractSystemService)
    tool = SystemDeleteFileTool(mock_service)
    assert tool.name == "system_delete_file"

    tool.execute(path="trash.txt", confirmed=True)
    mock_service.delete_file.assert_called_once_with("trash.txt", True)


def test_system_search_files_tool() -> None:
    mock_service = MagicMock(spec=AbstractSystemService)
    mock_service.search_files.return_value = ["/path/to/a.txt"]
    tool = SystemSearchFilesTool(mock_service)
    assert tool.name == "system_search_files"

    res = tool.execute(search_dir="~/docs", pattern="*.txt")
    assert "a.txt" in res
    mock_service.search_files.assert_called_once_with("~/docs", "*.txt")


def test_system_open_folders_tools() -> None:
    mock_service = MagicMock(spec=AbstractSystemService)

    # Downloads
    tool_dl = SystemOpenDownloadsTool(mock_service)
    assert tool_dl.name == "system_open_downloads"
    tool_dl.execute()
    mock_service.open_downloads.assert_called_once()

    # Documents
    tool_docs = SystemOpenDocumentsTool(mock_service)
    assert tool_docs.name == "system_open_documents"
    tool_docs.execute()
    mock_service.open_documents.assert_called_once()


def test_system_read_cpu_tool() -> None:
    mock_service = MagicMock(spec=AbstractSystemService)
    mock_service.read_cpu.return_value = {
        "usage_percent": 15.5,
        "cores_physical": 4,
        "cores_logical": 8,
        "frequency_mhz": 2400.0,
    }
    tool = SystemReadCpuTool(mock_service)
    assert tool.name == "system_read_cpu"

    res = tool.execute()
    assert "CPU Utilization: 15.5%" in res
    assert "Cores: 4" in res


def test_system_read_ram_tool() -> None:
    mock_service = MagicMock(spec=AbstractSystemService)
    mock_service.read_ram.return_value = {
        "total_bytes": 16 * 1024**3,
        "available_bytes": 8 * 1024**3,
        "used_bytes": 8 * 1024**3,
        "free_bytes": 4 * 1024**3,
        "percent": 50.0,
    }
    tool = SystemReadRamTool(mock_service)
    assert tool.name == "system_read_ram"

    res = tool.execute()
    assert "RAM Usage: 50.0%" in res
    assert "Total Memory: 16.00 GB" in res


def test_system_read_disk_tool() -> None:
    mock_service = MagicMock(spec=AbstractSystemService)
    mock_service.read_disk.return_value = {
        "total_bytes": 500 * 1024**3,
        "used_bytes": 200 * 1024**3,
        "free_bytes": 300 * 1024**3,
        "percent": 40.0,
    }
    tool = SystemReadDiskTool(mock_service)
    assert tool.name == "system_read_disk"

    res = tool.execute()
    assert "Disk Usage: 40.0%" in res
    assert "Total Capacity: 500.00 GB" in res


def test_system_read_battery_tool() -> None:
    mock_service = MagicMock(spec=AbstractSystemService)
    mock_service.read_battery.return_value = {
        "percent": 88,
        "secsleft": 7200,
        "power_plugged": False,
        "status": "On Battery",
    }
    tool = SystemReadBatteryTool(mock_service)
    assert tool.name == "system_read_battery"

    res = tool.execute()
    assert "Battery Level: 88%" in res
    assert "Remaining: 2h 0m" in res


def test_system_monitor_processes_tool() -> None:
    mock_service = MagicMock(spec=AbstractSystemService)
    mock_service.monitor_processes.return_value = [
        {
            "pid": 1234,
            "name": "python",
            "cpu_percent": 12.0,
            "memory_percent": 2.5,
            "username": "jojo",
        }
    ]
    tool = SystemMonitorProcessesTool(mock_service)
    assert tool.name == "system_monitor_processes"

    res = tool.execute(limit=5)
    assert "python" in res
    assert "1234" in res
    mock_service.monitor_processes.assert_called_once_with(limit=5)
