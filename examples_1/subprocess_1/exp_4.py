"""Связь с дочерним процессом"""
import platform
from subprocess import Popen, PIPE, STDOUT
import chardet

PARAM = "-n" if platform.system().lower() == 'windows' else "-c"
ARGS = ["ping", PARAM, "2", "google.com"]
process = Popen(ARGS, stdout=PIPE, stderr=STDOUT)

# communicate - связь с созданным процессом
# None – это результат stderr, а это значит, что ошибок не найдено
stdout_data, stderr_data = process.communicate()
print('stdout_data: ', stdout_data)
print('stderr_data: ', stderr_data)

result = chardet.detect(stdout_data)
out = stdout_data.decode(result['encoding'])
print(out)
