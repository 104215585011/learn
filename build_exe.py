import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILD_ROOT = ROOT / "build"
DIST_ROOT = ROOT / "dist"
ICON_PATH = ROOT / "assets" / "floatvocab.ico"


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "FloatVocab",
        "--distpath",
        str(DIST_ROOT),
        "--workpath",
        str(BUILD_ROOT / "work"),
        "--specpath",
        str(BUILD_ROOT / "spec"),
        "--add-data",
        f"{ROOT / 'data'};data",
    ]
    if ICON_PATH.exists():
        command.extend(["--icon", str(ICON_PATH)])
    command.append(str(ROOT / "app.py"))
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
