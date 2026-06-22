"""
Simple Time Tracker for Vectorworks - Current Project Only
Tracks time for the currently open project
"""

import vs
import os
import re
from datetime import datetime

def TimeTrackerSimple():
    # Get the current document name
    current_doc = vs.GetFName()
    if not current_doc:
        vs.AlrtDialog("No document is currently open!")
        return
    
    # Get just the filename without path
    project_name = os.path.basename(current_doc)
    
    # Find and parse the log file
    log_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 
                           'Nemetschek', 'Vectorworks', '2025', 'Vectorworks Log.txt')
    
    if not os.path.exists(log_path):
        vs.AlrtDialog("Can't find Vectorworks Log.txt")
        return
    
    # Parse the log for THIS project only
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        vs.AlrtDialog("Error reading log file")
        return
    
    # Calculate total time for this project
    total_hours = 0
    sessions = []
    current_session_start = None
    
    lines = content.split('\n')
    for line in lines:
        # Look for this project being opened
        if f'Opened "{project_name}"' in line:
            match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)', line)
            if match:
                current_session_start = datetime.strptime(match.group(1), '%m/%d/%Y %I:%M:%S %p')
        
        # Look for this project being closed
        elif f'Closed "{project_name}"' in line and current_session_start:
            match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)', line)
            if match:
                session_end = datetime.strptime(match.group(1), '%m/%d/%Y %I:%M:%S %p')
                hours = (session_end - current_session_start).total_seconds() / 3600
                sessions.append((current_session_start, session_end, hours))
                total_hours += hours
                current_session_start = None
    
    # If there's an open session (file currently open), calculate time until now
    if current_session_start:
        session_end = datetime.now()
        hours = (session_end - current_session_start).total_seconds() / 3600
        sessions.append((current_session_start, session_end, hours))
        total_hours += hours
    
    if total_hours == 0:
        vs.AlrtDialog(f"No time logged for {project_name} yet.")
        return
    
    # Get the hourly rate for this project
    rate_str = vs.StrDialog(f"Hourly rate for {project_name}:", "100")
    if not rate_str:
        return
    
    try:
        rate = float(rate_str)
    except:
        vs.AlrtDialog("Invalid rate")
        return
    
    # Calculate total amount
    total_amount = total_hours * rate
    
    # Show results
    output = []
    output.append(f"TIME TRACKING FOR: {project_name}")
    output.append("=" * 60)
    output.append("")
    output.append("SESSIONS:")
    
    for i, (start, end, hours) in enumerate(sessions[-10:], 1):  # Show last 10 sessions
        if end.date() == datetime.now().date() and i == len(sessions):
            output.append(f"  Current session: {start.strftime('%I:%M %p')} - NOW ({hours:.2f} hrs)")
        else:
            output.append(f"  {start.strftime('%m/%d %I:%M %p')} - {end.strftime('%I:%M %p')} ({hours:.2f} hrs)")
    
    if len(sessions) > 10:
        output.append(f"  ... and {len(sessions) - 10} more sessions")
    
    output.append("")
    output.append("-" * 60)
    output.append(f"Total Hours: {total_hours:.2f}")
    output.append(f"Rate: ${rate:.2f}/hour")
    output.append(f"TOTAL AMOUNT: ${total_amount:.2f}")
    output.append("-" * 60)
    output.append("")
    output.append("Re-run this command to update with current session time.")
    
    result_text = '\n'.join(output)
    vs.AlrtDialog(result_text)
    
    # Quick save option
    if vs.YNDialog(f"Save invoice for {project_name}?") == 1:
        # Create invoice content first
        invoice_content = []
        invoice_content.append(f"INVOICE - {project_name}")
        invoice_content.append(f"Generated: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}")
        invoice_content.append("=" * 60)
        invoice_content.append("")
        invoice_content.append(f"Project: {project_name}")
        invoice_content.append(f"Total Hours: {total_hours:.2f}")
        invoice_content.append(f"Hourly Rate: ${rate:.2f}")
        invoice_content.append(f"TOTAL DUE: ${total_amount:.2f}")
        invoice_content.append("")
        invoice_content.append("=" * 60)
        invoice_content.append("")
        invoice_content.append("Session Details:")
        for start, end, hours in sessions:
            invoice_content.append(f"{start.strftime('%m/%d/%Y %I:%M %p')} - {end.strftime('%I:%M %p')} ({hours:.2f} hrs)")
        
        invoice_text = '\n'.join(invoice_content)
        
        # Try to save to Documents folder as default
        try:
            # Create default filename
            safe_name = project_name.replace('.vwx', '').replace('.', '_')
            for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
                safe_name = safe_name.replace(char, '_')
            
            default_filename = f"{safe_name}_Invoice_{datetime.now().strftime('%Y%m%d')}.txt"
            
            # Get save path from user
            save_path = vs.PutFile("Save Invoice", default_filename)
            
            if save_path:
                # PutFile might return a tuple, extract the path
                if isinstance(save_path, tuple):
                    save_path = save_path[0]
                
                # Ensure we have a proper string path
                save_path = str(save_path)
                
                # Write the file
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(invoice_text)
                
                vs.AlrtDialog(f"Invoice saved successfully!\n\n{os.path.basename(save_path)}")
                
        except Exception as e:
            # If file save fails, show the invoice content so user can copy it
            vs.AlrtDialog(f"Could not save file. Copy this invoice text:\n\n{invoice_text[:500]}...\n\n(Full text truncated for display)")

# Run it
try:
    TimeTrackerSimple()
except Exception as e:
    vs.AlrtDialog(f"Error: {str(e)}") 