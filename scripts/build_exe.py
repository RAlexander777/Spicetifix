import os
import subprocess
import zipfile
from pathlib import Path


def build_standalone_exe():
    print("=" * 50)
    print("   SPICETIFIX BUILDER (PyInstaller + ZIP)")
    print("=" * 50)

    project_root = Path(__file__).resolve().parent.parent
    main_script = project_root / "main.py"
    web_dir = project_root / "web"
    dist_dir = project_root / "dist"
    app_name = "Spicetifix"

    try:
        subprocess.run(["pyinstaller", "--version"], capture_output=True, check=True)
    except Exception:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--clean",
        f"--name={app_name}",
        f"--add-data={web_dir}{os.pathsep}web",
        "--add-data", f"{project_root / 'spicetifix'}{os.pathsep}spicetifix",
        str(main_script),
    ]

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
                zf.write(file, arcname)

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
                zf.write(file, arcname)

    print(f"ZIP created: {zip_path} ({os.path.getsize(zip_path) / 1024 / 1024:.1f} MB)")
    return True


import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--zip-only":
        build_zip_only()
    else:
        build_standalone_exe()
