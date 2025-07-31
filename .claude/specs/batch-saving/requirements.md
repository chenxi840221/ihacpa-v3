# Requirements Document

## Introduction

The batch-saving feature enhances the IHACPA Python Package Review Automation system by implementing efficient batch processing for Excel file operations. Currently, the system processes 486 packages individually and saves changes to the Excel file after each package update, which can be inefficient and prone to data loss during long-running scans. This feature will introduce intelligent batching, intermediate checkpointing, and optimized I/O operations to improve reliability, performance, and user experience.

## Alignment with Product Vision

This feature directly supports the IHACPA product vision by:
- **Improving Reliability**: Reduces risk of data loss during long vulnerability scans of 486 packages
- **Enhancing Performance**: Optimizes Excel I/O operations through batching, reducing processing time
- **Supporting Scale**: Enables efficient processing of larger package sets while maintaining system responsiveness
- **Maintaining Data Integrity**: Provides checkpointing and recovery mechanisms for interrupted scans
- **User Experience**: Provides better progress visibility and recovery options for security analysts

## Requirements

### Requirement 1: Batch Processing for Excel Updates

**User Story:** As a security analyst, I want the system to process packages in configurable batches and save Excel updates efficiently, so that I can reliably scan large package sets without data loss or performance degradation.

#### Acceptance Criteria

1. WHEN a scan processes packages THEN the system SHALL group packages into configurable batches (default: 10 packages per batch)
2. WHEN a batch is completed THEN the system SHALL save all batch updates to Excel in a single I/O operation
3. IF a batch fails during processing THEN the system SHALL save completed packages from the batch and continue with the next batch
4. WHEN batch size is configured THEN the system SHALL validate the batch size is between 1 and 100 packages
5. WHEN memory usage exceeds threshold THEN the system SHALL automatically reduce batch size and save current progress

### Requirement 2: Intermediate Checkpointing

**User Story:** As a security analyst, I want the system to create intermediate checkpoints during long scans, so that I can resume processing from the last checkpoint if the scan is interrupted.

#### Acceptance Criteria

1. WHEN processing batches THEN the system SHALL create checkpoint files every 5 completed batches
2. WHEN a checkpoint is created THEN the system SHALL save package processing state, progress metadata, and Excel backup
3. IF the system is interrupted THEN the system SHALL detect existing checkpoints on restart
4. WHEN resuming from checkpoint THEN the system SHALL skip already processed packages and continue from the checkpoint position
5. WHEN a scan completes successfully THEN the system SHALL clean up intermediate checkpoint files

### Requirement 3: User-Controlled Start and Resume Points

**User Story:** As a security analyst, I want explicit control over where batch processing starts and resumes, so that I can easily restart from any point, skip completed sections, or resume interrupted scans without confusion.

#### Acceptance Criteria

1. WHEN starting a scan THEN the system SHALL provide CLI options: `--start-fresh`, `--resume-auto`, `--resume-from-package N`, `--resume-from-batch N`
2. WHEN `--start-fresh` is specified THEN the system SHALL ignore existing checkpoints and start from package 1
3. WHEN `--resume-auto` is specified THEN the system SHALL automatically resume from the latest checkpoint if available
4. WHEN `--resume-from-package N` is specified THEN the system SHALL start processing from package N and create new checkpoints
5. WHEN `--resume-from-batch N` is specified THEN the system SHALL start processing from the beginning of batch N
6. WHEN no resume option is specified AND checkpoints exist THEN the system SHALL prompt user to choose: "Start fresh", "Resume from checkpoint", or "Custom start point"
7. WHEN resuming from a custom point THEN the system SHALL validate the Excel file state matches the expected state for that position
8. IF validation fails THEN the system SHALL display current vs expected state and offer options: "Force continue", "Start fresh", or "Cancel"

### Requirement 4: Progress Persistence and Recovery

**User Story:** As a security analyst, I want comprehensive recovery options when scans are interrupted, so that I can always get back to a working state regardless of how the interruption occurred.

#### Acceptance Criteria

