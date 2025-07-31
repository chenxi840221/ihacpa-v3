#!/usr/bin/env python3
"""
Checkpoint Manager for IHACPA Python Package Review Automation
Handles checkpoint creation, validation, and recovery operations
"""

import json
import os
import hashlib
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging


@dataclass
class CheckpointMetadata:
    """Metadata for checkpoint files"""
    timestamp: datetime
    checkpoint_id: str
    excel_file_path: str
    excel_file_hash: str
    excel_file_size: int
    total_packages: int
    completed_packages: int
    current_batch: int
    current_package: int
    batch_size: int
    strategy: str
    processing_statistics: Dict[str, Any]
    

@dataclass
class CheckpointValidation:
    """Results of checkpoint validation"""
    is_valid: bool
    excel_file_matches: bool
    metadata_valid: bool
    can_resume: bool
    issues: List[str]
    recommendations: List[str]


class CheckpointManager:
    """
    Manages checkpoint creation, validation, and recovery for batch processing.
    Provides atomic checkpoint operations with data integrity verification.
    """
    
    def __init__(self, checkpoint_dir: Path, excel_file_path: Path, logger: logging.Logger):
        """Initialize CheckpointManager"""
        self.checkpoint_dir = checkpoint_dir
        self.excel_file_path = excel_file_path
        self.logger = logger
        
        # Ensure checkpoint directory exists
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir = self.checkpoint_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # File patterns
        self.checkpoint_pattern = "checkpoint_{timestamp}_{id}.json"
        self.backup_pattern = "excel_backup_{timestamp}_{id}.xlsx"
    
    async def create_checkpoint(self, batch_state: Dict[str, Any], 
                              processing_config: Dict[str, Any]) -> Optional[str]:
        """
        Create a comprehensive checkpoint with data validation
        
        Args:
            batch_state: Current batch processing state
            processing_config: Batch processing configuration
            
        Returns:
            Checkpoint ID if successful, None if failed
        """
        try:
            timestamp = datetime.now()
            checkpoint_id = self._generate_checkpoint_id(timestamp)
            
            # Calculate Excel file hash for integrity checking
            excel_hash = await self._calculate_file_hash(self.excel_file_path)
            excel_size = self.excel_file_path.stat().st_size
            
            # Create checkpoint metadata
            metadata = CheckpointMetadata(
                timestamp=timestamp,
                checkpoint_id=checkpoint_id,
                excel_file_path=str(self.excel_file_path),
                excel_file_hash=excel_hash,
                excel_file_size=excel_size,
                total_packages=batch_state.get('total_packages', 0),
                completed_packages=batch_state.get('completed_packages', 0),
                current_batch=batch_state.get('current_batch', 0),
                current_package=batch_state.get('current_package', 0),
                batch_size=processing_config.get('batch_size', 10),
                strategy=processing_config.get('strategy', 'fixed-size'),
                processing_statistics=batch_state.get('processing_statistics', {})
            )
            
            # Create checkpoint data structure
            checkpoint_data = {
                'version': '1.0',
                'metadata': asdict(metadata),
                'batch_state': batch_state,
                'processing_config': processing_config,
                'system_info': {
                    'created_by': 'IHACPA BatchController',
                    'python_version': os.sys.version,
                    'platform': os.name
                }
            }
            
            # Write checkpoint file atomically
            checkpoint_file = self.checkpoint_dir / self.checkpoint_pattern.format(
                timestamp=timestamp.strftime('%Y%m%d_%H%M%S'),
                id=checkpoint_id[:8]
            )
            
            if await self._write_checkpoint_file(checkpoint_file, checkpoint_data):
                # Create Excel backup
                backup_file = self.backup_dir / self.backup_pattern.format(
                    timestamp=timestamp.strftime('%Y%m%d_%H%M%S'),
                    id=checkpoint_id[:8]
                )
                
                if await self._create_excel_backup(backup_file):
                    self.logger.info(f"Checkpoint created successfully: {checkpoint_id}")
                    return checkpoint_id
                else:
                    # Clean up checkpoint if backup failed
                    checkpoint_file.unlink(missing_ok=True)
                    self.logger.error("Failed to create Excel backup, checkpoint rolled back")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to create checkpoint: {e}")
            return None
    
    async def validate_checkpoint(self, checkpoint_id: str) -> CheckpointValidation:
        """
        Validate a checkpoint for integrity and resumability
        
        Args:
            checkpoint_id: ID of checkpoint to validate
            
        Returns:
            CheckpointValidation with detailed validation results
        """
        validation = CheckpointValidation(
            is_valid=False,
            excel_file_matches=False,
            metadata_valid=False,
            can_resume=False,
            issues=[],
            recommendations=[]
        )
        
        try:
            # Find checkpoint file
            checkpoint_file = self._find_checkpoint_file(checkpoint_id)
            if not checkpoint_file:
                validation.issues.append(f"Checkpoint file not found for ID: {checkpoint_id}")
                return validation
            
            # Load checkpoint data
            checkpoint_data = await self._load_checkpoint_file(checkpoint_file)
            if not checkpoint_data:
                validation.issues.append("Failed to load checkpoint data")
                return validation
            
            # Validate metadata structure
            metadata = checkpoint_data.get('metadata', {})
            if not self._validate_metadata_structure(metadata):
                validation.issues.append("Invalid checkpoint metadata structure")
                return validation
            
            validation.metadata_valid = True
            
            # Check Excel file integrity
            current_excel_hash = await self._calculate_file_hash(self.excel_file_path)
            expected_hash = metadata.get('excel_file_hash')
            
            if current_excel_hash == expected_hash:
                validation.excel_file_matches = True
            else:
                validation.issues.append("Excel file has been modified since checkpoint")
                validation.recommendations.append("Consider using backup Excel file or starting fresh")
            
            # Check file size consistency
            current_size = self.excel_file_path.stat().st_size
            expected_size = metadata.get('excel_file_size', 0)
            
            if abs(current_size - expected_size) > 1024:  # 1KB tolerance
                validation.issues.append(f"Excel file size changed: {expected_size} -> {current_size}")
            
            # Check if backup file exists
            backup_file = self._find_backup_file(checkpoint_id)
            if not backup_file:
                validation.issues.append("Excel backup file not found")
                validation.recommendations.append("Backup file missing, recovery options limited")
            
            # Determine if checkpoint can be used for resuming
            validation.can_resume = (
                validation.metadata_valid and 
                (validation.excel_file_matches or backup_file is not None)
            )
            
            validation.is_valid = validation.metadata_valid and len(validation.issues) == 0
            
            if validation.can_resume:
                validation.recommendations.append("Checkpoint is suitable for resuming processing")
            elif validation.excel_file_matches:
                validation.recommendations.append("Excel file matches, safe to resume")
            elif backup_file:
                validation.recommendations.append("Use backup file to restore and resume")
            
            return validation
            
        except Exception as e:
            validation.issues.append(f"Validation error: {e}")
            self.logger.error(f"Checkpoint validation failed: {e}")
            return validation
    
    async def restore_from_checkpoint(self, checkpoint_id: str, 
                                    force_restore: bool = False) -> Optional[Dict[str, Any]]:
        """
        Restore processing state from checkpoint
        
        Args:
            checkpoint_id: ID of checkpoint to restore from
            force_restore: Skip validation and force restoration
            
        Returns:
            Restored batch state and config, None if failed
        """
        try:
            if not force_restore:
                validation = await self.validate_checkpoint(checkpoint_id)
                if not validation.can_resume:
                    self.logger.error(f"Checkpoint {checkpoint_id} is not suitable for restoration")
                    self.logger.error(f"Issues: {', '.join(validation.issues)}")
                    return None
            
            # Load checkpoint
            checkpoint_file = self._find_checkpoint_file(checkpoint_id)
            checkpoint_data = await self._load_checkpoint_file(checkpoint_file)
            
            if not checkpoint_data:
                self.logger.error(f"Failed to load checkpoint data for {checkpoint_id}")
                return None
            
            # Restore Excel file if needed
            if not force_restore:
                validation = await self.validate_checkpoint(checkpoint_id)
                if not validation.excel_file_matches:
                    backup_file = self._find_backup_file(checkpoint_id)
                    if backup_file:
                        self.logger.info("Restoring Excel file from backup")
                        shutil.copy2(backup_file, self.excel_file_path)
                    else:
                        self.logger.warning("Excel file mismatch and no backup available")
            
            # Extract state and config
            restored_data = {
                'batch_state': checkpoint_data.get('batch_state', {}),
                'processing_config': checkpoint_data.get('processing_config', {}),
                'metadata': checkpoint_data.get('metadata', {}),
                'restored_from': checkpoint_id,
                'restored_at': datetime.now()
            }
            
            self.logger.info(f"Successfully restored from checkpoint: {checkpoint_id}")
            return restored_data
            
        except Exception as e:
            self.logger.error(f"Failed to restore from checkpoint {checkpoint_id}: {e}")
            return None
    
    def list_available_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List all available checkpoints with metadata
        
        Returns:
            List of checkpoint information dictionaries
        """
        checkpoints = []
        
        try:
            # Find all checkpoint files
            checkpoint_files = list(self.checkpoint_dir.glob("checkpoint_*.json"))
            
            for checkpoint_file in sorted(checkpoint_files, key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    # Extract checkpoint ID from filename
                    checkpoint_id = self._extract_checkpoint_id(checkpoint_file)
                    
                    # Load basic metadata
                    with open(checkpoint_file, 'r') as f:
                        data = json.load(f)
                        metadata = data.get('metadata', {})
                    
                    checkpoint_info = {
                        'checkpoint_id': checkpoint_id,
                        'file_path': str(checkpoint_file),
                        'created': metadata.get('timestamp'),
                        'total_packages': metadata.get('total_packages', 0),
                        'completed_packages': metadata.get('completed_packages', 0),
                        'current_batch': metadata.get('current_batch', 0),
                        'batch_size': metadata.get('batch_size', 0),
                        'strategy': metadata.get('strategy', 'unknown'),
                        'file_size': checkpoint_file.stat().st_size,
                        'has_backup': self._find_backup_file(checkpoint_id) is not None
                    }
                    
                    checkpoints.append(checkpoint_info)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to read checkpoint {checkpoint_file}: {e}")
                    continue
            
            return checkpoints
            
        except Exception as e:
            self.logger.error(f"Failed to list checkpoints: {e}")
            return []
    
    async def cleanup_old_checkpoints(self, keep_count: int = 10) -> int:
        """
        Clean up old checkpoint files, keeping only the most recent ones
        
        Args:
            keep_count: Number of recent checkpoints to keep
            
        Returns:
            Number of checkpoints removed
        """
        try:
            checkpoints = self.list_available_checkpoints()
            
            if len(checkpoints) <= keep_count:
                return 0
            
            # Sort by creation time (most recent first)
            checkpoints.sort(key=lambda x: x.get('created', ''), reverse=True)
            
            # Remove old checkpoints
            removed_count = 0
            for checkpoint in checkpoints[keep_count:]:
                checkpoint_id = checkpoint['checkpoint_id']
                
                # Remove checkpoint file
                checkpoint_file = self._find_checkpoint_file(checkpoint_id)
                if checkpoint_file and checkpoint_file.exists():
                    checkpoint_file.unlink()
                    removed_count += 1
                
                # Remove backup file
                backup_file = self._find_backup_file(checkpoint_id)
                if backup_file and backup_file.exists():
                    backup_file.unlink()
            
            self.logger.info(f"Cleaned up {removed_count} old checkpoints")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup checkpoints: {e}")
            return 0
    
    async def create_emergency_checkpoint(self, batch_state: Dict[str, Any]) -> Optional[str]:
        """
        Create emergency checkpoint during error conditions
        
        Args:
            batch_state: Current processing state to save
            
        Returns:
            Emergency checkpoint ID if successful
        """
        try:
            self.logger.warning("Creating emergency checkpoint due to processing error")
            
            # Create minimal config for emergency checkpoint
            emergency_config = {
                'batch_size': batch_state.get('current_batch_size', 10),
                'strategy': 'emergency',
                'emergency': True,
                'created_reason': 'processing_error'
            }
            
            checkpoint_id = await self.create_checkpoint(batch_state, emergency_config)
            
            if checkpoint_id:
                self.logger.info(f"Emergency checkpoint created: {checkpoint_id}")
            
            return checkpoint_id
            
        except Exception as e:
            self.logger.error(f"Failed to create emergency checkpoint: {e}")
            return None
    
    # Private helper methods
    
    def _generate_checkpoint_id(self, timestamp: datetime) -> str:
        """Generate unique checkpoint ID"""
        base_string = f"{timestamp.isoformat()}_{self.excel_file_path.name}"
        return hashlib.md5(base_string.encode()).hexdigest()
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file for integrity checking"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate file hash: {e}")
            return ""
    
    async def _write_checkpoint_file(self, checkpoint_file: Path, 
                                   checkpoint_data: Dict[str, Any]) -> bool:
        """Write checkpoint file atomically"""
        try:
            # Write to temporary file first
            temp_file = checkpoint_file.with_suffix('.tmp')
            
            with open(temp_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2, default=str)
            
            # Atomic rename
            temp_file.rename(checkpoint_file)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write checkpoint file: {e}")
            return False
    
    async def _create_excel_backup(self, backup_file: Path) -> bool:
        """Create backup of Excel file"""
        try:
            shutil.copy2(self.excel_file_path, backup_file)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create Excel backup: {e}")
            return False
    
    async def _load_checkpoint_file(self, checkpoint_file: Path) -> Optional[Dict[str, Any]]:
        """Load checkpoint data from file"""
        try:
            with open(checkpoint_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint file: {e}")
            return None
    
    def _find_checkpoint_file(self, checkpoint_id: str) -> Optional[Path]:
        """Find checkpoint file by ID"""
        try:
            # Try to find by ID in filename
            pattern = f"*_{checkpoint_id[:8]}.json"
            matches = list(self.checkpoint_dir.glob(pattern))
            
            if matches:
                return matches[0]
            
            # Fallback: search in file contents
            for checkpoint_file in self.checkpoint_dir.glob("checkpoint_*.json"):
                try:
                    with open(checkpoint_file, 'r') as f:
                        data = json.load(f)
                        if data.get('metadata', {}).get('checkpoint_id') == checkpoint_id:
                            return checkpoint_file
                except:
                    continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to find checkpoint file: {e}")
            return None
    
    def _find_backup_file(self, checkpoint_id: str) -> Optional[Path]:
        """Find backup file by checkpoint ID"""
        try:
            pattern = f"*_{checkpoint_id[:8]}.xlsx"
            matches = list(self.backup_dir.glob(pattern))
            return matches[0] if matches else None
        except Exception as e:
            self.logger.error(f"Failed to find backup file: {e}")
            return None
    
    def _extract_checkpoint_id(self, checkpoint_file: Path) -> str:
        """Extract checkpoint ID from filename or file contents"""
        try:
            # Try to extract from filename first
            parts = checkpoint_file.stem.split('_')
            if len(parts) >= 3:
                return parts[-1]
            
            # Fallback to file contents
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)
                return data.get('metadata', {}).get('checkpoint_id', 'unknown')
        except:
            return 'unknown'
    
    def _validate_metadata_structure(self, metadata: Dict[str, Any]) -> bool:
        """Validate checkpoint metadata structure"""
        required_fields = [
            'timestamp', 'checkpoint_id', 'excel_file_path', 'excel_file_hash',
            'total_packages', 'completed_packages', 'current_batch', 'batch_size'
        ]
        
        return all(field in metadata for field in required_fields)