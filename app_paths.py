"""Writable user storage and resources for source and packaged applications."""
import os
import sys
import subprocess
from pathlib import Path
ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
PUBLIC = (ROOT / 'distribution.json').exists()

def storage_root():
    if os.getenv('BULLETIN_HOME'):
        return Path(os.environ['BULLETIN_HOME']).expanduser()
    if not PUBLIC and not getattr(sys, 'frozen', False):
        return ROOT
    if sys.platform == 'win32':
        return Path(os.getenv('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))) / 'BulletinStudio'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/BulletinStudio'
    return Path(os.getenv('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'BulletinStudio'

def documents_folder():
    if os.getenv('BULLETIN_OUTPUT'):
        return Path(os.environ['BULLETIN_OUTPUT']).expanduser()
    if sys.platform == 'win32':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
                return Path(os.path.expandvars(winreg.QueryValueEx(key, 'Personal')[0]))
        except OSError:
            pass
    return Path.home() / 'Documents'

def open_folder(folder):
    if sys.platform == 'win32':
        os.startfile(str(folder))
    else:
        subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(folder)])
