from pathlib import Path
from src.application.tools.desktop_parser import scan_installed_apps


def test_desktop_parser_and_scanner(tmp_path: Path) -> None:
    """Verifies parsing of standard, hidden, and malformed Linux .desktop entry files."""
    # 1. Create a mock desktop entry directory
    app_dir = tmp_path / "applications"
    app_dir.mkdir()

    # 2. Write a valid desktop file
    valid_file = app_dir / "app-a.desktop"
    valid_file.write_text("""[Desktop Entry]
Name=App A
Exec=cmd-a %u
GenericName=Web Browser
Categories=Network;WebBrowser;
Keywords=Internet;WWW;
""")

    # 3. Write a file with NoDisplay=true (should be ignored)
    nodisplay_file = app_dir / "app-b.desktop"
    nodisplay_file.write_text("""[Desktop Entry]
Name=App B Hidden
Exec=cmd-b
NoDisplay=true
""")

    # 4. Write a malformed desktop file
    malformed_file = app_dir / "app-c.desktop"
    malformed_file.write_text("""[Desktop Entry]
Comment=No Name or Exec here
""")

    # 5. Run scanner
    apps = scan_installed_apps(dirs=[str(app_dir)])

    # 6. Asserts
    assert len(apps) == 1
    app = apps[0]
    assert app.name == "App A"
    assert app.exec_command == "cmd-a"
    assert app.generic_name == "Web Browser"
    assert "Network" in app.categories
    assert "WebBrowser" in app.categories
    assert "Internet" in app.keywords
