# macos-winter-overlay

I saw a short video on social media of a Mac desktop with snow piling up on the Dock and interactive fairy lights hanging from the menu bar, and wanted to recreate something similar myself as a quick weekend project.

Instead of reaching for Electron or Swift, I built it in pure Python using PyObjC to talk directly to macOS `AppKit` and `Quartz` APIs.

## What it does

- **Desktop-level overlay:** Sits right above your wallpaper (`kCGDesktopWindowLevel + 1`) and stays behind open application windows so it never gets in the way while studying or coding.
- **Dock snow accumulation:** Reads the exact width and position of your macOS Dock and lets snow pile up strictly along its top edge, smoothing out into drifts.
- **Cursor interaction:** Sweep your mouse across the Dock to shovel through the snowbank and kick particles back into the air, or brush past the fairy lights at the top to make them swing on a spring-pendulum physics model.
- **Menu bar controls:** Adds a small snowflake (`❄`) icon to the top-right menu bar to pause snowfall, clear the snowbank on the Dock, or quit cleanly.

## Performance & Battery

Desktop overlays often drain battery or eat hundreds of megabytes of RAM when built with web wrappers. This one is kept intentionally light:

- **Memory:** ~45–65 MB of RAM (native Cocoa window without Chromium overhead).
- **CPU & Battery:** Capped at 30 FPS and batches all snowflakes into a single `NSBezierPath` per frame rather than creating hundreds of separate draw calls, keeping CPU usage around 2–4% on Apple Silicon / Intel Macs.
- **Zero-cost pause:** Clicking **Pause Snow** in the menu bar halts the physics and redraw loop completely while keeping your current snowdrift on the Dock.

## Option 1: Run from source (Python)

Requires macOS and Python 3.9+.

```bash
git clone https://github.com/svet111/macos-winter-overlay.git
cd macos-winter-overlay

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python winter_overlay.py
```



## Option 2: Standalone macOS `.app`

If you do not want to set up a Python environment, download `WinterOverlay-macOS.zip` from the [suspicious link removed] page and unzip it.

**Note on first launch:** Because the app is not signed with a paid Apple Developer certificate, macOS Gatekeeper will block a normal double-click the first time. Right-click `WinterOverlay.app` -> **Open** -> **Open** (or run `xattr -cr WinterOverlay.app` in Terminal).

## Building the `.app` bundle yourself

```bash
pip install py2app
python setup.py py2app

```

The standalone app will be generated in `dist/WinterOverlay.app`.
