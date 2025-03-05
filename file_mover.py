#!/usr/bin/env python3
import json
import os
import re
import shutil
import datetime
import time
import signal
import sys
from typing import Dict, Any, Optional, Pattern
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class FileMoverService:
    def __init__(self, config_path: str) -> None:
        """Initialize the file mover service with the given configuration file.

        Args:
            config_path: Path to the JSON configuration file
        """
        # Setup logging first so we can log any initialization errors
        self._setup_logging()
        
        try:
            self.config: Dict[str, Any] = self._load_config(config_path)
            self.source_folder: Path = Path(self.config["source_folder"])
            self.destination_parent: Path = Path(self.config["destination_parent_folder"])
            
            # Compile regex for date pattern (YYYY-MM-DD)
            # Make the pattern more specific to match valid dates
            self.date_pattern: Pattern[str] = re.compile(r'^(20\d{2}|19\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$')
            
            # Validate folders exist
            self._validate_folders()
            
            # Flag to control service loop
            self.running = True
            
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            raise

    def _setup_logging(self) -> None:
        """Set up logging configuration with rotation."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / "file_mover.log"
        
        # Set up a rotating file handler (10 MB max size, keep 5 backup files)
        handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5
        )
        
        console_handler = logging.StreamHandler()
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[handler, console_handler]
        )
        
        self.logger = logging.getLogger("FileMoverService")

    def _validate_folders(self) -> None:
        """Validate that source and destination folders exist."""
        if not self.source_folder.exists():
            self.logger.error(f"Source folder not found: {self.source_folder}")
            raise FileNotFoundError(f"Source folder not found: {self.source_folder}")
        
        if not self.destination_parent.exists():
            self.logger.error(f"Destination parent folder not found: {self.destination_parent}")
            raise FileNotFoundError(f"Destination parent folder not found: {self.destination_parent}")
        
        self.logger.info(f"Source folder: {self.source_folder}")
        self.logger.info(f"Destination parent folder: {self.destination_parent}")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file.
        
        Args:
            config_path: Path to the JSON configuration file
            
        Returns:
            Dictionary containing configuration settings
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.logger.info(f"Loaded configuration from {config_path}")
                return config
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            raise Exception(f"Invalid JSON in configuration file: {e}")
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {config_path}")
            raise Exception(f"Configuration file not found: {config_path}")
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise Exception(f"Error loading configuration: {e}")

    def extract_address(self, filename: str) -> Optional[str]:
        """Extract address from filename.
        
        Args:
            filename: The filename to parse
            
        Returns:
            The extracted address or None if not found
        """
        try:
            # Handle empty filenames
            if not filename:
                return None
            
            # Remove file extension
            name_without_ext = os.path.splitext(filename)[0]
            
            # Split by " - " (space-dash-space) to properly separate parts
            parts = [part.strip() for part in name_without_ext.split(" - ")]
            
            # Filter out empty parts
            parts = [p for p in parts if p]
            
            if not parts:
                return None
            
            # Check if first part looks like a date (YYYY-MM-DD)
            date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
            
            if len(parts) >= 2 and date_pattern.match(parts[0]):
                # If first part is a date, return the second part as the address
                return parts[1]
            
            # If no date pattern or not enough parts, assume the first part is the address
            return parts[0]
        
        except Exception as e:
            self.logger.error(f"Error extracting address from {filename}: {e}")
            return None

    def find_matching_folder(self, address: str) -> Optional[Path]:
        """Find a matching folder based on address.
        
        Args:
            address: The address to match
            
        Returns:
            Path to the matching folder or None if not found
        """
        try:
            address_lower = address.lower()
            
            for folder in self.destination_parent.iterdir():
                if folder.is_dir():
                    folder_parts = folder.name.split('-')
                    if len(folder_parts) >= 2:
                        folder_address = folder_parts[1].strip().lower()
                        # Check if addresses match (allowing for some flexibility)
                        if folder_address in address_lower or address_lower in folder_address:
                            return folder
            
            return None
        except Exception as e:
            self.logger.error(f"Error finding matching folder for address '{address}': {e}")
            return None

    def ensure_date_in_filename(self, filename: str) -> str:
        """Ensure filename has a date prefix (YYYY-MM-DD).
        
        Args:
            filename: The original filename
            
        Returns:
            Filename with date prefix
        """
        try:
            # Simple date pattern check
            date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}')
            
            # Check if filename already starts with a date
            if date_pattern.match(filename):
                return filename
            
            # Add today's date to the filename
            today = datetime.date.today().strftime("%Y-%m-%d")
            return f"{today} - {filename}"
        except Exception as e:
            self.logger.error(f"Error ensuring date in filename {filename}: {e}")
            return filename  # Return original filename if there's an error

    def handle_duplicate_file(self, destination_path: Path) -> Path:
        """Handle duplicate files by adding a suffix.
        
        Args:
            destination_path: The original destination path
            
        Returns:
            A new destination path that doesn't conflict
        """
        if not destination_path.exists():
            return destination_path
        
        base_name = destination_path.stem
        extension = destination_path.suffix
        parent_dir = destination_path.parent
        
        counter = 1
        while True:
            new_path = parent_dir / f"{base_name}_{counter}{extension}"
            if not new_path.exists():
                return new_path
            counter += 1

    def move_file(self, file_path: Path, folder_lookup: Dict[str, Path]) -> None:
        """Move a file to the appropriate destination subfolder.
        
        Args:
            file_path: Path to the file to be moved
            folder_lookup: Dictionary mapping addresses to folder paths
        """
        try:
            if not file_path.exists():
                self.logger.warning(f"File no longer exists: {file_path}")
                return
                
            original_filename = file_path.name
            
            # Extract address from filename
            address = self.extract_address(original_filename)
            
            if not address:
                self.logger.warning(f"Could not extract address from {original_filename}, skipping")
                return
            
            # Find matching folder using the lookup dictionary
            destination_folder = self._find_matching_folder_from_lookup(address, folder_lookup)
            
            if not destination_folder:
                self.logger.info(f"No matching folder found for address '{address}', skipping file {original_filename}")
                return
            
            # Ensure filename has date
            new_filename = self.ensure_date_in_filename(original_filename)
            
            # Determine the appropriate subfolder
            if "Banks Fee Letter".lower() in original_filename.lower():
                subfolder_name = "Contracts"
                final_destination = destination_folder / subfolder_name
                final_destination.mkdir(exist_ok=True)
            else:
                # Default to Correspondence folder
                correspondence_folder = destination_folder / "Correspondence"
                correspondence_folder.mkdir(exist_ok=True)
                
                # Create date subfolder within Correspondence
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                date_subfolder = correspondence_folder / today_str
                date_subfolder.mkdir(exist_ok=True)
                
                final_destination = date_subfolder
            
            # Create destination path
            destination_path = final_destination / new_filename
            
            # Handle duplicate files
            if destination_path.exists():
                self.logger.info(f"File already exists at {destination_path}")
                destination_path = self.handle_duplicate_file(destination_path)
                self.logger.info(f"Using new path: {destination_path}")
            
            # Move the file
            try:
                shutil.move(str(file_path), str(destination_path))
                self.logger.info(f"Moved {original_filename} to {destination_path}")
            except PermissionError:
                self.logger.warning(f"Permission denied when moving {original_filename}. Waiting and retrying...")
                time.sleep(1)  # Wait a second and try again
                shutil.move(str(file_path), str(destination_path))
                self.logger.info(f"Successfully moved {original_filename} after retry")
            
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")

    def process_files(self) -> None:
        """Process all files in the source folder."""
        try:
            self.logger.info(f"Starting to process files in {self.source_folder}")
            
            # Build folder lookup dictionary once per polling interval
            folder_lookup = self._build_folder_lookup()
            
            # Get list of files first to avoid modification during iteration
            files_to_process = [f for f in self.source_folder.iterdir() if f.is_file()]
            
            if not files_to_process:
                self.logger.info("No files found to process")
                return
                
            self.logger.info(f"Found {len(files_to_process)} files to process")
            
            for file_path in files_to_process:
                try:
                    self.move_file(file_path, folder_lookup)
                except Exception as e:
                    self.logger.error(f"Error moving file {file_path}: {e}")
                    # Continue with next file
            
            self.logger.info("Finished processing files")
            
        except Exception as e:
            self.logger.error(f"Error in process_files: {e}")

    def _build_folder_lookup(self) -> Dict[str, Path]:
        """Build a lookup dictionary for efficient folder matching.
        
        Returns:
            Dictionary mapping lowercase address substrings to folder paths
        """
        folder_lookup: Dict[str, Path] = {}
        
        try:
            # Count the folders for logging
            folder_count = 0
            
            for folder in self.destination_parent.iterdir():
                if folder.is_dir():
                    folder_parts = folder.name.split('-')
                    if len(folder_parts) >= 2:
                        folder_address = folder_parts[1].strip().lower()
                        folder_lookup[folder_address] = folder
                        folder_count += 1
            
            self.logger.info(f"Built folder lookup with {folder_count} folders")
            return folder_lookup
            
        except Exception as e:
            self.logger.error(f"Error building folder lookup: {e}")
            return {}

    def _find_matching_folder_from_lookup(self, address: str, folder_lookup: Dict[str, Path]) -> Optional[Path]:
        """Find a matching folder using the lookup dictionary.
        
        Args:
            address: The address to match
            folder_lookup: Dictionary mapping addresses to folder paths
            
        Returns:
            Path to the matching folder or None if not found
        """
        try:
            address_lower = address.lower()
            
            # First try exact match
            if address_lower in folder_lookup:
                return folder_lookup[address_lower]
            
            # Then try partial matches
            for folder_address, folder_path in folder_lookup.items():
                if folder_address in address_lower or address_lower in folder_address:
                    return folder_path
            
            return None
        except Exception as e:
            self.logger.error(f"Error finding matching folder for address '{address}': {e}")
            return None

    def run_service_loop(self, interval_seconds: int = 60) -> None:
        """Run the file mover service in a continuous loop.
        
        Args:
            interval_seconds: Time in seconds between processing cycles
        """
        self.logger.info(f"Starting file mover service loop with {interval_seconds} second interval")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        try:
            while self.running:
                start_time = time.time()
                
                try:
                    self.process_files()
                except Exception as e:
                    self.logger.error(f"Error in processing cycle: {e}")
                
                # Calculate time to sleep
                elapsed = time.time() - start_time
                sleep_time = max(0, interval_seconds - elapsed)
                
                if sleep_time > 0:
                    self.logger.debug(f"Sleeping for {sleep_time:.1f} seconds until next cycle")
                    # Sleep in small increments to allow for responsive shutdown
                    for _ in range(int(sleep_time)):
                        if not self.running:
                            break
                        time.sleep(1)
                    # Sleep any remaining fraction of a second
                    if self.running and sleep_time % 1 > 0:
                        time.sleep(sleep_time % 1)
            
            self.logger.info("Service loop stopped gracefully")
            
        except Exception as e:
            self.logger.error(f"Unexpected error in service loop: {e}")
            raise

    def _handle_shutdown(self, signum: int, frame: Optional[Any]) -> None:
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False


def run_service(config_path: str = "config.json") -> None:
    """Run the file mover service with the given configuration.
    
    Args:
        config_path: Path to the configuration file
    """
    try:
        service = FileMoverService(config_path)
        
        # Get polling interval from config or use default
        interval_seconds = service.config.get("polling_interval_seconds", 60)
        
        service.run_service_loop(interval_seconds)
    except Exception as e:
        print(f"Error running service: {e}")
        logging.error(f"Error running service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="File Mover Service")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")
    
    args = parser.parse_args()
    
    run_service(args.config) 