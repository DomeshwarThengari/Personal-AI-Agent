import os
from pathlib import Path
from src.infrastructure.system.local_system_service import LocalSystemService


def test_create_folder(tmp_path: Path) -> None:
    service = LocalSystemService()
    folder = tmp_path / "test_folder"

    res = service.create_folder(str(folder))
    assert "Successfully created folder" in res
    assert folder.exists()
    assert folder.is_dir()


def test_rename_file(tmp_path: Path) -> None:
    service = LocalSystemService()
    src = tmp_path / "old.txt"
    src.write_text("hello")
    dest = tmp_path / "new.txt"

    # Rename successfully
    res = service.rename_file(str(src), str(dest))
    assert "Successfully renamed" in res
    assert not src.exists()
    assert dest.exists()
    assert dest.read_text() == "hello"

    # Destination already exists warning
    src_again = tmp_path / "old2.txt"
    src_again.write_text("another")
    res_warn = service.rename_file(str(src_again), str(dest), confirmed=False)
    assert "Warning" in res_warn
    assert src_again.exists()

    # Destination already exists overwrite
    res_overwrite = service.rename_file(str(src_again), str(dest), confirmed=True)
    assert "Successfully renamed" in res_overwrite
    assert not src_again.exists()
    assert dest.read_text() == "another"


def test_copy_file(tmp_path: Path) -> None:
    service = LocalSystemService()
    src = tmp_path / "src.txt"
    src.write_text("copy-me")
    dest = tmp_path / "dest.txt"

    res = service.copy_file(str(src), str(dest))
    assert "Successfully copied" in res
    assert src.exists()
    assert dest.exists()
    assert dest.read_text() == "copy-me"

    # Copy warning if destination exists
    src2 = tmp_path / "src2.txt"
    src2.write_text("different")
    res_warn = service.copy_file(str(src2), str(dest), confirmed=False)
    assert "Warning" in res_warn

    # Copy overwrite if destination exists
    res_overwrite = service.copy_file(str(src2), str(dest), confirmed=True)
    assert "Successfully copied" in res_overwrite
    assert dest.read_text() == "different"


def test_move_file(tmp_path: Path) -> None:
    service = LocalSystemService()
    src = tmp_path / "src.txt"
    src.write_text("move-me")
    dest = tmp_path / "dest.txt"

    res = service.move_file(str(src), str(dest))
    assert "Successfully moved" in res
    assert not src.exists()
    assert dest.exists()
    assert dest.read_text() == "move-me"

    # Move warning if destination exists
    src2 = tmp_path / "src2.txt"
    src2.write_text("different")
    res_warn = service.move_file(str(src2), str(dest), confirmed=False)
    assert "Warning" in res_warn

    # Move overwrite if destination exists
    res_overwrite = service.move_file(str(src2), str(dest), confirmed=True)
    assert "Successfully moved" in res_overwrite
    assert not src2.exists()
    assert dest.read_text() == "different"


def test_delete_file(tmp_path: Path) -> None:
    service = LocalSystemService()
    file_to_del = tmp_path / "delete.txt"
    file_to_del.write_text("delete-me")

    # Requiring confirmation warning
    res_warn = service.delete_file(str(file_to_del), confirmed=False)
    assert "Warning" in res_warn
    assert file_to_del.exists()

    # Deleting with confirmation
    res = service.delete_file(str(file_to_del), confirmed=True)
    assert "Successfully deleted" in res
    assert not file_to_del.exists()


def test_search_files(tmp_path: Path) -> None:
    service = LocalSystemService()
    dir_to_search = tmp_path / "search_root"
    os.makedirs(dir_to_search)

    (dir_to_search / "a.txt").write_text("a")
    (dir_to_search / "b.log").write_text("b")
    os.makedirs(dir_to_search / "sub")
    (dir_to_search / "sub" / "c.txt").write_text("c")

    results = service.search_files(str(dir_to_search), "*.txt")
    assert len(results) == 2
    basenames = [os.path.basename(r) for r in results]
    assert "a.txt" in basenames
    assert "c.txt" in basenames


def test_read_cpu_ram_disk_battery() -> None:
    service = LocalSystemService()

    # Read CPU
    cpu = service.read_cpu()
    assert "usage_percent" in cpu
    assert "cores_logical" in cpu

    # Read RAM
    ram = service.read_ram()
    assert "total_bytes" in ram
    assert "percent" in ram

    # Read Disk
    disk = service.read_disk()
    assert "total_bytes" in disk
    assert "percent" in disk

    # Read Battery
    battery = service.read_battery()
    assert "percent" in battery
    assert "power_plugged" in battery


def test_monitor_processes() -> None:
    service = LocalSystemService()
    processes = service.monitor_processes(limit=5)
    assert len(processes) <= 5
    if processes:
        assert "pid" in processes[0]
        assert "name" in processes[0]
        assert "cpu_percent" in processes[0]
