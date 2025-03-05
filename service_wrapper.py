import os
import sys
import signal
import logging
from typing import Any
from file_mover import FileMoverService

def run_as_service():
    """Run the file mover as a Windows service."""
    # Determine config path and base directory
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    # Now use command line args if provided
    if len(sys.argv) > 2 and sys.argv[1] == "--config":
        config_path = sys.argv[2]
    else:
        # Default to config.json in the base directory
        config_path = os.path.join(base_dir, "config.json")
    
    # Set up logging to file and console
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Create file handler
    file_handler = logging.FileHandler(os.path.join(log_dir, "service.log"))
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    logger = logging.getLogger("FileMoverService")
    logger.info(f"Starting File Mover Service with config: {config_path}")
    
    try:
        # Create and run the service
        service = FileMoverService(config_path)
        
        # Get polling interval from config
        interval_seconds = service.config.get("polling_interval_seconds", 60)
        
        # Set up signal handlers
        def handle_exit(signum: int, frame: Any) -> None:
            logger.info(f"Received signal {signum}, shutting down...")
            service.running = False
            
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
        
        # Run the service loop
        service.run_service_loop(interval_seconds)
        
    except Exception as e:
        logger.error(f"Service error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_as_service() 