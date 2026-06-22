import vs
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

def TimeTracker():
    # Create dialog
    dialog = vs.CreateLayout('Time Tracker', False, 'OK', 'Cancel')
    vs.CreateStaticText(dialog, 1, 'Select Vectorworks Log File:', 60)
    vs.CreatePushButton(dialog, 2, 'Browse...')
    vs.CreateStaticText(dialog, 3, 'Selected file: None', 60)
    vs.CreateStaticText(dialog, 4, '--- Project Summary ---', 60)
    
    # Reserve IDs for dynamic project display (5-99)
    # ID 100 will be total
    vs.CreateStaticText(dialog, 100, 'Total Billable: $0.00', 60)
    
    vs.SetFirstLayoutItem(dialog, 1)
    vs.SetBelowItem(dialog, 1, 2, 0, 0)
    vs.SetBelowItem(dialog, 2, 3, 0, 0)
    vs.SetBelowItem(dialog, 3, 4, 0, 2)
    
    # Dialog data
    project_times = defaultdict(timedelta)
    project_rates = {}  # Store rates for each project
    project_ids = {}    # Store dialog IDs for each project
    next_id = 5
    last_item_id = 4
    
    def DialogHandler(item, data):
        nonlocal last_item_id, next_id
        
        if item == 12255:  # Dialog setup
            pass
            
        elif item == 1:  # OK button
            return 1
            
        elif item == 2:  # Browse button
            # Default to Vectorworks log folder
            default_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Nemetschek', 'Vectorworks', '2025', 'Vectorworks Log.txt')
            if not os.path.exists(default_path):
                # Try without year folder
                default_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Nemetschek', 'Vectorworks', 'Vectorworks Log.txt')
            
            file_path = vs.GetFile()
            if file_path:
                vs.SetItemText(dialog, 3, f'Selected file: {os.path.basename(file_path)}')
                parse_log_file(file_path)
                
        elif item in project_rates:  # Rate changed for a project
            update_total()
                
        return 0
    
    def parse_log_file(file_path):
        nonlocal last_item_id, next_id
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            project_times.clear()
            project_rates.clear()
            project_ids.clear()
            
            current_project = None
            start_time = None
            
            for line in lines:
                # Look for project open patterns
                open_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+Opened\s+"([^"]+\.vwx)"', line)
                if open_match:
                    if current_project and start_time:
                        # Calculate time for previous project
                        end_time = datetime.strptime(open_match.group(1), '%m/%d/%Y %I:%M:%S %p')
                        duration = end_time - start_time
                        if duration.total_seconds() > 0:
                            project_times[current_project] += duration
                    
                    current_project = open_match.group(2)
                    start_time = datetime.strptime(open_match.group(1), '%m/%d/%Y %I:%M:%S %p')
                
                # Look for close patterns
                close_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+Closed\s+"([^"]+\.vwx)"', line)
                if close_match and current_project and start_time:
                    # Make sure we're closing the same file we opened
                    if close_match.group(2) == current_project:
                        end_time = datetime.strptime(close_match.group(1), '%m/%d/%Y %I:%M:%S %p')
                        duration = end_time - start_time
                        if duration.total_seconds() > 0:
                            project_times[current_project] += duration
                        current_project = None
                        start_time = None
            
            # Create UI elements for each project
            current_y = last_item_id
            for project, total_time in sorted(project_times.items()):
                hours = total_time.total_seconds() / 3600
                
                # Create static text for project name and hours
                text_id = next_id
                vs.CreateStaticText(dialog, text_id, f'{project}: {hours:.2f} hrs', 40)
                
                # Create rate input for this project
                rate_id = next_id + 1
                vs.CreateStaticText(dialog, rate_id + 1000, 'Rate $', 10)  # Label
                vs.CreateEditReal(dialog, rate_id, 2, 100.0)  # Rate input
                
                # Position the elements
                vs.SetBelowItem(dialog, current_y, text_id, 0, 1)
                vs.SetRightItem(dialog, text_id, rate_id + 1000, 2, 0)
                vs.SetRightItem(dialog, rate_id + 1000, rate_id, 0, 0)
                
                # Store the rate ID for this project
                project_rates[rate_id] = project
                project_ids[project] = {'text': text_id, 'rate': rate_id}
                
                current_y = text_id
                next_id += 2
            
            # Position the total at the bottom
            vs.SetBelowItem(dialog, current_y, 100, 0, 2)
            
            update_total()
            
        except Exception as e:
            vs.AlrtDialog(f'Error reading log file: {str(e)}')
    
    def update_total():
        try:
            total_bill = 0
            total_hours = 0
            
            for project, total_time in project_times.items():
                hours = total_time.total_seconds() / 3600
                total_hours += hours
                
                if project in project_ids:
                    rate_id = project_ids[project]['rate']
                    success, rate = vs.GetEditReal(dialog, rate_id)
                    if success:
                        project_bill = hours * rate
                        total_bill += project_bill
            
            vs.SetItemText(dialog, 100, f'Total Billable: ${total_bill:.2f} ({total_hours:.2f} hrs)')
        except:
            pass
    
    if vs.RunLayoutDialog(dialog, DialogHandler) == 1:
        # Generate detailed report
        if project_times:
            report = 'Time Tracking Report\n' + '='*50 + '\n\n'
            total_hours = 0
            total_bill = 0
            
            for project, total_time in sorted(project_times.items()):
                hours = total_time.total_seconds() / 3600
                total_hours += hours
                
                # Get the rate for this project
                rate = 100.0  # default
                if project in project_ids:
                    rate_id = project_ids[project]['rate']
                    success, rate = vs.GetEditReal(dialog, rate_id)
                    if not success:
                        rate = 100.0
                
                bill = hours * rate
                total_bill += bill
                
                report += f'{project}\n'
                report += f'  Time: {hours:.2f} hours\n'
                report += f'  Rate: ${rate:.2f}/hr\n'
                report += f'  Bill: ${bill:.2f}\n\n'
            
            report += '-'*50 + '\n'
            report += f'Total Hours: {total_hours:.2f}\n'
            report += f'Total Bill: ${total_bill:.2f}'
            
            vs.AlrtDialog(report)

# Run the plugin
TimeTracker() 