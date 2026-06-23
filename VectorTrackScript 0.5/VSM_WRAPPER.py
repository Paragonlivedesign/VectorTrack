# Paste this into the VectorTrackScript 0.5 menu command script in Plug-in Manager.
# Replace 2026 with your Vectorworks year if different.

import os
import sys
import importlib
import traceback
import vs

VW_YEAR = '2026'
PLUGIN_FOLDER = 'VectorTrackScript 0.5'

try:
    user_plugins = os.path.join(
        os.environ.get('APPDATA', ''),
        'Nemetschek', 'Vectorworks', VW_YEAR, 'Plug-ins',
    )
    plugin_folder = os.path.join(user_plugins, PLUGIN_FOLDER)
    if plugin_folder not in sys.path:
        sys.path.insert(0, plugin_folder)

    import vectortrackscript_main
    importlib.reload(vectortrackscript_main)
    vectortrackscript_main.execute()
except Exception as e:
    vs.AlrtDialog(f"VectorTrackScript 0.5 Error:\n\n{e}\n\n{traceback.format_exc()}")
