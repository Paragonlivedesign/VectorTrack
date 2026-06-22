import vs
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

def TimeTracker():
    # Dialog constants
    kOK = 1
    kCancel = 2
    kBrowse = 3
    kFileLabel = 4
    kStartDate = 5
    kEndDate = 6
    kFilterButton = 7
    kListBrowser = 8
    kTotalLabel = 9
    kExportButton = 10
    
    # Store data
    dialog_data = {
        'project_times': defaultdict(timedelta),
        'all_entries': [],
        'filtered_times': defaultdict(timedelta),
        'file_path': ''
    }
    
    def DialogHandler(item, data):
        if item == 12255:  # Dialog setup event (kSetupDialogC)
            # Set up list browser after dialog is initialized
            # Note: CreateListBoxN requires careful setup - some functions may not work as expected
            vs.SetLBControlType(dialog, kListBrowser, 1)  # Static text mode
            vs.EnableLBColumnLines(dialog, kListBrowser, True)
            
            # Set up columns - using InsertLBColumn
            # Note: Column indices are 0-based according to the forums
            vs.InsertLBColumn(dialog, kListBrowser, 0, 'Project', 300)
            vs.InsertLBColumn(dialog, kListBrowser, 1, 'Hours', 80)
            vs.InsertLBColumn(dialog, kListBrowser, 2, 'Rate $/hr', 80)
            vs.InsertLBColumn(dialog, kListBrowser, 3, 'Total $', 100)
            
            # Set default dates (last 30 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            vs.SetItemText(dialog, kStartDate, start_date.strftime('%m/%d/%Y'))
            vs.SetItemText(dialog, kEndDate, end_date.strftime('%m/%d/%Y'))
            
            # Auto-load the default log file if it exists
            default_log = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 
                                     'Nemetschek', 'Vectorworks', '2025', 'Vectorworks Log.txt')
            if os.path.exists(default_log):
                dialog_data['file_path'] = default_log
                vs.SetItemText(dialog, kFileLabel, f'File: {os.path.basename(default_log)}')
                try:
                    parse_log_file(default_log)
                    filter_by_date()
                except Exception as e:
                    vs.AlrtDialog(f'Error loading log file: {str(e)}')
            else:
                # Try without year folder
                default_log = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 
                                         'Nemetschek', 'Vectorworks', 'Vectorworks Log.txt')
                if os.path.exists(default_log):
                    dialog_data['file_path'] = default_log
                    vs.SetItemText(dialog, kFileLabel, f'File: {os.path.basename(default_log)}')
                    try:
                        parse_log_file(default_log)
                        filter_by_date()
                    except Exception as e:
                        vs.AlrtDialog(f'Error loading log file: {str(e)}')
            
        elif item == kOK:  # OK button
            return 1
            
        elif item == kCancel:  # Cancel button
            return 2
            
        elif item == kBrowse:  # Browse button
            file_path = vs.GetFile()
            if file_path:
                dialog_data['file_path'] = file_path
                vs.SetItemText(dialog, kFileLabel, f'File: {os.path.basename(file_path)}')
                try:
                    parse_log_file(file_path)
                    filter_by_date()
                except Exception as e:
                    vs.AlrtDialog(f'Error loading log file: {str(e)}')
                    
        elif item == kFilterButton:  # Filter button
            try:
                filter_by_date()
            except Exception as e:
                vs.AlrtDialog(f'Error filtering data: {str(e)}')
            
        elif item == kExportButton:  # Export button
            try:
                export_report()
            except Exception as e:
                vs.AlrtDialog(f'Error exporting report: {str(e)}')
                
        return 0
    
    def parse_log_file(file_path):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        dialog_data['project_times'].clear()
        dialog_data['all_entries'].clear()
        
        current_project = None
        start_time = None
        
        for line in lines:
            # Look for project open patterns
            open_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+Opened\s+"([^"]+\.vwx)"', line)
            if open_match:
                if current_project and start_time:
                    # Save previous session
                    end_time = datetime.strptime(open_match.group(1), '%m/%d/%Y %I:%M:%S %p')
                    dialog_data['all_entries'].append({
                        'project': current_project,
                        'start': start_time,
                        'end': end_time,
                        'duration': end_time - start_time
                    })
                
                current_project = open_match.group(2)
                start_time = datetime.strptime(open_match.group(1), '%m/%d/%Y %I:%M:%S %p')
            
            # Look for close patterns
            close_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+Closed\s+"([^"]+\.vwx)"', line)
            if close_match and current_project and start_time:
                if close_match.group(2) == current_project:
                    end_time = datetime.strptime(close_match.group(1), '%m/%d/%Y %I:%M:%S %p')
                    dialog_data['all_entries'].append({
                        'project': current_project,
                        'start': start_time,
                        'end': end_time,
                        'duration': end_time - start_time
                    })
                    current_project = None
                    start_time = None
        
        # Calculate total time per project
        for entry in dialog_data['all_entries']:
            dialog_data['project_times'][entry['project']] += entry['duration']
    
    def filter_by_date():
        # Get date range from dialog
        start_str = vs.GetItemText(dialog, kStartDate)
        end_str = vs.GetItemText(dialog, kEndDate)
        
        start_date = datetime.strptime(start_str, '%m/%d/%Y')
        end_date = datetime.strptime(end_str, '%m/%d/%Y') + timedelta(days=1)  # Include full end day
        
        # Filter entries
        dialog_data['filtered_times'].clear()
        for entry in dialog_data['all_entries']:
            if start_date <= entry['start'] < end_date:
                dialog_data['filtered_times'][entry['project']] += entry['duration']
        
        # Update list browser
        update_list_browser()
    
    def update_list_browser():
        # Clear existing items
        vs.DeleteAllLBItems(dialog, kListBrowser)
        
        total_hours = 0
        total_bill = 0
        row = 0
        
        # Add filtered projects
        for project, duration in sorted(dialog_data['filtered_times'].items()):
            hours = duration.total_seconds() / 3600
            rate = 100.0  # Default rate
            bill = hours * rate
            
            total_hours += hours
            total_bill += bill
            
            # Add row - use InsertLBItem
            vs.InsertLBItem(dialog, kListBrowser, row, project)
            vs.SetLBItemText(dialog, kListBrowser, row, 0, project)
            vs.SetLBItemText(dialog, kListBrowser, row, 1, f'{hours:.2f}')
            vs.SetLBItemText(dialog, kListBrowser, row, 2, f'{rate:.2f}')
            vs.SetLBItemText(dialog, kListBrowser, row, 3, f'${bill:.2f}')
            
            row += 1
        
        # Update total
        vs.SetItemText(dialog, kTotalLabel, f'Total: ${total_bill:.2f} ({total_hours:.2f} hours)')
    
    def export_report():
        if not dialog_data['filtered_times']:
            vs.AlrtDialog('No data to export. Please load a file and filter first.')
            return
            
        report = 'Vectorworks Time Tracking Report\n'
        report += '=' * 50 + '\n\n'
        report += f'Date Range: {vs.GetItemText(dialog, kStartDate)} to {vs.GetItemText(dialog, kEndDate)}\n\n'
        
        total_hours = 0
        total_bill = 0
        
        for project, duration in sorted(dialog_data['filtered_times'].items()):
            hours = duration.total_seconds() / 3600
            rate = 100.0  # Default rate
            bill = hours * rate
            
            total_hours += hours
            total_bill += bill
            
            report += f'{project}\n'
            report += f'  Hours: {hours:.2f}\n'
            report += f'  Rate: ${rate:.2f}/hr\n'
            report += f'  Total: ${bill:.2f}\n\n'
        
        report += '-' * 50 + '\n'
        report += f'Total Hours: {total_hours:.2f}\n'
        report += f'Total Billing: ${total_bill:.2f}'
        
        vs.AlrtDialog(report)
    
    # Create dialog
    dialog = vs.CreateLayout('Time Tracker', False, 'OK', 'Cancel')
    
    # File selection
    vs.CreateStaticText(dialog, 10, 'Select Vectorworks Log File:', 50)
    vs.CreatePushButton(dialog, kBrowse, 'Browse...')
    vs.CreateStaticText(dialog, kFileLabel, 'No file selected', 50)
    
    # Date range
    vs.CreateStaticText(dialog, 20, 'Date Range:', 50)
    vs.CreateStaticText(dialog, 21, 'Start:', 10)
    vs.CreateEditText(dialog, kStartDate, '01/01/2025', 15)
    vs.CreateStaticText(dialog, 22, 'End:', 10)
    vs.CreateEditText(dialog, kEndDate, '12/31/2025', 15)
    vs.CreatePushButton(dialog, kFilterButton, 'Filter')
    
    # List browser for results - use CreateListBoxN with single selection (False for last param)
    # Parameters: dialog, ID, width (in chars), height (in rows), multiSelect
    vs.CreateListBoxN(dialog, kListBrowser, 60, 15, False)
    
    # Total and export
    vs.CreateStaticText(dialog, kTotalLabel, 'Total: $0.00', 50)
    vs.CreatePushButton(dialog, kExportButton, 'Export Report')
    
    # Layout
    vs.SetFirstLayoutItem(dialog, 10)
    vs.SetRightItem(dialog, 10, kBrowse, 1, 0)
    vs.SetBelowItem(dialog, 10, kFileLabel, 0, 0)
    
    vs.SetBelowItem(dialog, kFileLabel, 20, 0, 2)
    vs.SetBelowItem(dialog, 20, 21, 0, 0)
    vs.SetRightItem(dialog, 21, kStartDate, 1, 0)
    vs.SetRightItem(dialog, kStartDate, 22, 2, 0)
    vs.SetRightItem(dialog, 22, kEndDate, 1, 0)
    vs.SetRightItem(dialog, kEndDate, kFilterButton, 2, 0)
    
    vs.SetBelowItem(dialog, 21, kListBrowser, 0, 1)
    vs.SetBelowItem(dialog, kListBrowser, kTotalLabel, 0, 1)
    vs.SetBelowItem(dialog, kTotalLabel, kExportButton, 0, 1)
    
    # Run dialog
    try:
        if vs.RunLayoutDialog(dialog, DialogHandler) == 1:
            if dialog_data['filtered_times']:
                vs.AlrtDialog('Time tracking complete! Use Export Report to see full details.')
    except Exception as e:
        vs.AlrtDialog(f'Dialog error: {str(e)}')

# Run the plugin
try:
    TimeTracker()
except Exception as e:
    vs.AlrtDialog(f'Plugin initialization error: {str(e)}') 