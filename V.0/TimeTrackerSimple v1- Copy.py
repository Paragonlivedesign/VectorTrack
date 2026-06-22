"""
Simplified Time Tracker Plugin for Vectorworks
Helps locate and parse the correct session log file
"""

import vs
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

def TimeTrackerSimple():
    # Dialog constants
    kOK = 1
    kCancel = 2
    kSelectLog = 3
    kParseButton = 4
    kExportButton = 5
    kFindLogs = 6
    
    # Store data
    global_data = {
        'log_path': '',
        'project_times': {}
    }
    
    def find_log_files():
        """Find all potential log files in Vectorworks directories"""
        log_locations = []
        
        # Specific log files to look for
        target_logs = [
            'Vectorworks Log.txt',  # Has session/file open info
            'VW User Log.txt',      # User activity log
            'Session Log.txt',
            'Usage Log.txt'
        ]
        
        # Common Vectorworks log locations
        base_paths = [
            os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Nemetschek', 'Vectorworks', '2025'),
            os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Nemetschek', 'Vectorworks'),
            os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Vectorworks'),
            os.path.join(os.path.expanduser('~'), 'Documents', 'Vectorworks')
        ]
        
        # Look for specific log files first
        for base_path in base_paths:
            if os.path.exists(base_path):
                for log_name in target_logs:
                    log_path = os.path.join(base_path, log_name)
                    if os.path.exists(log_path):
                        # Verify it contains session data
                        try:
                            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                                sample = f.read(2000)
                                if '.vwx' in sample and ('Opened "' in sample or 'Opening file' in sample):
                                    log_locations.append((log_name, log_path))
                        except:
                            continue
        
        # Also search subdirectories for any log files
        for base_path in base_paths[:2]:  # Just check first two paths deeply
            if os.path.exists(base_path):
                try:
                    for root, dirs, files in os.walk(base_path):
                        # Don't go too deep
                        if root.count(os.sep) - base_path.count(os.sep) > 3:
                            continue
                        for file in files:
                            if file.endswith('.txt') and 'log' in file.lower():
                                full_path = os.path.join(root, file)
                                # Check if already found
                                if any(full_path == path for _, path in log_locations):
                                    continue
                                # Quick check for session data
                                try:
                                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        sample = f.read(1000)
                                        if '.vwx"' in sample and 'Opened "' in sample:
                                            log_locations.append((file, full_path))
                                except:
                                    continue
                except:
                    continue
        
        if log_locations:
            # Auto-select if we found "Vectorworks Log.txt"
            for name, path in log_locations:
                if name == 'Vectorworks Log.txt':
                    global_data['log_path'] = path
                    vs.AlrtDialog(f'Found and selected: {name}\n\nClick "Parse and Show" to analyze.')
                    return
            
            # Otherwise show what we found
            msg = "Found potential session logs:\n\n"
            for name, path in log_locations[:5]:  # Show max 5
                msg += f"• {name}\n  {path}\n\n"
            msg += "Use 'Select Log File' to choose one."
            vs.AlrtDialog(msg)
        else:
            vs.AlrtDialog("No session logs found automatically.\n\n" +
                         "Please use 'Select Log File' to browse to:\n" +
                         "C:\\Users\\<YourName>\\AppData\\Roaming\\Nemetschek\\Vectorworks\\2025\\\n\n" +
                         "Look for 'Vectorworks Log.txt' or similar.")
    
    def parse_log_file():
        """Parse log file looking for file open/close events"""
        if not global_data['log_path'] or not os.path.exists(global_data['log_path']):
            vs.AlrtDialog('Please select a log file first.')
            return False
            
        try:
            with open(global_data['log_path'], 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            vs.AlrtDialog(f'Error reading file: {str(e)}')
            return False
        
        if not content:
            vs.AlrtDialog('Log file is empty.')
            return False
        
        # Check if this looks like a session log
        if '.vwx' not in content:
            vs.AlrtDialog('This does not appear to be a session log file.\n\n' +
                         'Session logs contain entries like:\n' +
                         '1/5/2025 10:15:00 AM Opened "Project.vwx"\n\n' +
                         'Please select a different log file.')
            return False
        
        # Parse the log
        lines = content.split('\n')
        project_times = defaultdict(lambda: 0.0)
        current_project = None
        start_time = None
        entries_found = 0
        
        for line in lines:
            if not line.strip():
                continue
                
            # Try multiple patterns to find open/close events
            
            # Pattern 1: Standard text log format
            # "1/5/2025 10:15:00 AM Opened "Project.vwx""
            open_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+Opened\s+"([^"]+\.vwx)"', line)
            if open_match:
                entries_found += 1
                if current_project and start_time:
                    # Close previous
                    end_time = datetime.strptime(open_match.group(1), '%m/%d/%Y %I:%M:%S %p')
                    hours = (end_time - start_time).total_seconds() / 3600
                    if hours > 0:
                        project_times[current_project] += hours
                
                current_project = os.path.basename(open_match.group(2))
                start_time = datetime.strptime(open_match.group(1), '%m/%d/%Y %I:%M:%S %p')
                continue
            
            # Check for close
            close_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+Closed\s+"([^"]+\.vwx)"', line)
            if close_match and current_project:
                entries_found += 1
                project_name = os.path.basename(close_match.group(2))
                if project_name == current_project:
                    end_time = datetime.strptime(close_match.group(1), '%m/%d/%Y %I:%M:%S %p')
                    hours = (end_time - start_time).total_seconds() / 3600
                    if hours > 0:
                        project_times[current_project] += hours
                    current_project = None
                    start_time = None
        
        # Close any open project
        if current_project and start_time:
            # Assume 1 hour if still open
            project_times[current_project] += 1.0
            vs.AlrtDialog(f'Note: "{current_project}" is still open in the log.\nAssuming 1 hour for this session.')
        
        if entries_found == 0:
            vs.AlrtDialog('No file open/close entries found in this log.\n\n' +
                         'This might be the wrong log file.\n' +
                         'Look for entries like:\n' +
                         '1/5/2025 10:15:00 AM Opened "Project.vwx"')
            return False
        
        if not project_times:
            vs.AlrtDialog(f'Found {entries_found} log entries but could not calculate times.\n' +
                         'This might be due to an unexpected log format.')
            return False
        
        global_data['project_times'] = dict(project_times)
        vs.AlrtDialog(f'Successfully parsed {entries_found} entries for {len(project_times)} projects.')
        return True
    
    def show_results():
        """Display results"""
        if not global_data['project_times']:
            vs.AlrtDialog('No data to display. Parse a log file first.')
            return
            
        # Build simple text output
        lines = []
        lines.append('PROJECT TIME SUMMARY')
        lines.append('=' * 50)
        lines.append('')
        
        total_hours = 0
        for project, hours in sorted(global_data['project_times'].items()):
            total_hours += hours
            proj_name = project
            if len(proj_name) > 35:
                proj_name = proj_name[:32] + '...'
            lines.append(f'{proj_name:<40} {hours:>6.2f} hrs')
        
        lines.append('-' * 50)
        lines.append(f'{"TOTAL":<40} {total_hours:>6.2f} hrs')
        lines.append('')
        lines.append(f'Log file: {os.path.basename(global_data["log_path"])}')
        
        vs.AlrtDialog('\n'.join(lines))
    
    def export_results():
        """Export to text file"""
        if not global_data['project_times']:
            vs.AlrtDialog('No data to export.')
            return
            
        file_path = vs.PutFile('Save Report', 'TimeReport.txt')
        if not file_path:
            return
            
        try:
            with open(file_path, 'w') as f:
                f.write('Vectorworks Time Tracking Report\n')
                f.write(f'Generated: {datetime.now().strftime("%m/%d/%Y %I:%M %p")}\n')
                f.write(f'Log File: {os.path.basename(global_data["log_path"])}\n\n')
                
                total_hours = 0
                for project, hours in sorted(global_data['project_times'].items()):
                    total_hours += hours
                    f.write(f'{project:<40} {hours:>6.2f} hrs\n')
                
                f.write('-' * 50 + '\n')
                f.write(f'{"TOTAL":<40} {total_hours:>6.2f} hrs\n')
                
            vs.AlrtDialog('Report exported successfully!')
        except Exception as e:
            vs.AlrtDialog(f'Export error: {str(e)}')
    
    # Main dialog handler
    def DialogHandler(item, data):
        if item == kFindLogs:
            find_log_files()
            
        elif item == kSelectLog:
            file_path = vs.GetFile()
            if file_path and os.path.exists(file_path):
                global_data['log_path'] = file_path
                vs.AlrtDialog(f'Selected: {os.path.basename(file_path)}')
                
        elif item == kParseButton:
            if parse_log_file():
                show_results()
                
        elif item == kExportButton:
            export_results()
            
        return item
    
    # Auto-find logs on startup
    try:
        # Try to auto-load Vectorworks Log.txt
        default_log = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 
                                 'Nemetschek', 'Vectorworks', '2025', 'Vectorworks Log.txt')
        if os.path.exists(default_log):
            # Quick verify it has session data
            with open(default_log, 'r', encoding='utf-8', errors='ignore') as f:
                sample = f.read(1000)
                if '.vwx' in sample and 'Opened "' in sample:
                    global_data['log_path'] = default_log
    except:
        pass
    
    # Create minimal dialog
    try:
        dialog = vs.CreateLayout('Time Tracker', False, 'OK', 'Cancel')
        
        vs.CreateStaticText(dialog, 10, 'Find and parse Vectorworks session logs', 50)
        vs.CreatePushButton(dialog, kFindLogs, 'Find Log Files')
        vs.CreatePushButton(dialog, kSelectLog, 'Select Log File')
        vs.CreatePushButton(dialog, kParseButton, 'Parse and Show')
        vs.CreatePushButton(dialog, kExportButton, 'Export Report')
        
        # Show current selection if any
        if global_data['log_path']:
            vs.CreateStaticText(dialog, 11, f'Auto-found: {os.path.basename(global_data["log_path"])}', 50)
            vs.SetFirstLayoutItem(dialog, 11)
            vs.SetBelowItem(dialog, 11, 10, 0, 1)
        else:
            vs.SetFirstLayoutItem(dialog, 10)
            
        vs.SetBelowItem(dialog, 10, kFindLogs, 0, 1)
        vs.SetBelowItem(dialog, kFindLogs, kSelectLog, 0, 1)
        vs.SetBelowItem(dialog, kSelectLog, kParseButton, 0, 1)
        vs.SetBelowItem(dialog, kParseButton, kExportButton, 0, 1)
        
        vs.RunLayoutDialog(dialog, DialogHandler)
        
    except Exception as e:
        vs.AlrtDialog(f'Dialog creation error: {str(e)}')

# Run plugin
try:
    TimeTrackerSimple()
except Exception as e:
    vs.AlrtDialog(f'Plugin error: {str(e)}') 