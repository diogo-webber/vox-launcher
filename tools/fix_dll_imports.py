import os
import sys
import ctypes
from pathlib import Path

def fix_dll_imports():
    """Fix DLL imports by adding Windows System32 to PATH"""
    if sys.platform == 'win32':
        system32 = os.path.join(os.environ.get('SystemRoot', ''), 'System32')
        if system32 and os.path.exists(system32):
            if 'PATH' not in os.environ:
                os.environ['PATH'] = system32
            elif system32 not in os.environ['PATH']:
                os.environ['PATH'] = system32 + os.pathsep + os.environ['PATH']

        # Pre-load commonly needed DLLs
        try:
            ctypes.windll.kernel32
            ctypes.windll.user32
            # Try to load the problematic DLL
            try:
                ctypes.windll.LoadLibrary("GetUserDefaultUILanguage.dll")
            except:
                pass
        except Exception:
            pass  # Ignore if DLLs can't be loaded

# Run the fix function
fix_dll_imports()
