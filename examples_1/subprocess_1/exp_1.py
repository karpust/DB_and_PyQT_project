"""Дочерний процесс запуска консольной команды"""
import platform
from subprocess import call, Popen, PIPE
import chardet

# Класс subprocess.Popen() - Выполняет программу в новом процессе
# Popen не дожидается конца выполнения вызванного процесса
# (он завершается, а запущенное приложение 'висит')

# stdin и stdout это файлоподобные объекты, предоставляемые OS.
# stdout=PIPE - стандартный поток вывода
# вывод результатов выполнения команды с декодированием

# shell=True - выполнение кода через оболочку

COMMAND = 'dir' if platform.system().lower() == 'windows' else 'ls'

# мы не знаем в чем нужно декодировать
# но нам помогает модуль chardet
PROC = Popen(COMMAND, shell=True, stdout=PIPE)
DATA = PROC.stdout.read()
RESULT = chardet.detect(DATA)
print(RESULT)
OUT = DATA.decode(RESULT['encoding'])
print(OUT)

# Popen поддерживает менеджеры контекста
with Popen(COMMAND, shell=True, stdout=PIPE) as p:
    out = p.stdout.read().decode(RESULT['encoding'])
    print(out)
