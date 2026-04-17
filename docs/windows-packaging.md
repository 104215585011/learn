# Windows Packaging

This project already ships as a desktop GUI via `tkinter`.

## Runtime storage

- Source runs keep `floatvocab.db` in the project root.
- Packaged runs store `floatvocab.db` in `%APPDATA%\FloatVocab`.
- On the first packaged launch, a legacy database from the app folder is copied into `%APPDATA%\FloatVocab` when needed.

## Build steps

1. Install build dependency:
   `pip install -r requirements-build.txt`
2. Build the app bundle:
   `python build_exe.py`
3. Compile the installer with Inno Setup:
   open `installer/FloatVocab.iss`

## Installer output

- PyInstaller bundle: `dist/FloatVocab`
- Installer: `dist/installer/FloatVocab-Setup.exe`

## Notes

- Put an icon at `assets/floatvocab.ico` to include it automatically during PyInstaller builds.
- If you change the app version, update `AppVersion` in `installer/FloatVocab.iss`.
