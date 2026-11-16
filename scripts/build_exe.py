import os
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path


def _read_app_version(project_root: Path) -> str:
    """Read __version__ from the package without importing it."""
    init = project_root / "spicetifix" / "__init__.py"
    match = re.search(r'__version__\s*=\s*"([^"]+)"', init.read_text(encoding="utf-8"))
    return match.group(1) if match else "0.0.0"


def _write_version_file(project_root: Path, version: str) -> Path:
    """Write a PyInstaller version resource so the EXE's Properties show a version."""
    parts = [int(p) if p.isdigit() else 0 for p in version.split(".")]
    parts += [0] * (4 - len(parts))
    ver_tuple = f"({parts[0]}, {parts[1]}, {parts[2]}, {parts[3]})"
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={ver_tuple},
    prodvers={ver_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', 'RAlexander777'),
        StringStruct('FileDescription', 'Spicetifix - Spotify & Spicetify setup'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', 'Spicetifix'),
        StringStruct('OriginalFilename', 'Spicetifix.exe'),
        StringStruct('ProductName', 'Spicetifix'),
        StringStruct('ProductVersion', '{version}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    path = project_root / "build" / "version_info.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _add_file_to_zip(zf, file, arcname):
    """Write a file into the zip with a UTC extended-timestamp (0x5455) extra
    field so extraction tools display the correct local time regardless of
    timezone. Without it, DOS timestamps are interpreted ambiguously and some
    tools shift them by the UTC offset."""
    info = zipfile.ZipInfo.from_file(file, arcname)
    info.compress_type = zipfile.ZIP_DEFLATED
    mtime = int(os.stat(file).st_mtime)
    info.extra += b"\x55\x54\x05\x00\x01" + struct.pack("<I", mtime)
    with open(file, "rb") as fh:
        zf.writestr(info, fh.read())


def build_standalone_exe(console=False):
    print("=" * 50)
    print("   SPICETIFIX BUILDER (PyInstaller + ZIP)")
    print("=" * 50)

    project_root = Path(__file__).resolve().parent.parent
    main_script = project_root / "main.py"
    web_dir = project_root / "web"
    dist_dir = project_root / "dist"
    app_name = "Spicetifix"

    try:
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], capture_output=True, check=True)
    except Exception:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    version = _read_app_version(project_root)
    version_file = _write_version_file(project_root, version)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--clean",
        "--noupx",
        f"--name={app_name}",
        f"--add-data={web_dir}{os.pathsep}web",
        f"--version-file={version_file}",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.filedialog",
        "--collect-all=spicetifix",
        "--collect-all=webview",
        "--hidden-import=pythonnet",
        "--hidden-import=clr_loader",
        "--exclude-module=PyQt5",
        "--exclude-module=PyQt6",
        "--exclude-module=Pyside6",
        str(main_script),
    ]

    if not console:
        cmd.insert(cmd.index("--clean") + 1, "--windowed")

    print(f"\nRunning: {' '.join(cmd)}\n")
    res = subprocess.run(cmd, cwd=str(project_root))

    if res.returncode != 0:
        print("\nBUILD FAILED.")
        return False

    app_dir = dist_dir / app_name
    exe_path = app_dir / f"{app_name}.exe"
    if not exe_path.exists():
        print(f"\nERROR: {exe_path} not found.")
        return False

    print(f"\nExecutable: {exe_path}")

    zip_path = dist_dir / f"{app_name}.zip"
    print(f"Creating ZIP archive: {zip_path} ...")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in app_dir.rglob("*"):
            if file.is_file():
                arcname = str(file.relative_to(dist_dir))
                _add_file_to_zip(zf, file, arcname)

    print(f"ZIP archive: {zip_path} ({os.path.getsize(zip_path) / 1024 / 1024:.1f} MB)")
    print("\nBUILD SUCCESSFUL!")
    print(f"  Folder: {app_dir}")
    print(f"  ZIP:    {zip_path}")
    return True


def build_zip_only():
    project_root = Path(__file__).resolve().parent.parent
    dist_dir = project_root / "dist"
    app_name = "Spicetifix"
    app_dir = dist_dir / app_name

    if not app_dir.exists():
        print(f"ERROR: {app_dir} not found. Run the full build first.")
        return False

    zip_path = dist_dir / f"{app_name}.zip"
    print(f"Creating ZIP archive: {zip_path} ...")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in app_dir.rglob("*"):
            if file.is_file():
                arcname = str(file.relative_to(dist_dir))
                _add_file_to_zip(zf, file, arcname)

    print(f"ZIP created: {zip_path} ({os.path.getsize(zip_path) / 1024 / 1024:.1f} MB)")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--zip-only":
        ok = build_zip_only()
    elif len(sys.argv) > 1 and sys.argv[1] == "--console":
        ok = build_standalone_exe(console=True)
    else:
        ok = build_standalone_exe()
    sys.exit(0 if ok else 1)
