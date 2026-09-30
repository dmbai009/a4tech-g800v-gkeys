"""Entry point for the standalone gkeys.exe.

    gkeys.exe               first run: install + start; next runs: uninstall / reinstall prompt
    gkeys.exe --run         the background remapper itself (what autostart launches)
    gkeys.exe --install     install / update without asking
    gkeys.exe --uninstall   stop, remove autostart, the Apps entry and the installed files
    --quiet                 no dialogs (for scripts)

Everything is per-user (HKCU + %LOCALAPPDATA%), no admin rights needed.
"""
import ctypes
import os
import shutil
import subprocess
import sys
import time
import winreg

import gkeys

APP_NAME = "A4Tech G-keys"
INSTALL_DIR = os.path.join(os.environ["LOCALAPPDATA"], "Programs", APP_NAME)
INSTALLED_EXE = os.path.join(INSTALL_DIR, "gkeys.exe")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\A4TechGKeys"

MB_OK, MB_YESNOCANCEL = 0x0, 0x3
MB_ICONINFO, MB_ICONQUESTION, MB_ICONERROR = 0x40, 0x20, 0x10
IDYES, IDNO = 6, 7  # IDCANCEL (2) = do nothing
DETACHED_PROCESS, CREATE_NO_WINDOW = 0x8, 0x08000000


QUIET = "--quiet" in sys.argv


def msg(text, flags=MB_OK | MB_ICONINFO):
    if QUIET:
        return 0
    return ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, flags)


def is_installed():
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY))
        return True
    except OSError:
        return False


def start_background():
    subprocess.Popen([INSTALLED_EXE, "--run"], close_fds=True,
                     creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW)


def install():
    gkeys.stop_running_instance()
    os.makedirs(INSTALL_DIR, exist_ok=True)
    if os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(INSTALLED_EXE):
        # the stopped instance may keep the old exe locked for a moment
        for attempt in range(20):
            try:
                shutil.copy2(sys.executable, INSTALLED_EXE)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.25)

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
        winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, f'"{INSTALLED_EXE}" --run')

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
        size_kb = os.path.getsize(INSTALLED_EXE) // 1024
        for name, value in [
            ("DisplayName", APP_NAME),
            ("DisplayIcon", INSTALLED_EXE),
            ("Publisher", "dmbai009"),
            ("InstallLocation", INSTALL_DIR),
            ("UninstallString", f'"{INSTALLED_EXE}" --uninstall'),
        ]:
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
        for name, value in [("NoModify", 1), ("NoRepair", 1), ("EstimatedSize", size_kb)]:
            winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, value)

    start_background()


def delete_value(key, name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, name)
    except FileNotFoundError:
        pass


def uninstall():
    stopped = gkeys.stop_running_instance()
    delete_value(RUN_KEY, APP_NAME)
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except FileNotFoundError:
        pass
    # The running exe can't delete itself: a hidden cmd retries for ~15 s after we exit.
    # CREATE_NO_WINDOW gives it a hidden console; with DETACHED_PROCESS cmd fails outright.
    if os.path.isdir(INSTALL_DIR):
        subprocess.Popen(
            f'cmd /c for /l %i in (1,1,15) do (ping -n 2 127.0.0.1 >nul'
            f' & rmdir /s /q "{INSTALL_DIR}" 2>nul & if not exist "{INSTALL_DIR}" exit)',
            creationflags=CREATE_NO_WINDOW, close_fds=True)
    return stopped


def interactive():
    if not is_installed():
        install()
        msg(f"{APP_NAME} is installed and running.\n\n"
            "G1-G7 → F13-F19, G9-G13 → F20-F24, G14-G16 → Kana / Convert / NonConvert.\n"
            "Remove any bindings from the G-keys in the A4Tech app.\n\n"
            "It starts automatically with Windows. To remove it, run this file again "
            f'or uninstall "{APP_NAME}" in Settings → Apps.')
        return

    answer = msg(f"{APP_NAME} is already installed.\n\n"
                 "Yes — uninstall\nNo — reinstall / update to this version\nCancel — do nothing",
                 MB_YESNOCANCEL | MB_ICONQUESTION)
    if answer == IDYES:
        uninstall_with_message()
    elif answer == IDNO:
        install()
        msg(f"{APP_NAME} is reinstalled and running.")


def uninstall_with_message():
    if uninstall():
        msg(f"{APP_NAME} is uninstalled.")
    else:
        msg(f"{APP_NAME} is uninstalled, but the running instance didn't stop.\n"
            "End gkeys.exe in Task Manager or sign out and back in.", MB_OK | MB_ICONERROR)


def main():
    args = sys.argv[1:]
    try:
        if "--run" in args:
            gkeys.main()
        elif "--uninstall" in args:
            uninstall_with_message()
        elif "--install" in args:
            install()
        else:
            interactive()
    except Exception as e:  # no console in the exe, so surface errors in a dialog
        if "--run" not in args:
            msg(f"Error: {e}", MB_OK | MB_ICONERROR)
        raise


if __name__ == "__main__":
    main()
