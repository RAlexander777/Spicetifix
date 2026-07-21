import os
import sys
import subprocess
from pathlib import Path

def build_standalone_exe():
    """
    Compiles Automatify into a single portable Windows executable (.exe)
    bundling the Python web backend API and static web assets.
    """
    print("==================================================")
    print("   AUTOMATIFY STANDALONE EXE BUILDER (PyInstaller)")
    print("==================================================")

    project_root = Path(__file__).resolve().parent.parent
    main_script = project_root / "main.py"
    web_dir = project_root / "web"

    # Check if pyinstaller is installed
    try:
        subprocess.run(["pyinstaller", "--version"], capture_output=True, check=True)
    except Exception:
        print("PyInstaller not found in environment. Installing via pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=Automatify",
        f"--add-data={web_dir}{os.path.pathsep}web",
        str(main_script)
    ]

    print(f"Running build command: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(project_root))

    if res.returncode == 0:
        dist_exe = project_root / "dist" / "Automatify" / "Automatify.exe"
        print("\nBUILD SUCCESSFUL!")
        print(f"Executable generated at: {dist_exe}")
        return True
    else:
        print("\nBUILD FAILED.")
        return False

if __name__ == "__main__":
    build_standalone_exe()
