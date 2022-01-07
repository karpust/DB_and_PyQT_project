"""Получение кода завершения подпроцесса"""

import platform
from subprocess import Popen

PROGRAM = 'regedit.exe' if platform.system().lower() == 'windows' else 'libreoffice'
PROCESS = Popen(PROGRAM)
