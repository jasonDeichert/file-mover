
import sys
import shutil
import subprocess
from pathlib import Path

def build_package():
    """Build the standalone package."""
    print("Building File Mover Service package...")
    
    # Create build directory
    build_dir = Path("build")
    dist_dir = Path("dist")
    
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
        
    build_dir.mkdir()
    
    # Check for icon file
    icon_file = Path("file_icon.ico")
    if not icon_file.exists():
        print("Warning: file_icon.ico not found, using default icon")
        # Create a simple icon or use a default one
    
    # Build the service executable
    print("Building service executable...")
    subprocess.run([
        "pyinstaller",
        "--clean",
        "--onefile",
        "--name", "FileMoverService",
        "--icon", "file_icon.ico" if icon_file.exists() else "NONE",
        "service_wrapper.py"
    ], check=True)
    
    # Build the config GUI
    print("Building configuration GUI...")
    subprocess.run([
        "pyinstaller",
        "--clean",
        "--onefile",
        "--name", "FileMoverConfig",
        "--icon", "file_icon.ico" if icon_file.exists() else "NONE",
        "--windowed",
        "config_gui.py"
    ], check=True)
    
    # Create the final package directory
    package_dir = Path("FileMoverService")
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir()
    
    # Copy executables
    shutil.copy(dist_dir / "FileMoverService.exe", package_dir)
    shutil.copy(dist_dir / "FileMoverConfig.exe", package_dir)
    
    # Download NSSM (Non-Sucking Service Manager)
    print("Downloading NSSM...")
    import urllib.request
    nssm_url = "https://nssm.cc/release/nssm-2.24.zip"
    nssm_zip = build_dir / "nssm.zip"
    
    urllib.request.urlretrieve(nssm_url, nssm_zip)
    
    # Extract NSSM
    import zipfile
    with zipfile.ZipFile(nssm_zip, 'r') as zip_ref:
        zip_ref.extractall(build_dir)
    
    # Copy NSSM executable (32 or 64 bit depending on system)
    if sys.maxsize > 2**32:
        nssm_exe = build_dir / "nssm-2.24" / "win64" / "nssm.exe"
    else:
        nssm_exe = build_dir / "nssm-2.24" / "win32" / "nssm.exe"
    
    shutil.copy(nssm_exe, package_dir)
    
    # Create default config
    import json
    default_config = {
        "source_folder": "",
        "destination_parent_folder": "",
        "polling_interval_seconds": 60
    }
    
    with open(package_dir / "config.json", 'w') as f:
        json.dump(default_config, f, indent=4)
    
    # Create logs directory
    (package_dir / "logs").mkdir()
    
    # Create README
    with open(package_dir / "README.txt", 'w') as f:
        f.write("""File Mover Service
=================

This package contains:

1. FileMoverConfig.exe - Configuration utility
2. FileMoverService.exe - The service executable
3. nssm.exe - Service manager utility

Installation:
1. Run FileMoverConfig.exe
2. Configure source and destination folders
3. Click "Install Service"
4. The service will be installed and set to start automatically

Uninstallation:
1. Run FileMoverConfig.exe
2. Click "Uninstall Service"

For more information, see the documentation.
""")
    
    # Create a ZIP archive
    shutil.make_archive("FileMoverService", 'zip', ".", "FileMoverService")
    
    print(f"Package created successfully: FileMoverService.zip")
    print(f"You can also find the unzipped files in the {package_dir} directory")

if __name__ == "__main__":
    build_package() 