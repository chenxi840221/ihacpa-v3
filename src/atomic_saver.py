#!/usr/bin/env python3
"""
Atomic Saver for IHACPA Python Package Review Automation
Provides atomic file operations for Excel files with backup and rollback capabilities
"""

import os
import shutil
import tempfile
import time
import fcntl
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

from excel_handler import ExcelHandler


class AtomicSaveError(Exception):
    """Custom exception for atomic save operations"""
    pass


class AtomicSaver:
    """
    Provides atomic save operations for Excel files with backup and rollback capabilities.
    Ensures data integrity through atomic file operations and comprehensive error handling.
    """
    
    def __init__(self, excel_handler: ExcelHandler, logger: logging.Logger):
        """Initialize AtomicSaver with Excel handler and logger"""
        self.excel_handler = excel_handler
        self.logger = logger
        self.backup_dir = Path("data/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Track current operation state
        self.current_backup: Optional[Path] = None
        self.temp_file: Optional[Path] = None
        self.lock_file: Optional[Path] = None
        
    @contextmanager
    def atomic_save_context(self, create_backup: bool = True):
        """
        Context manager for atomic save operations
        
        Args:
            create_backup: Whether to create a backup before saving
            
        Yields:
            Path to temporary file for safe operations
            
        Raises:
            AtomicSaveError: If save operation fails
        """
        temp_file = None
        backup_file = None
        lock_file = None
        
        try:
            # Create file lock to prevent concurrent access
            lock_file = self._acquire_file_lock()
            
            # Create backup if requested
            if create_backup:
                backup_file = self._create_backup()
                self.current_backup = backup_file
            
            # Create temporary file for atomic operations
            temp_file = self._create_temp_file()
            self.temp_file = temp_file
            
            self.logger.debug(f"Starting atomic save operation with temp file: {temp_file}")
            
            yield temp_file
            
            # If we reach here, operation was successful
            # Perform atomic rename
            self._atomic_rename(temp_file, self.excel_handler.file_path)
            
            self.logger.info("Atomic save operation completed successfully")
            
        except Exception as e:
            # Rollback on error
            self.logger.error(f"Atomic save operation failed: {e}")
            
            if backup_file and backup_file.exists():
                try:
                    self._rollback_from_backup(backup_file)
                    self.logger.info("Successfully rolled back to backup")
                except Exception as rollback_error:
                    self.logger.error(f"Rollback failed: {rollback_error}")
                    raise AtomicSaveError(f"Save failed and rollback failed: {rollback_error}")
            
            raise AtomicSaveError(f"Atomic save operation failed: {e}")
            
        finally:
            # Cleanup temporary files
            self._cleanup_temp_files(temp_file, lock_file)
            
            # Reset state
            self.current_backup = None
            self.temp_file = None
            self.lock_file = None
    
    async def save_batch_atomically(self, batch_data: List[Dict[str, Any]], 
                                  create_backup: bool = True) -> bool:
        """
        Save a batch of package updates atomically
        
        Args:
            batch_data: List of package update data
            create_backup: Whether to create backup before saving
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            with self.atomic_save_context(create_backup=create_backup) as temp_file:
                # Copy current Excel file to temp location
                shutil.copy2(self.excel_handler.file_path, temp_file)
                
                # Create temporary Excel handler for the temp file
                temp_excel = ExcelHandler(str(temp_file))
                if not temp_excel.load_workbook():
                    raise AtomicSaveError("Failed to load temporary Excel file")
                
                # Apply all batch updates to temp file
                for item in batch_data:
                    if item.get('status') == 'success':
                        package_data = item.get('package_data', {})
                        updates = item.get('result', {}).get('updates', {})
                        row_number = package_data.get('row_number')
                        
                        if row_number and updates:
                            temp_excel.update_package_data(row_number, updates)
                
                # Save the temporary Excel file
                if not temp_excel.save_workbook(backup=False):
                    raise AtomicSaveError("Failed to save temporary Excel file")
                
                # Close the temporary workbook
                temp_excel.close_workbook()
                
                # Validate the temp file before atomic rename
                if not self._validate_excel_file(temp_file):
                    raise AtomicSaveError("Temporary Excel file validation failed")
            
            # If we reach here, the context manager has successfully renamed the file
            # Reload the main Excel handler
            self.excel_handler.close_workbook()
            return self.excel_handler.load_workbook()
            
        except Exception as e:
            self.logger.error(f"Batch atomic save failed: {e}")
            return False
    
    async def save_with_retry(self, batch_data: List[Dict[str, Any]], 
                            max_retries: int = 3, delay: float = 1.0) -> bool:
        """
        Save with exponential backoff retry on failure
        
        Args:
            batch_data: Batch data to save
            max_retries: Maximum number of retry attempts
            delay: Initial delay between retries (seconds)
            
        Returns:
            True if save successful, False otherwise
        """
        for attempt in range(max_retries + 1):
            try:
                result = await self.save_batch_atomically(batch_data, create_backup=(attempt == 0))
                if result:
                    if attempt > 0:
                        self.logger.info(f"Save succeeded on attempt {attempt + 1}")
                    return True
                    
            except Exception as e:
                if attempt == max_retries:
                    self.logger.error(f"Save failed after {max_retries + 1} attempts: {e}")
                    return False
                
                retry_delay = delay * (2 ** attempt)  # Exponential backoff
                self.logger.warning(f"Save attempt {attempt + 1} failed: {e}. Retrying in {retry_delay:.1f}s")
                time.sleep(retry_delay)
        
        return False
    
    def restore_from_backup(self, backup_path: Optional[Path] = None) -> bool:
        """
        Restore Excel file from backup
        
        Args:
            backup_path: Specific backup file to restore from (None for latest)
            
        Returns:
            True if restore successful, False otherwise
        """
        try:
            if backup_path is None:
                backup_path = self._find_latest_backup()
            
            if not backup_path or not backup_path.exists():
                self.logger.error("No backup file available for restoration")
                return False
            
            # Validate backup file
            if not self._validate_excel_file(backup_path):
                self.logger.error(f"Backup file validation failed: {backup_path}")
                return False
            
            # Create current file backup before restoration
            current_backup = self._create_backup()
            
            try:
                # Restore from backup
                shutil.copy2(backup_path, self.excel_handler.file_path)
                
                # Reload Excel handler
                self.excel_handler.close_workbook()
                if self.excel_handler.load_workbook():
                    self.logger.info(f"Successfully restored from backup: {backup_path}")
                    return True
                else:
                    # Rollback if reload fails
                    shutil.copy2(current_backup, self.excel_handler.file_path)
                    self.logger.error("Failed to reload after restoration, rolled back")
                    return False
                    
            except Exception as e:
                # Rollback on error
                if current_backup and current_backup.exists():
                    shutil.copy2(current_backup, self.excel_handler.file_path)
                raise e
                
        except Exception as e:
            self.logger.error(f"Backup restoration failed: {e}")
            return False
    
    def list_available_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backup files
        
        Returns:
            List of backup file information
        """
        backups = []
        
        try:
            backup_files = list(self.backup_dir.glob("*.xlsx"))
            backup_files.extend(list(self.backup_dir.glob("*.backup_*.xlsx")))
            
            for backup_file in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    stat = backup_file.stat()
                    
                    backup_info = {
                        'file_path': str(backup_file),
                        'file_name': backup_file.name,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_mtime),
                        'is_valid': self._validate_excel_file(backup_file, quick_check=True)
                    }
                    
                    backups.append(backup_info)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to read backup info for {backup_file}: {e}")
                    continue
            
            return backups
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Clean up old backup files
        
        Args:
            keep_count: Number of recent backups to keep
            
        Returns:
            Number of backups removed
        """
        try:
            backups = self.list_available_backups()
            
            if len(backups) <= keep_count:
                return 0
            
            # Remove old backups
            removed_count = 0
            for backup in backups[keep_count:]:
                try:
                    Path(backup['file_path']).unlink()
                    removed_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to remove backup {backup['file_path']}: {e}")
            
            self.logger.info(f"Cleaned up {removed_count} old backup files")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}")
            return 0
    
    # Private helper methods
    
    def _acquire_file_lock(self) -> Path:
        """Acquire file lock to prevent concurrent access"""
        lock_file = Path(f"{self.excel_handler.file_path}.lock")
        
        try:
            # Create lock file
            with open(lock_file, 'w') as f:
                f.write(f"{os.getpid()}\n{datetime.now().isoformat()}\n")
            
            # Try to acquire exclusive lock (non-blocking)
            with open(lock_file, 'r') as f:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.lock_file = lock_file
                    return lock_file
                except BlockingIOError:
                    raise AtomicSaveError("File is locked by another process")
                    
        except Exception as e:
            if lock_file.exists():
                lock_file.unlink(missing_ok=True)
            raise AtomicSaveError(f"Failed to acquire file lock: {e}")
    
    def _create_backup(self) -> Path:
        """Create backup of current Excel file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{self.excel_handler.file_path.stem}.backup_{timestamp}.xlsx"
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(self.excel_handler.file_path, backup_path)
            self.logger.debug(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            raise AtomicSaveError(f"Failed to create backup: {e}")
    
    def _create_temp_file(self) -> Path:
        """Create temporary file for atomic operations"""
        try:
            # Create temp file in same directory as target file
            temp_dir = self.excel_handler.file_path.parent
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.xlsx.tmp',
                prefix='ihacpa_atomic_',
                dir=temp_dir
            )
            os.close(temp_fd)  # Close file descriptor, we just need the path
            
            return Path(temp_path)
            
        except Exception as e:
            raise AtomicSaveError(f"Failed to create temporary file: {e}")
    
    def _atomic_rename(self, source: Path, target: Path) -> None:
        """Perform atomic rename operation"""
        try:
            # On Windows, we need to remove target first for atomic rename
            if os.name == 'nt' and target.exists():
                # Create a temporary backup during rename
                temp_backup = target.with_suffix(target.suffix + '.atomic_backup')
                target.rename(temp_backup)
                
                try:
                    source.rename(target)
                    # Remove temporary backup on success
                    temp_backup.unlink(missing_ok=True)
                except Exception:
                    # Restore from temporary backup on failure
                    temp_backup.rename(target)
                    raise
            else:
                # Unix-like systems support atomic rename directly
                source.rename(target)
                
        except Exception as e:
            raise AtomicSaveError(f"Atomic rename failed: {e}")
    
    def _rollback_from_backup(self, backup_path: Path) -> None:
        """Rollback Excel file from backup"""
        try:
            if backup_path.exists():
                shutil.copy2(backup_path, self.excel_handler.file_path)
            else:
                raise AtomicSaveError("Backup file not found for rollback")
                
        except Exception as e:
            raise AtomicSaveError(f"Rollback operation failed: {e}")
    
    def _cleanup_temp_files(self, temp_file: Optional[Path], lock_file: Optional[Path]) -> None:
        """Clean up temporary files"""
        try:
            if temp_file and temp_file.exists():
                temp_file.unlink()
                
            if lock_file and lock_file.exists():
                lock_file.unlink()
                
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temporary files: {e}")
    
    def _validate_excel_file(self, file_path: Path, quick_check: bool = False) -> bool:
        """
        Validate Excel file integrity
        
        Args:
            file_path: Path to Excel file to validate
            quick_check: If True, perform only basic validation
            
        Returns:
            True if file is valid, False otherwise
        """
        try:
            if not file_path.exists():
                return False
            
            # Check file size
            if file_path.stat().st_size == 0:
                return False
            
            if quick_check:
                # Quick check: just verify it's a valid Excel file by extension and size
                return file_path.suffix.lower() in ['.xlsx', '.xls'] and file_path.stat().st_size > 1024
            
            # Full validation: try to load with openpyxl
            temp_handler = ExcelHandler(str(file_path))
            try:
                result = temp_handler.load_workbook()
                temp_handler.close_workbook()
                return result
            except Exception:
                return False
                
        except Exception as e:
            self.logger.warning(f"File validation failed for {file_path}: {e}")
            return False
    
    def _find_latest_backup(self) -> Optional[Path]:
        """Find the most recent backup file"""
        try:
            backups = self.list_available_backups()
            return Path(backups[0]['file_path']) if backups else None
        except Exception:
            return None