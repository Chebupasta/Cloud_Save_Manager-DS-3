import os
import sys

def get_ds3_save_path():
    if sys.platform.startswith('win'):
        appdata = os.getenv('APPDATA')
        base = os.path.join(appdata, 'DarkSoulsIII')
        if not os.path.exists(base):
            return None
        for folder in os.listdir(base):
            slot = os.path.join(base, folder, 'DS30000.sl2')
            if os.path.isfile(slot):
                return slot
    else:
        # Linux/Mac (Steam Proton/Wine)
        home = os.path.expanduser('~')
        candidates = [
            os.path.join(home, '.steam/steam/steamapps/compatdata/374320/pfx/drive_c/users/steamuser/AppData/Roaming/DarkSoulsIII'),
            os.path.join(home, '.wine/drive_c/users/', os.getenv('USER', ''), 'AppData/Roaming/DarkSoulsIII'),
        ]
        for base in candidates:
            if os.path.exists(base):
                for folder in os.listdir(base):
                    slot = os.path.join(base, folder, 'DS30000.sl2')
                    if os.path.isfile(slot):
                        return slot
    return None 