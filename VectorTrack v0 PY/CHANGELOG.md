# Changelog

All notable changes to VectorTrack will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Enhanced logging system with improved categorization and readability
  - Added `[STATUS]` prefix for activity and idle state changes
  - Added `[SESSION]` prefix for session-related events
  - Added `[SETTINGS]` prefix for configuration changes
- Improved log file management
  - Switched to single log file with daily rotation
  - Added 7-day log retention policy
  - Implemented log compression for older files
- Enhanced session log dialog
  - Updated to work with new log file format
  - Improved log entry filtering and display
  - Added better error handling for log file access

## [0.0.1-alpha] - 2024-03-XX

### Added
- Initial application structure and core functionality
- Automatic Vectorworks process detection and monitoring
- File tracking system with multi-file support
- Activity monitoring with idle state detection
- Project-specific hourly rate configuration
- Session tracking and logging system
- Basic license management system
- Dark and light theme support
- Custom color theme options
- Professional PDF report generation
- Session summary table with real-time updates
- Application settings management
- Log viewing and export capabilities
- Modern UI with hard-edged design
- Status indicators (Active, Paused, Idle)
- Basic error handling and logging

### Technical
- PyQt6-based user interface implementation
- Windows process monitoring system
- Activity tracking with configurable idle timeout
- SQLite-based session storage
- PDF report generation using ReportLab
- Logging system with rotation and compression
- Settings persistence using QSettings

### Known Issues
- Window detection may need refinement for certain Vectorworks configurations
- Rate changes require pausing active tracking sessions
- Some UI elements may need additional polish
- Window detection might miss some edge cases
- No support for tracking and merging time across different versions of the same file

## [1.0.0] - 2024

### Added
- PDF report generation using ReportLab
  - Individual file reports with session history
  - Master project reports with aggregated data
  - Professional formatting with tables and styling
  - Project summaries and statistics
- Per-file rate configuration
  - Ability to set different rates for each file
  - Rate editing restrictions during active tracking
  - Rate changes only allowed when paused
- Enhanced session tracking
  - Detailed session history for each file
  - Chronological session logs
  - Improved time accuracy with seconds display
- Modern user interface improvements
  - Enhanced dark mode theme
  - Improved visual feedback
  - Better layout and spacing
  - Modern styling for all components
- Automatic file management
  - Improved file detection
  - Better handling of multiple open files
  - Enhanced file switching capabilities

### Changed
- Switched from JSON to PDF for report generation
- Updated rate input behavior for better control
- Improved time display format to include seconds
- Enhanced UI styling and visual feedback
- Modernized dark mode color scheme
- Optimized file tracking logic
- Updated project organization in reports

### Fixed
- Rate input field stability issues
- UI glitches in dark mode
- File tracking accuracy improvements
- Session history display issues
- Report generation reliability

## [0.9.0] - 2024 (Beta)

### Added
- Initial implementation of core features
- Basic time tracking functionality
- Simple report generation
- File detection and monitoring
- Activity tracking
- License management system
- Basic user interface

[1.0.0]: https://github.com/yourusername/vectortrack/releases/tag/v1.0.0
[0.9.0]: https://github.com/yourusername/vectortrack/releases/tag/v0.9.0 