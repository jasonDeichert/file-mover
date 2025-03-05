#!/usr/bin/env python3
import shutil
import tempfile
import unittest
import json
import datetime
from pathlib import Path
from file_mover import FileMoverService


class TestFileMoverService(unittest.TestCase):
    """Test cases for the FileMoverService."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create temporary directories for testing
        self.test_dir = Path(tempfile.mkdtemp())
        self.source_dir = self.test_dir / "source"
        self.dest_dir = self.test_dir / "destination"
        self.source_dir.mkdir()
        self.dest_dir.mkdir()
        
        # Create test config file
        self.config_path = self.test_dir / "test_config.json"
        config = {
            "source_folder": str(self.source_dir),
            "destination_parent_folder": str(self.dest_dir)
        }
        with open(self.config_path, 'w') as f:
            json.dump(config, f)
        
        # Create destination folders with the expected format
        self.folders = [
            "1001 - 123 Main St - Office Building",
            "1002 - 456 Oak Ave - Apartment Complex"
        ]
        for folder in self.folders:
            (self.dest_dir / folder).mkdir()
        
        # Today's date for testing
        self.today = datetime.date.today().strftime("%Y-%m-%d")

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.test_dir)

    def test_extract_address(self):
        """Test the address extraction functionality."""
        service = FileMoverService(str(self.config_path))
        
        # Test with date prefix
        self.assertEqual(service.extract_address("2023-01-01 - 123 Main St - Document.pdf"), "123 Main St")
        
        # Test without date prefix
        self.assertEqual(service.extract_address("456 Oak Ave - Report.docx"), "456 Oak Ave")
        

    def test_find_matching_folder(self):
        """Test the folder matching functionality."""
        service = FileMoverService(str(self.config_path))
        
        # Test exact match
        folder = service.find_matching_folder("123 Main St")
        self.assertIsNotNone(folder)
        if folder:  # Only access name if folder is not None
            self.assertEqual(folder.name, self.folders[0])
        
        # Test partial match
        folder = service.find_matching_folder("456 Oak")
        self.assertIsNotNone(folder)
        if folder:  # Only access name if folder is not None
            self.assertEqual(folder.name, self.folders[1])
        
        # Test no match
        self.assertIsNone(service.find_matching_folder("789 Pine Rd"))

    def test_ensure_date_in_filename(self):
        """Test adding date to filenames."""
        service = FileMoverService(str(self.config_path))
        
        # Test with existing date
        filename = "2023-01-01 - Document.pdf"
        self.assertEqual(service.ensure_date_in_filename(filename), filename)
        
        # Test without date
        filename = "Document.pdf"
        expected = f"{self.today} - {filename}"
        self.assertEqual(service.ensure_date_in_filename(filename), expected)

    def test_move_to_contracts(self):
        """Test moving a file to the Contracts folder."""
        # Create a test file with "Banks Fee Letter" in the name
        test_file = self.source_dir / "123 Main St - Banks Fee Letter.pdf"
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Run the service
        service = FileMoverService(str(self.config_path))
        service.process_files()
        
        # Check if file was moved to the Contracts folder
        expected_path = self.dest_dir / self.folders[0] / "Contracts" / f"{self.today} - 123 Main St - Banks Fee Letter.pdf"
        self.assertTrue(expected_path.exists(), f"File not found at {expected_path}")

    def test_move_to_correspondence(self):
        """Test moving a file to the Correspondence folder with date subfolder."""
        # Create a test file
        test_file = self.source_dir / "456 Oak Ave - Report.pdf"
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Run the service
        service = FileMoverService(str(self.config_path))
        service.process_files()
        
        # Check if file was moved to the Correspondence folder with today's date
        expected_path = self.dest_dir / self.folders[1] / "Correspondence" / self.today / f"{self.today} - 456 Oak Ave - Report.pdf"
        self.assertTrue(expected_path.exists(), f"File not found at {expected_path}")

    def test_handle_duplicate_files(self):
        """Test handling of duplicate files."""
        # Create a test file
        test_file = self.source_dir / "123 Main St - Document.pdf"
        with open(test_file, 'w') as f:
            f.write("Test content 1")
        
        # Run the service
        service = FileMoverService(str(self.config_path))
        service.process_files()
        
        # Create another file with the same name
        test_file = self.source_dir / "123 Main St - Document.pdf"
        with open(test_file, 'w') as f:
            f.write("Test content 2")
        
        # Run the service again
        service = FileMoverService(str(self.config_path))
        service.process_files()
        
        # Check if both files exist with different names
        base_path = self.dest_dir / self.folders[0] / "Correspondence" / self.today
        original_file = base_path / f"{self.today} - 123 Main St - Document.pdf"
        duplicate_file = base_path / f"{self.today} - 123 Main St - Document_1.pdf"
        
        self.assertTrue(original_file.exists(), f"Original file not found at {original_file}")
        self.assertTrue(duplicate_file.exists(), f"Duplicate file not found at {duplicate_file}")

    def test_extract_address_edge_cases(self):
        """Test address extraction with edge cases."""
        service = FileMoverService(str(self.config_path))
        
        # Test with no dashes
        self.assertEqual(service.extract_address("filename.pdf"), "filename")
        
        # Test with empty parts
        self.assertEqual(service.extract_address(" - .pdf"), None)
        
        # Test with multiple dashes but no date
        self.assertEqual(service.extract_address("address - part1 - part2.pdf"), "address")
        
        # Test with date-like string that isn't a valid date
        self.assertEqual(service.extract_address("9999-99-99 - address.pdf"), "address")
        
        # Test with completely empty string
        self.assertIsNone(service.extract_address(""))

    def test_no_matching_folder(self):
        """Test handling of files with no matching destination folder."""
        # Create a test file with an address that doesn't match any folder
        test_file = self.source_dir / "Nonexistent Address - Document.pdf"
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Run the service
        service = FileMoverService(str(self.config_path))
        service.process_files()
        
        # Verify the file wasn't moved (still in source directory)
        self.assertTrue(test_file.exists(), "File should not be moved when no matching folder is found")
        
        # Verify no files were created in destination folders
        for folder in self.folders:
            correspondence_path = self.dest_dir / folder / "Correspondence"
            if correspondence_path.exists():
                for date_folder in correspondence_path.iterdir():
                    self.assertEqual(len(list(date_folder.glob("*Nonexistent Address*"))), 0, 
                                    "No files with nonexistent address should be in destination")


if __name__ == "__main__":
    unittest.main() 