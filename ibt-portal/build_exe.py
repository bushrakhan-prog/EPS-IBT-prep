"""
IBT Portal — EXE Builder
========================
Run this ONCE on your laptop to create IBTPortal.exe

Steps:
  1. Open terminal in the ibt-portal folder
  2. Run: python build_exe.py
  3. Wait 2-3 minutes
  4. Find IBTPortal.exe inside the  dist/  folder
  5. Copy the entire  dist/IBTPortal/  folder anywhere
  6. Double-click IBTPortal.exe to launch

The .exe will work on any Windows PC — no Python needed!
"""

import subprocess
import sys
import os

print("\n🔧 IBT Portal EXE Builder")
print("=" * 40)

# Install PyInstaller if needed
print("\n[1/3] Installing PyInstaller...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])
print("      ✅ Done")

# Build the exe
print("\n[2/3] Building .exe (this takes 2-3 minutes)...")

base = os.path.dirname(os.path.abspath(__file__))

cmd = [
    "pyinstaller",
    "--noconfirm",
    "--onedir",                          # folder mode (faster startup than --onefile)
    "--windowed",                        # no black console window
    "--name", "IBTPortal",
    "--icon", "NONE",
    # Include all template and static folders
    "--add-data", f"{base}/templates{os.pathsep}templates",
    "--add-data", f"{base}/static{os.pathsep}static",
    "--add-data", f"{base}/data{os.pathsep}data",
    # Hidden imports Flask needs
    "--hidden-import", "flask",
    "--hidden-import", "flask_sqlalchemy",
    "--hidden-import", "sqlalchemy",
    "--hidden-import", "werkzeug",
    "--hidden-import", "jinja2",
    "--hidden-import", "click",
    "--hidden-import", "itsdangerous",
    "launcher.py"
]

subprocess.check_call(cmd, cwd=base)

print("\n[3/3] Cleaning up...")

# Tell user where to find it
dist_path = os.path.join(base, "dist", "IBTPortal")
print(f"""
✅ BUILD COMPLETE!
{'='*40}
Your .exe is ready at:
  {dist_path}

To use it:
  1. Copy the entire "IBTPortal" folder to any location
     (Desktop, USB drive, school server, etc.)
  2. Double-click  IBTPortal.exe
  3. A small control window opens + browser launches
  4. The database.db file is saved next to the .exe
     so student data is preserved between sessions.

To share with school:
  • Copy the IBTPortal folder to each computer, OR
  • Put it on a shared network drive and
    use the START_PORTAL.bat for LAN access.
{'='*40}
""")
