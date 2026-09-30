# A4Tech G800V G-keys

Makes the G-keys of an **A4Tech X7 G800V** keyboard work as standalone keys on Windows,
so they can be bound independently in games, OBS, Discord, AutoHotkey, etc.

Out of the box the G-keys only work by being bound (in the A4Tech app) to other
keys or combinations. However, the keyboard also reports every G-key press on a
hidden vendor-defined HID interface (usage page `0xFFA0`) as a bitmask. `gkeys.py`
listens to that interface and emulates keys that don't exist on a regular keyboard.

## Default mapping

| G-key   | Emulated key |
|---------|--------------|
| G1–G7   | F13–F19      |
| G9–G13  | F20–F24      |
| G14     | Kana         |
| G15     | Convert      |
| G16     | NonConvert   |

There is no physical G8 key (its bit exists in the report but is never set).
Kana / Convert / NonConvert are Japanese keyboard keys: they do nothing on
Russian/English layouts but are seen by apps and games as distinct keys.

Change the `MAPPING` dict at the top of `gkeys.py` to use other keys or
combinations (e.g. `["CTRL", "F13"]`).

## Standalone exe (easiest)

`gkeys.exe` needs no Python and no admin rights.

1. Remove any bindings from the G-keys in the A4Tech app.
2. Double-click `gkeys.exe`. It copies itself to
   `%LOCALAPPDATA%\Programs\A4Tech G-keys\`, adds itself to autostart
   (`HKCU\...\Run`), registers in **Settings → Apps** and starts in the background.

To uninstall, either uninstall **A4Tech G-keys** in Settings → Apps, or run
`gkeys.exe` again and choose **Yes**. Choosing **No** there reinstalls, e.g. to
update to a newer exe. Uninstalling stops the background process and removes
the autostart entry, the Apps entry and the installed files.

Command line: `gkeys.exe --install | --uninstall | --run [--quiet]`
(`--quiet` suppresses dialogs).

Windows SmartScreen / Defender may warn about an unsigned exe: click
**More info → Run anyway**.

### Building the exe

```
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --noconsole --name gkeys app.py
```

The result is `dist\gkeys.exe`.

## Running from source

### Requirements

- Windows
- Python 3.8+
- `pip install -r requirements.txt` (installs [hidapi](https://pypi.org/project/hidapi/))

Remove any bindings from the G-keys in the A4Tech app, otherwise each press
will trigger both the old binding and the new key. (The vendor reports are sent
either way.)

### Running

With a console window and a log of every press:

```
python gkeys.py
```

In the background, without a window:

```
pythonw gkeys.py
```

To stop the background instance, end the `pythonw.exe` process in Task Manager.

### Autostart

Create a shortcut in the Startup folder that launches the script with `pythonw`
(run in PowerShell from the repository folder):

```powershell
$pyw = (Get-Command pythonw).Source
$lnk = (New-Object -ComObject WScript.Shell).CreateShortcut("$([Environment]::GetFolderPath('Startup'))\A4Tech G-keys.lnk")
$lnk.TargetPath = $pyw
$lnk.Arguments = "`"$PWD\gkeys.py`""
$lnk.WorkingDirectory = "$PWD"
$lnk.Save()
```

To remove autostart, delete `A4Tech G-keys.lnk` from the Startup folder
(`Win+R` → `shell:startup`).

#### Games running as administrator

Windows blocks input sent by a normal process into elevated windows. If a game
runs as administrator, the script must run elevated too. In that case use Task
Scheduler instead of the Startup folder: create a task triggered "At log on",
check "Run with highest privileges", action: `pythonw.exe` with the full path to
`gkeys.py` as the argument.

## Notes

- Games with kernel anti-cheat may ignore injected (software-generated) input.
- If the script exits or the keyboard is unplugged while a G-key is held, all
  held keys are released so nothing gets stuck.

## Debugging

`sniff.py` dumps raw reports from all readable HID interfaces of the keyboard:

```
python sniff.py 30
```

Report format on page `0xFFA0`: `04 xx xx b3 b4 00 00 00 80`, where `b3` bits
0–7 are G1–G8 and `b4` bits 0–7 are G9–G16. Bytes 1–2 change when bindings are
edited in the A4Tech app.
