import logging.handlers
import os
import sys

# sys.path.append('../')

# создадим путь для лог файла, чтобы создавался там же где логконфиг:
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'client.log')

# логгер - это регистратор верхнего уровня
# создадим логгер с именем client:
LOG = logging.getLogger('client')

# создадим обработчик который выводит в файл
# все, начиная с уровня DEBUG:
FILE_HANDLER = logging.FileHandler(PATH, encoding="utf-8")
FILE_HANDLER.setLevel(logging.DEBUG)

# создадим обработчик который выводит в stderr
# все начиная с уровня ERROR:
STREAM_HANDLER = logging.StreamHandler(sys.stderr)

# создадим форматтер для создания сообщений в формате
# (здесь нельзя использовать F-строки, только %),
# "<дата-время> <уровеньважности> <имямодуля> <сообщение>":
FORMATTER = logging.Formatter("%(asctime)s - %(levelname)-8s - %(module)s - %(message)s")

# подключаем форматтер к обработчику:
FILE_HANDLER.setFormatter(FORMATTER)

# добавим обработчик к логгеру:
LOG.addHandler(FILE_HANDLER)

# установим логгеру уровень, с которого писать в лог-файл
# логгер будет пропускать все начиная с уровня DEBUG:
LOG.setLevel(logging.DEBUG)


if __name__ == '__main__':
    LOG.debug("Отладочная информация")
    LOG.info("Информационное сообщение")
    LOG.warning("Предупреждение")
    LOG.error("Сообщение об ошибке")
    LOG.critical("Критическое сообщение")

