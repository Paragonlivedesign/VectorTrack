# VectorTrack

Professional time tracking software for Vectorworks projects. Automatically tracks your work time and generates detailed reports.

## Version
Current Version: 0.0.1-alpha

## Features
- Automatic detection and tracking of open Vectorworks files
- Individual hourly rates per project
- Idle detection and status tracking
- Detailed time reports with billable amounts
- Dark and light theme support
- Session logging and export capabilities
- Custom color themes
- Professional PDF report generation

## Requirements
- Windows 10 or later
- Python 3.8 or later
- Vectorworks 2023 or later

## Installation
1. Clone this repository
2. Install required dependencies:
```bash
pip install -r requirements.txt
```
3. Run the application:
```bash
python -m vectortrack
```

## Changelog

### Version 0.0.1-alpha (2024-03-XX)
Initial alpha release with core functionality:
- Basic file tracking implementation
- Activity monitoring with idle detection
- Project-specific hourly rates
- Session tracking and logging
- PDF report generation
- Dark/light theme support
- Custom color themes
- Application settings management
- Basic license management system
- Session summary table
- Log viewing and export capabilities

## Known Issues
- Window detection may require refinement for certain Vectorworks configurations
- Rate changes during active tracking sessions require pausing first
- No way to track and merge time across different versions of the same file

## Upcoming Features
- Project Version Management
  - Smart Version Detection
    - Pattern recognition for common version formats (v1, rev1, _001, etc.)
    - Detection of date-based versions (YYYYMMDD)
    - Recognition of client revision numbers
    - Backup file detection ("_backup", ".backup", etc.)
  - Version Relationship Management
    - Visual version timeline/tree view
    - Drag-and-drop version linking
    - Bulk version association
    - Version branching support
    - Version tags and labels
  - Time Tracking Across Versions
    - Consolidated time views across all versions
    - Per-version breakdown of time spent
    - Version comparison reports
    - Activity timeline across versions
    - Automatic rate inheritance between versions
  - Project Organization
    - Project groups for related files
    - Version hierarchies
    - Custom version naming schemes
    - Version status tracking (Draft, Review, Final, etc.)
    - Archive management for old versions
  - Smart Features
    - Automatic version suggestions based on patterns
    - Similar file detection
    - Project continuation detection when reopening
    - Version conflict detection
    - Backup version management
  - Reporting
    - Version-aware PDF reports
    - Version comparison reports
    - Time distribution across versions
    - Version milestone tracking
    - Client revision tracking
- Data Portability & Synchronization
  - Local Data Export/Import
    - Export complete tracking data to portable format
    - Import tracking history from other installations
    - Merge data from multiple sources
    - Conflict resolution for overlapping sessions
  - Cloud Synchronization (Future)
    - User profiles with secure authentication
    - Automatic data sync across devices
    - Web dashboard for data access
    - Real-time synchronization
    - Offline mode support
- Enhanced idle state detection and logging
- Improved window detection for multiple Vectorworks instances
- Export data in multiple formats
- Advanced reporting features
- Project categorization and tagging
- Time entry adjustments
- Integration with billing systems

## License
Copyright © 2024 VectorTrack. All rights reserved. 