1. WHEN a scan is interrupted THEN the system SHALL save the current progress state including: last completed package, current batch number, and processing statistics
2. WHEN resuming a scan THEN the system SHALL validate the Excel file matches the expected checkpoint state
3. IF the Excel file has been modified since checkpoint THEN the system SHALL show a diff summary and offer merge options: "Use checkpoint version", "Use current version", or "Manual merge"
4. WHEN resuming THEN the system SHALL display detailed progress summary: completed packages, remaining packages, estimated time, and processing statistics
5. WHEN recovery is not possible THEN the system SHALL provide specific error details and suggest manual resolution steps
6. WHEN multiple checkpoint files exist THEN the system SHALL list available checkpoints with timestamps and allow user selection

### Requirement 5: Configurable Batch Strategies

**User Story:** As a system administrator, I want to configure different batching strategies for different environments, so that I can optimize performance for development, testing, and production scenarios.

#### Acceptance Criteria

1. WHEN configuring batch strategy THEN the system SHALL support "fixed-size", "memory-adaptive", and "time-based" strategies
2. WHEN using fixed-size strategy THEN the system SHALL process exactly N packages per batch
3. WHEN using memory-adaptive strategy THEN the system SHALL adjust batch size based on memory usage (target: <80% memory usage)
4. WHEN using time-based strategy THEN the system SHALL save progress every T minutes regardless of batch completion
5. WHEN strategy parameters are invalid THEN the system SHALL use default fixed-size strategy with warning

### Requirement 6: Atomic Batch Operations

**User Story:** As a security analyst, I want each batch to be saved atomically, so that I never end up with partially saved or corrupted Excel data.

#### Acceptance Criteria

1. WHEN saving a batch THEN the system SHALL use atomic file operations (write to temp file, then rename)
2. WHEN a save operation fails THEN the system SHALL preserve the previous valid Excel state
3. IF Excel file becomes corrupted THEN the system SHALL restore from the most recent valid backup
4. WHEN concurrent access is detected THEN the system SHALL use file locking to prevent data corruption
5. WHEN atomic operation fails THEN the system SHALL log detailed error information and provide recovery options

### Requirement 7: Batch Performance Optimization

**User Story:** As a security analyst, I want batch operations to be optimized for Excel I/O performance, so that large scans complete as quickly as possible.

#### Acceptance Criteria

1. WHEN processing batches THEN the system SHALL buffer Excel cell updates in memory before writing
2. WHEN saving batches THEN the system SHALL optimize openpyxl operations for bulk updates
3. WHEN multiple batches are pending THEN the system SHALL coalesce sequential writes when safe
4. WHEN Excel file size grows large THEN the system SHALL use streaming operations to maintain performance
5. WHEN batch operations complete THEN the system SHALL report timing metrics for performance monitoring

## Non-Functional Requirements

### Performance
- Batch operations SHALL complete 30-50% faster than individual package saves for typical 486-package scans
- Memory usage SHALL not exceed 1GB during batch processing regardless of batch size
- Excel file I/O operations SHALL use optimized bulk update patterns to minimize disk operations
- Checkpoint creation SHALL complete within 5 seconds for typical package datasets

### Security
- Checkpoint files SHALL be stored in secure temporary directories with appropriate file permissions
- Excel file backups SHALL maintain the same security permissions as the original file
- Recovery operations SHALL validate file integrity before proceeding with restoration
- Temporary files SHALL be securely deleted after successful completion

### Reliability
- Batch operations SHALL provide 99.9% success rate for individual batch saves
- System SHALL automatically recover from transient I/O errors with exponential backoff retry
- Checkpoint files SHALL include checksums to detect corruption
- Atomic operations SHALL guarantee either complete success or complete rollback with no partial states

### Usability
- Batch configuration SHALL be exposed through YAML configuration files with clear documentation
- Progress reporting SHALL show batch-level progress in addition to package-level progress
- Resume operations SHALL provide clear status information about what will be processed
- Error messages SHALL provide specific guidance for manual recovery when automatic recovery fails