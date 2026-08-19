import subprocess
import os
import sys
from pathlib import Path
from typing import Optional

# exeとして実行されている場合、自分自身のフォルダを基準にする
if getattr(sys, "frozen", False):
    os.chdir(Path(sys.executable).parent)

MAIN_EXE = str(Path(sys.executable).parent.parent / "mgl79.exe" / "mgl79.exe")


def main():
    process: Optional[subprocess.Popen] = None
    while True:
        if process is not None and process.poll() is not None:
            process = None
        if process is None:
            process = subprocess.Popen([MAIN_EXE])


if __name__ == "__main__":
    main()
