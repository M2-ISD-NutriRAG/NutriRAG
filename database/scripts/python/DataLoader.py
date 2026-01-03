"""
Data loading module for NutriRAG.

Provides the DataLoader class for downloading data from Google Drive and Kaggle.
"""

import logging
import os
import shutil
from typing import Optional

import gdown
import kagglehub

from config import CACHE_DIR, TEMP_KAGGLE_CACHE_DIR


class DataLoader:
    """Handles data loading from various sources (Google Drive, Kaggle)."""

    def __init__(self, cache_dir: str = CACHE_DIR):
        """
        Initialize DataLoader.

        Args:
            cache_dir: Directory to store downloaded files.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.logger.info(f"Cache directory: {self.cache_dir}")

    def load_from_drive(self, file_id: str, output_filename: str) -> str:
        """
        Download file from Google Drive.

        Args:
            file_id: Google Drive file ID
            output_filename: Name for the downloaded file

        Returns:
            Absolute path to the downloaded file
        """
        output_path = os.path.join(self.cache_dir, output_filename)
        url = f'https://drive.google.com/uc?id={file_id}'

        self.logger.info(f"Downloading {output_filename}...")

        if not os.path.exists(output_path):
            gdown.download(url, output_path, quiet=False, fuzzy=True)
            self.logger.info(f"✅ Downloaded: {output_path}")
        else:
            self.logger.info(f"File already exists: {output_filename}")

    def load_from_local(self, source_folder: str, filename: str) -> str:
        """
        Copy file from local source folder to cache.

        Args:
            source_folder: Path to the folder containing the file
            filename: Name of the file to copy

        Returns:
            Absolute path to the copied file in cache
        """
        source_path = os.path.join(source_folder, filename)
        output_path = os.path.join(self.cache_dir, filename)

        self.logger.info(f"Copying {filename} from {source_folder}...")

        if os.path.exists(source_path):
            if not os.path.exists(output_path) or os.path.getmtime(source_path) > os.path.getmtime(output_path):
                shutil.copy2(source_path, output_path)
                self.logger.info(f"✅ Copied: {output_path}")
            else:
                self.logger.info(f"File already exists and is up to date: {filename}")
        else:
            self.logger.warning(f"Source file not found: {source_path}")
            # If not found, check if it already exists in cache
            if os.path.exists(output_path):
                self.logger.info(f"Using existing file in cache: {filename}")
            else:
                raise FileNotFoundError(f"File not found in source or cache: {filename}")

        return os.path.abspath(output_path)
    
    def load_from_kaggle(self, dataset: str, output_filename: str) -> Optional[str]:
        """
        Download dataset from Kaggle.

        Args:
            dataset: Kaggle dataset identifier (e.g., 'owner/dataset-name')
            output_filename: Name for the output file

        Returns:
            Absolute path to the downloaded file, or None if download failed
        """
        final_file_path = os.path.join(self.cache_dir, output_filename)
        
        # Check if file already exists
        if os.path.exists(final_file_path):
            self.logger.info(f"File already exists: {output_filename}")
            return os.path.abspath(final_file_path)
        
        temp_cache_dir = TEMP_KAGGLE_CACHE_DIR
        os.environ['KAGGLEHUB_CACHE'] = temp_cache_dir

        self.logger.info(f"Downloading Kaggle dataset: {dataset}...")

        try:
            download_path = kagglehub.dataset_download(dataset)
            self.logger.info(f"Downloaded to: {download_path}")

            final_file_path = os.path.join(self.cache_dir, output_filename)

            files_found = os.listdir(download_path)

            if len(files_found) > 0:
                source_file = files_found[0]
                source_path = os.path.join(download_path, source_file)

                if os.path.exists(final_file_path):
                    os.remove(final_file_path)

                shutil.move(source_path, final_file_path)
                self.logger.info(f"✅ Saved as: {final_file_path}")
            else:
                self.logger.error("No files found in downloaded dataset")
                final_file_path = None

            # Cleanup
            if os.path.exists(temp_cache_dir):
                shutil.rmtree(temp_cache_dir)
                self.logger.info("Cleaned up temporary cache")

            return os.path.abspath(final_file_path) if final_file_path else None

        except Exception as e:
            self.logger.error(f"Error downloading from Kaggle: {e}")
            return None

    def close(self) -> None:
        """Clean up resources."""
        pass
