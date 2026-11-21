from setuptools import setup

APP = ["winter_overlay.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "includes": ["objc", "AppKit", "Foundation", "Quartz"],
    "plist": {
        "CFBundleName": "WinterOverlay",
        "CFBundleDisplayName": "Winter Overlay",
        "CFBundleIdentifier": "io.github.svet111.winter-overlay",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    },
}

setup(
    app=APP,
    name="WinterOverlay",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)