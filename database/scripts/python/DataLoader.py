"""
Data loading module for NutriRAG.

Provides the DataLoader class for downloading data from Google Drive and Kaggle.
"""

import logging
import os
import shutil
from typing import Optional

from config import CACHE_DIR


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

    def close(self) -> None:
        """Clean up resources."""
        pass
