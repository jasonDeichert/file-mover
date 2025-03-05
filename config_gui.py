#!/usr/bin/env python3
import os
import sys
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, Callable, cast, TypeVar

# Add this type helper near the top of the file
T = TypeVar('T')

# Create a wrapper function for messagebox functions
def show_message_box(func: Callable[..., T], title: str, message: str) -> T:
    """Type-safe wrapper for messagebox functions."""
    return func(title=title, message=message)

class FileMoverConfigApp:
    def __init__(self, root: tk.Tk) -> None:
        """Initialize the configuration application.
        
        Args:
            root: The tkinter root window
        """
        self.root: tk.Tk = root
        self.root.title("File Mover Service Configuration")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        
        # Set icon if available
        try:
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                base_path: str = cast(str, sys._MEIPASS) #type: ignore
            else:
                # Running as script
                base_path: str = os.path.dirname(os.path.abspath(__file__))
                
            icon_path: str = os.path.join(base_path, "file_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path) #type: ignore
        except Exception:
            pass
        
        # Set config path to be in the same directory as the executable
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            exe_dir = os.path.dirname(sys.executable)
            self.config_path = os.path.join(exe_dir, "config.json")
        else:
            # Running as script
            self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        
        self.config: Dict[str, Any] = self.load_config()
        
        # Initialize UI variables
        self.source_var: tk.StringVar = tk.StringVar(value="")
        self.dest_var: tk.StringVar = tk.StringVar(value="")
        self.interval_var: tk.StringVar = tk.StringVar(value="")
        
        self.create_widgets()
        self.load_values_to_ui()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default.
        
        Returns:
            Dictionary containing configuration settings
        """
        default_config: Dict[str, Any] = {
            "source_folder": "",
            "destination_parent_folder": "",
            "polling_interval_seconds": 60
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            return default_config
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {e}") #type: ignore
            return default_config
    
    def load_values_to_ui(self) -> None:
        """Load configuration values into UI elements."""
        self.source_var.set(str(self.config.get("source_folder", "")))
        self.dest_var.set(str(self.config.get("destination_parent_folder", "")))
        self.interval_var.set(str(self.config.get("polling_interval_seconds", 60)))
    
    def save_config(self) -> bool:
        """Save configuration to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update config from UI
            self.config["source_folder"] = self.source_var.get()
            self.config["destination_parent_folder"] = self.dest_var.get()
            
            # Validate interval
            try:
                interval: int = int(self.interval_var.get())
                if interval <= 0:
                    messagebox.showerror("Error", "Polling interval must be a positive number") #type: ignore
                    return False
                self.config["polling_interval_seconds"] = interval
            except ValueError:
                messagebox.showerror("Error", "Polling interval must be a valid number") #type: ignore
                return False
            
            # Validate
            if not self.config["source_folder"] or not self.config["destination_parent_folder"]:
                messagebox.showerror("Error", "Source and destination folders must be specified") #type: ignore
                return False
                
            # Save to file
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
                
            messagebox.showinfo("Success", f"Configuration saved to {self.config_path}") #type: ignore
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}") #type: ignore
            return False
    
    def browse_folder(self, var: tk.StringVar) -> None:
        """Open folder browser dialog and update the variable.
        
        Args:
            var: The StringVar to update with the selected folder path
        """
        folder: str = filedialog.askdirectory()
        if folder:
            var.set(folder)
    
    def create_widgets(self) -> None:
        """Create the UI widgets."""
        main_frame: ttk.Frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label: ttk.Label = ttk.Label(
            main_frame, 
            text="File Mover Service Configuration", 
            font=("Helvetica", 14, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky="w")
        
        # Source folder
        source_label: ttk.Label = ttk.Label(main_frame, text="Source Folder:")
        source_label.grid(row=1, column=0, sticky="w", pady=5)
        
        source_entry: ttk.Entry = ttk.Entry(main_frame, textvariable=self.source_var, width=50)
        source_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        source_button: ttk.Button = ttk.Button(
            main_frame, 
            text="Browse...", 
            command=lambda: self.browse_folder(self.source_var)
        )
        source_button.grid(row=1, column=2, padx=5, pady=5)
        
        # Destination folder
        dest_label: ttk.Label = ttk.Label(main_frame, text="Destination Folder:")
        dest_label.grid(row=2, column=0, sticky="w", pady=5)
        
        dest_entry: ttk.Entry = ttk.Entry(main_frame, textvariable=self.dest_var, width=50)
        dest_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        dest_button: ttk.Button = ttk.Button(
            main_frame, 
            text="Browse...", 
            command=lambda: self.browse_folder(self.dest_var)
        )
        dest_button.grid(row=2, column=2, padx=5, pady=5)
        
        # Polling interval
        interval_label: ttk.Label = ttk.Label(main_frame, text="Polling Interval (seconds):")
        interval_label.grid(row=3, column=0, sticky="w", pady=5)
        
        interval_entry: ttk.Entry = ttk.Entry(main_frame, textvariable=self.interval_var, width=10)
        interval_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        
        # Folder structure explanation
        separator: ttk.Separator = ttk.Separator(main_frame, orient="horizontal")
        separator.grid(row=4, column=0, columnspan=3, sticky="ew", pady=15)
        
        info_title: ttk.Label = ttk.Label(
            main_frame, 
            text="Folder Structure Requirements:", 
            font=("Helvetica", 10, "bold")
        )
        info_title.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 5))
        
        info_text: str = (
            "• Destination folders must follow the format: 'NUMBER - ADDRESS - NAME'\n"
            "• Files will be matched to folders based on the ADDRESS part\n"
            "• Files with 'Banks Fee Letter' in the name will go to a 'Contracts' subfolder\n"
            "• Other files will go to 'Correspondence/YYYY-MM-DD' subfolders\n"
            "• Files without a date prefix will have today's date added automatically"
        )
        
        info_label: ttk.Label = ttk.Label(main_frame, text=info_text, justify="left")
        info_label.grid(row=6, column=0, columnspan=3, sticky="w", pady=5)
        
        # Buttons
        button_frame: ttk.Frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=3, pady=20)
        
        save_button: ttk.Button = ttk.Button(
            button_frame, 
            text="Save Configuration", 
            command=self.save_config
        )
        save_button.pack(side=tk.LEFT, padx=5)
        
        install_button: ttk.Button = ttk.Button(
            button_frame, 
            text="Install Service", 
            command=self.install_service
        )
        install_button.pack(side=tk.LEFT, padx=5)
        
        uninstall_button: ttk.Button = ttk.Button(
            button_frame, 
            text="Uninstall Service", 
            command=self.uninstall_service
        )
        uninstall_button.pack(side=tk.LEFT, padx=5)
        
        exit_button: ttk.Button = ttk.Button(
            button_frame, 
            text="Exit", 
            command=self.root.destroy
        )
        exit_button.pack(side=tk.LEFT, padx=5)
        
        # Make grid cells expandable
        main_frame.columnconfigure(1, weight=1)
    
    def install_service(self) -> None:
        """Install the Windows service."""
        if not self.save_config():
            return
            
        try:
            import subprocess
            
            # Get the path to the executable directory
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                exe_dir: str = os.path.dirname(sys.executable)
                
                # Use FileMoverService.exe, not the current executable (which is FileMoverConfig.exe)
                service_exe_path: str = os.path.join(exe_dir, "FileMoverService.exe")
                
                if not os.path.exists(service_exe_path):
                    messagebox.showerror("Error", "FileMoverService.exe not found in the same directory.") #type: ignore
                    return
            else:
                # Running as script - show error
                messagebox.showerror("Error", "Please run the compiled executable to install as a service") #type: ignore
                return
            
            # Use NSSM to install the service
            nssm_path: str = os.path.join(exe_dir, "nssm.exe")
            if not os.path.exists(nssm_path):
                messagebox.showerror("Error", "NSSM utility not found. Make sure it's included with the application.") #type: ignore
                return
                
            # Install the service
            cmd: list[str] = [
                nssm_path, "install", "FileMoverService", service_exe_path,
                "--config", self.config_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Set service to auto-start
                subprocess.run([nssm_path, "set", "FileMoverService", "Start", "SERVICE_AUTO_START"])
                
                # Set the working directory to the executable's directory
                subprocess.run([nssm_path, "set", "FileMoverService", "AppDirectory", exe_dir])
                
                # Set recovery options (restart on failure)
                subprocess.run([nssm_path, "set", "FileMoverService", "AppExit", "Default", "Restart"])
                
                # Set stdout and stderr to log files
                log_dir = os.path.join(exe_dir, "logs")
                os.makedirs(log_dir, exist_ok=True)
                
                subprocess.run([nssm_path, "set", "FileMoverService", "AppStdout", os.path.join(log_dir, "service_stdout.log")])
                subprocess.run([nssm_path, "set", "FileMoverService", "AppStderr", os.path.join(log_dir, "service_stderr.log")])
                
                messagebox.showinfo("Success", "Service installed successfully. You can start it from Windows Services.") #type: ignore
            else:
                messagebox.showerror("Error", f"Failed to install service: {result.stderr}") #type: ignore
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to install service: {e}") #type: ignore
    
    def uninstall_service(self) -> None:
        """Uninstall the Windows service."""
        try:
            import subprocess
            
            # Get the path to NSSM
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                exe_dir: str = os.path.dirname(sys.executable)
            else:
                # Running as script
                exe_dir: str = os.path.dirname(os.path.abspath(__file__))
                
            nssm_path: str = os.path.join(exe_dir, "nssm.exe")
            if not os.path.exists(nssm_path):
                messagebox.showerror("Error", "NSSM utility not found. Make sure it's included with the application.") #type: ignore
                return
            
            # Confirm uninstall
            if not messagebox.askyesno("Confirm", "Are you sure you want to uninstall the File Mover Service?"): #type: ignore
                return
                
            # Stop the service first
            subprocess.run([nssm_path, "stop", "FileMoverService"], capture_output=True)
            
            # Remove the service
            cmd: list[str] = [nssm_path, "remove", "FileMoverService", "confirm"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                messagebox.showinfo("Success", "Service uninstalled successfully.") #type: ignore
            else:
                messagebox.showerror("Error", f"Failed to uninstall service: {result.stderr}") #type: ignore
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to uninstall service: {e}") #type: ignore

def main() -> None:
    """Main entry point for the application."""
    root: tk.Tk = tk.Tk()
    _ = FileMoverConfigApp(root)  # Create app without storing reference
    root.mainloop()

if __name__ == "__main__":
    main() 