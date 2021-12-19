# This is a sample Python script.
import os
import subprocess
from pathlib import Path

from settings import config

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print(f"Version: {config['version']}")
    print(f"Working dir: {os.getcwd()}")
    if not os.path.exists('output'):
        os.mkdir('output')
        os.mkdir('output/data')
    elif not os.path.exists('output/data'):
        os.mkdir('output/data')

    binary = "blender"
    script = str(Path(config['scriptPath']))
    subprocess.run([binary, "-b", "--python", script])
