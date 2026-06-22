"""
VectorTrackScript v4 — summary dialog (CreateLayout).
"""

import os
import traceback
from typing import List

import vs

from vectortrack_config import aliases_from_paths, project_details_from_paths
from vectortrack_log import (
    build_summary_text,
    find_log_path,
    parse_sessions,
    read_log_content,
)
from vectortrack_rates import (
    get_rate,
    plugin_data_dir_for_year,
    set_rate,
)
from vectortrackscript_main import (
    PLUGIN_AUTHOR,
    PLUGIN_DONATE,
    PLUGIN_EMAIL,
    PLUGIN_NAME,
    PLUGIN_VERSION,
)

# Layout item IDs
kLabelProject = 1
kEditProject = 2
kLabelClient = 3
kEditClient = 4
kLabelRate = 5
kEditRate = 6
kLabelBudget = 7
kEditBudget = 8
kLabelTrust = 9
kEditTrust = 10
kLabelSummary = 11
kEditSummary = 12
kBtnRefresh = 13
kBtnCopy = 14
kBtnAbout = 15

_dialog = None
_state = {
    'project_name': '',
    'client_name': '',
    'budget_hours': 0.0,
    'trust_note': '',
    'aliases': [],
    'vw_year': 2026,
    'data_dir': '',
    'summary_text': '',
    'total_hours': 0.0,
}


def _get_vw_year() -> int:
    try:
        major, _minor, _maint, _platform = vs.GetVersion()
        return int(major)
    except Exception:
        return 2026


def _get_project_name() -> str:
    current_doc = vs.GetFName()
    if not current_doc:
        return ''
    return os.path.basename(current_doc.replace('\\', '/'))


def _normalize_name(name: str) -> str:
    return os.path.basename((name or '').replace('\\', '/')).strip().lower()


def _trust_note_for_data(content: str, aliases: List[str], sessions_count: int) -> str:
    score = 0.0
    if sessions_count > 0:
        score += 0.45
    if aliases:
        score += 0.35
    if 'save' in content.lower() and 'as' in content.lower():
        score += 0.20
    if score >= 0.8:
        level = 'High'
    elif score >= 0.5:
        level = 'Medium'
    else:
        level = 'Low'
    return f'{level} ({score:.2f})'


def _load_tracking_data(project_name: str, rate: float, client_name: str, budget_hours: float):
    log_path = find_log_path(_state['vw_year'])
    if not log_path:
        return (
            f'Cannot find Vectorworks Log.txt for VW {_state["vw_year"]}.\n'
            'Check that logging is enabled in Vectorworks preferences.',
            0.0,
            'Low (0.00)',
        )
    try:
        content = read_log_content(log_path)
    except OSError as exc:
        return f'Error reading log file:\n{exc}', 0.0, 'Low (0.00)'

    sessions, total_hours = parse_sessions(content, project_name, aliases=_state.get('aliases', []))
    trust_note = _trust_note_for_data(content, _state.get('aliases', []), len(sessions))
    if not sessions:
        return f'No time logged for {project_name} yet.', 0.0, trust_note

    summary = build_summary_text(
        project_name,
        sessions,
        total_hours,
        rate,
        client_name=client_name,
        budget_hours=budget_hours if budget_hours > 0 else None,
        trust_note=trust_note,
    )
    return summary, total_hours, trust_note


def _refresh_summary():
    project = _state['project_name']
    if not project:
        _state['summary_text'] = 'No document is currently open.'
        _state['total_hours'] = 0.0
        _state['trust_note'] = 'Low (0.00)'
        return

    try:
        rate = vs.GetEditReal(_dialog, kEditRate)
    except Exception:
        rate = get_rate(_state['data_dir'], project)
    client_name = vs.GetItemText(_dialog, kEditClient).strip() if _dialog else _state.get('client_name', '')
    try:
        budget_hours = float(vs.GetEditReal(_dialog, kEditBudget))
    except Exception:
        budget_hours = float(_state.get('budget_hours', 0.0))

    summary, total_hours, trust_note = _load_tracking_data(project, rate, client_name, budget_hours)
    _state['summary_text'] = summary
    _state['total_hours'] = total_hours
    _state['trust_note'] = trust_note
    _state['client_name'] = client_name
    _state['budget_hours'] = budget_hours
    vs.SetItemText(_dialog, kEditSummary, summary)
    vs.SetItemText(_dialog, kEditTrust, trust_note)


def _copy_text_to_clipboard(text: str) -> bool:
    try:
        import tkinter  # pylint: disable=import-outside-toplevel

        root = tkinter.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        return False


def _copy_summary():
    summary = _state.get('summary_text', '')
    if not summary:
        vs.AlrtDialog('Nothing to copy yet. Click Refresh first.')
        return
    if _copy_text_to_clipboard(summary):
        vs.AlrtDialog('Summary copied to clipboard.')
    else:
        vs.AlrtDialog('Clipboard copy failed in this environment. Select and copy from the summary field.')


def _show_about():
    about_text = (
        f'{PLUGIN_NAME} v{PLUGIN_VERSION}\n\n'
        f'Time tracking summary from Vectorworks Log.txt\n'
        f'for the currently open project file.\n\n'
        f'By {PLUGIN_AUTHOR}\n'
        f'Email: {PLUGIN_EMAIL}\n'
        f'{PLUGIN_DONATE}'
    )
    vs.AlrtDialog(about_text)


