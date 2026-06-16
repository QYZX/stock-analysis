import subprocess
import platform


def clear_screen():
    cmd = 'cls' if platform.system() == 'Windows' else 'clear'
    subprocess.run(cmd, shell=True)