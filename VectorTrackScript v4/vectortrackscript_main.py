"""
Bridge module for VectorTrackScript v4.
VSM wrapper: import vectortrackscript_main; vectortrackscript_main.execute()
"""
import importlib
import traceback

PLUGIN_NAME = 'VectorTrackScript'
PLUGIN_VERSION = '0.4.0'
PLUGIN_BETA = True


def format_plugin_version() -> str:
    label = f'{PLUGIN_NAME} {PLUGIN_VERSION}'
    if PLUGIN_BETA:
        label += ' beta'
    return label
PLUGIN_AUTHOR = 'PLD (Paragon Live Design)'
PLUGIN_EMAIL = 'Cody@Paragonlivedesign.com'
PLUGIN_DONATE = 'Donate: https://venmo.com/Cody-Lisle'


def execute():
    import vs
    try:
        import vectortrack_dialog
        importlib.reload(vectortrack_dialog)
        vectortrack_dialog.run()
    except Exception as e:
        vs.AlrtDialog(f"{PLUGIN_NAME} Error:\n\n{e}\n\n{traceback.format_exc()}")