def _create_dialog():
    global _dialog
    _dialog = vs.CreateLayout(
        f'{PLUGIN_NAME} v{PLUGIN_VERSION}',
        True,
        'Close',
        '',
    )

    vs.CreateStaticText(_dialog, kLabelProject, 'Project:', 12)
    vs.CreateEditText(_dialog, kEditProject, _state['project_name'], 48)
    vs.CreateStaticText(_dialog, kLabelClient, 'Client:', 12)
    vs.CreateEditText(_dialog, kEditClient, _state.get('client_name', ''), 48)
    vs.CreateStaticText(_dialog, kLabelRate, 'Hourly rate ($):', 16)
    vs.CreateEditReal(_dialog, kEditRate, 1, _state.get('initial_rate', 100.0), 10)
    vs.CreateStaticText(_dialog, kLabelBudget, 'Budget (hours):', 16)
    vs.CreateEditReal(_dialog, kEditBudget, 1, _state.get('budget_hours', 0.0), 10)
    vs.CreateStaticText(_dialog, kLabelTrust, 'Log trust:', 12)
    vs.CreateEditText(_dialog, kEditTrust, _state.get('trust_note', ''), 32)
    vs.CreateStaticText(_dialog, kLabelSummary, 'Summary:', 12)
    vs.CreateEditText(_dialog, kEditSummary, _state['summary_text'], 64)
    vs.CreatePushButton(_dialog, kBtnRefresh, 'Refresh')
    vs.CreatePushButton(_dialog, kBtnCopy, 'Copy Summary')
    vs.CreatePushButton(_dialog, kBtnAbout, 'About...')

    vs.SetFirstLayoutItem(_dialog, kLabelProject)
    vs.SetRightItem(_dialog, kLabelProject, kEditProject, 0, 0)
    vs.SetBelowItem(_dialog, kLabelProject, kLabelClient, 0, 0)
    vs.SetRightItem(_dialog, kLabelClient, kEditClient, 0, 0)
    vs.SetBelowItem(_dialog, kLabelClient, kLabelRate, 0, 0)
    vs.SetRightItem(_dialog, kLabelRate, kEditRate, 0, 0)
    vs.SetBelowItem(_dialog, kLabelRate, kLabelBudget, 0, 0)
    vs.SetRightItem(_dialog, kLabelBudget, kEditBudget, 0, 0)
    vs.SetBelowItem(_dialog, kLabelBudget, kLabelTrust, 0, 0)
    vs.SetRightItem(_dialog, kLabelTrust, kEditTrust, 0, 0)
    vs.SetBelowItem(_dialog, kLabelTrust, kLabelSummary, 0, 0)
    vs.SetBelowItem(_dialog, kLabelSummary, kEditSummary, 0, 0)
    vs.SetBelowItem(_dialog, kEditSummary, kBtnRefresh, 0, 8)
    vs.SetRightItem(_dialog, kBtnRefresh, kBtnCopy, 8, 0)
    vs.SetRightItem(_dialog, kBtnCopy, kBtnAbout, 8, 0)

    return _dialog


def _dialog_handler(item, _data):
    if item == kBtnRefresh:
        _refresh_summary()
    elif item == kBtnCopy:
        _copy_summary()
    elif item == kBtnAbout:
        _show_about()
    elif item == setup:
        vs.SetItemText(_dialog, kEditProject, _state['project_name'])
        vs.SetItemText(_dialog, kEditClient, _state.get('client_name', ''))
        vs.SetItemText(_dialog, kEditTrust, _state.get('trust_note', ''))
        _refresh_summary()
    elif item == ok:
        try:
            _state['client_name'] = vs.GetItemText(_dialog, kEditClient).strip()
            _state['trust_note'] = vs.GetItemText(_dialog, kEditTrust).strip()
            rate = vs.GetEditReal(_dialog, kEditRate)
            _state['budget_hours'] = float(vs.GetEditReal(_dialog, kEditBudget))
            if _state['project_name']:
                set_rate(_state['data_dir'], _state['project_name'], rate)
        except Exception:
            pass


setup = 2
ok = 1
cancel = 0


def run():
    global _dialog
    _state['vw_year'] = _get_vw_year()
    _state['data_dir'] = plugin_data_dir_for_year(_state['vw_year'])
    _state['project_name'] = _get_project_name()
    alias_map = aliases_from_paths(_state['vw_year'])
    normalized = _normalize_name(_state['project_name'])
    _state['aliases'] = []
    for canonical, aliases in alias_map.items():
        if _normalize_name(canonical) == normalized:
            _state['aliases'] = aliases
            break
    details = project_details_from_paths(_state['vw_year'], _state['project_name'])
    _state['client_name'] = str(details.get('client', '')) if isinstance(details, dict) else ''
    budget_raw = details.get('budget_hours', 0.0) if isinstance(details, dict) else 0.0
    try:
        _state['budget_hours'] = float(budget_raw)
    except (TypeError, ValueError):
        _state['budget_hours'] = 0.0
    _state['trust_note'] = 'Pending refresh'

    if not _state['project_name']:
        vs.AlrtDialog('No document is currently open!')
        return

    _state['initial_rate'] = get_rate(_state['data_dir'], _state['project_name'])
    _state['summary_text'] = 'Loading...'

    try:
        _create_dialog()
        vs.RunLayoutDialog(_dialog, _dialog_handler)
    except Exception as e:
        vs.AlrtDialog(f'{PLUGIN_NAME} Error:\n\n{e}\n\n{traceback.format_exc()}')
