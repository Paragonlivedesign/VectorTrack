"""
Time Tracker Pro for Vectorworks
Creates professional invoice layout on design layer
"""

import vs
import os
import re
from datetime import datetime

def TimeTrackerPro():
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
    
    # Get invoice details
    rate_str = vs.StrDialog(f"Hourly rate for {project_name}:", "100")
    if not rate_str:
        return
    
    try:
        rate = float(rate_str)
    except:
        vs.AlrtDialog("Invalid rate")
        return
    
    # Get client name
    client_name = vs.StrDialog("Client name:", "")
    if not client_name:
        client_name = "Client"
    
    # Get invoice number
    invoice_num = vs.StrDialog("Invoice number:", f"INV-{datetime.now().strftime('%Y%m%d')}")
    if not invoice_num:
        invoice_num = f"INV-{datetime.now().strftime('%Y%m%d')}"
    
    # Calculate total amount
    total_amount = total_hours * rate
    
    # Create invoice on new design layer
    create_professional_invoice(project_name, client_name, invoice_num, 
                               sessions, total_hours, rate, total_amount)

def create_professional_invoice(project_name, client_name, invoice_num, 
                               sessions, total_hours, rate, total_amount):
    """Create a professional invoice layout"""
    
    # Create new layer for invoice
    layer_name = f"Invoice_{datetime.now().strftime('%Y%m%d_%H%M')}"
    vs.Layer(layer_name)
    
    # Set drawing attributes - use specific class overrides
    vs.PenFore(0, 0, 0)  # Black pen
    vs.PenSize(1)
    vs.FillPat(1)  # Solid fill
    vs.FillFore(65535, 65535, 65535)  # White fill
    
    # Force class attributes OFF for this operation
    vs.EnableDrawingWorksheetPlanar(True)
    
    # Define page dimensions - let's use smaller units for testing
    scale = 10  # Scale factor
    page_width = 85 * scale
    page_height = 110 * scale
    margin = 5 * scale
    
    # Create a white background rectangle
    vs.Rect(0, page_height, page_width, 0)
    bg_rect = vs.LNewObj()
    vs.SetFillFore(bg_rect, 65535, 65535, 65535)
    vs.SetFPat(bg_rect, 1)
    vs.SetPenFore(bg_rect, 0, 0, 0)
    vs.SetLW(bg_rect, 1)
    
    # Helper function to create text with explicit positioning
    def create_text_at(text_str, x, y, size=10):
        vs.TextSize(size)
        vs.TextOrigin(x, y)
        vs.CreateText(text_str)
        h = vs.LNewObj()
        # Force text to be black
        vs.SetPenFore(h, 0, 0, 0)
        vs.SetFillFore(h, 0, 0, 0)
        vs.SetTextFill(h, 0)  # No fill background
        vs.SetClass(h, 'None')  # Remove class assignment
        return h
    
    # Company/Header Section
    y_pos = page_height - margin
    
    # Title - centered
    create_text_at('INVOICE', page_width/2 - 50, y_pos - 50, 24)
    
    # Invoice details (right side)
    create_text_at(f'Invoice #: {invoice_num}', page_width - margin - 200, y_pos - 100, 10)
    create_text_at(f'Date: {datetime.now().strftime("%B %d, %Y")}', page_width - margin - 200, y_pos - 130, 10)
    
    # Your company info (left side)
    create_text_at('Your Company Name', margin, y_pos - 100, 12)
    create_text_at('123 Your Street', margin, y_pos - 130, 10)
    create_text_at('Your City, State ZIP', margin, y_pos - 160, 10)
    create_text_at('Phone: (555) 123-4567', margin, y_pos - 190, 10)
    create_text_at('Email: your@email.com', margin, y_pos - 220, 10)
    
    # Line separator
    y_line = page_height - 300
    vs.MoveTo(margin, y_line)
    vs.LineTo(page_width - margin, y_line)
    line1 = vs.LNewObj()
    vs.SetPenFore(line1, 0, 0, 0)
    vs.SetLW(line1, 2)
    
    # Bill To section
    y_pos = page_height - 350
    create_text_at('BILL TO:', margin, y_pos, 12)
    create_text_at(client_name, margin, y_pos - 30, 11)
    
    # Project info
    y_pos = page_height - 450
    create_text_at(f'Project: {project_name}', margin, y_pos, 11)
    
    # Table header line
    y_pos = page_height - 550
    vs.MoveTo(margin, y_pos)
    vs.LineTo(page_width - margin, y_pos)
    line2 = vs.LNewObj()
    vs.SetPenFore(line2, 0, 0, 0)
    vs.SetLW(line2, 2)
    
    # Table headers
    create_text_at('DATE', margin + 20, y_pos - 30, 10)
    create_text_at('DESCRIPTION', margin + 250, y_pos - 30, 10)
    create_text_at('HOURS', page_width - margin - 150, y_pos - 30, 10)
    create_text_at('AMOUNT', page_width - margin - 50, y_pos - 30, 10)
    
    # Table header underline
    y_pos -= 50
    vs.MoveTo(margin, y_pos)
    vs.LineTo(page_width - margin, y_pos)
    line3 = vs.LNewObj()
    vs.SetPenFore(line3, 0, 0, 0)
    vs.SetLW(line3, 1)
    
    # Table rows
    y_pos -= 30
    row_height = 25
    
    # Group sessions by date
    sessions_by_date = {}
    for start, end, hours in sessions:
        date_key = start.strftime('%m/%d/%Y')
        if date_key not in sessions_by_date:
            sessions_by_date[date_key] = []
        sessions_by_date[date_key].append((start, end, hours))
    
    # Add rows
    for date_str, date_sessions in sorted(sessions_by_date.items()):
        daily_hours = sum(h for _, _, h in date_sessions)
        daily_amount = daily_hours * rate
        
        create_text_at(date_str, margin + 20, y_pos, 10)
        create_text_at(f"Work on {project_name.replace('.vwx', '')}", margin + 250, y_pos, 10)
        create_text_at(f'{daily_hours:.2f}', page_width - margin - 150, y_pos, 10)
        create_text_at(f'${daily_amount:.2f}', page_width - margin - 50, y_pos, 10)
        
        y_pos -= row_height
    
    # Subtotal line
    y_pos -= 20
    vs.MoveTo(margin, y_pos)
    vs.LineTo(page_width - margin, y_pos)
    line4 = vs.LNewObj()
    vs.SetPenFore(line4, 0, 0, 0)
    
    # Totals section
    y_pos -= 50
    totals_x = page_width - margin - 300
    
    # Subtotal
    create_text_at('Subtotal:', totals_x, y_pos, 10)
    create_text_at(f'${total_amount:.2f}', page_width - margin - 50, y_pos, 10)
    
    # Tax line
    y_pos -= 30
    create_text_at('Tax (0%):', totals_x, y_pos, 10)
    create_text_at('$0.00', page_width - margin - 50, y_pos, 10)
    
    # Total line
    y_pos -= 30
    vs.MoveTo(totals_x - 20, y_pos + 10)
    vs.LineTo(page_width - margin, y_pos + 10)
    line5 = vs.LNewObj()
    vs.SetPenFore(line5, 0, 0, 0)
    vs.SetLW(line5, 2)
    
    # Total amounts
    create_text_at('TOTAL:', totals_x, y_pos - 20, 12)
    create_text_at(f'${total_amount:.2f}', page_width - margin - 50, y_pos - 20, 12)
    
    # Payment terms
    y_pos = 100
    create_text_at('Payment Terms: Due upon receipt', margin, y_pos, 9)
    create_text_at('Thank you for your business!', margin, y_pos - 30, 9)
    
    # Group all objects
    vs.SelectAll()
    vs.Group()
    invoice_group = vs.LNewObj()
    
    # Center on page
    vs.HCenter(invoice_group, 0, 0)
    
    # Deselect and zoom
    vs.DSelectAll()
    vs.DoMenuTextByName('Fit To Objects', 0)
    
    vs.AlrtDialog(f"Professional invoice created on layer '{layer_name}'!\n\n" +
                 "The invoice has been grouped for easy manipulation.")

# Run the plugin
try:
    TimeTrackerPro()
except Exception as e:
    vs.AlrtDialog(f"Error: {str(e)}") 