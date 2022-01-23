import os
import sys
import logging.handlers

# sys.path.append('../')

# создадим путь для лог файла, чтобы создавался там же где логконфиг:
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'server.log')

# логгер - это регистратор верхнего уровня
# создадим логгер с именем server:
LOG = logging.getLogger('server')

# создадим обработчик который выводит в файл
# все, начиная с уровня DEBUG:
FILE_HANDLER = logging.handlers.TimedRotatingFileHandler(PATH, when='D', interval=1, encoding='utf-8')
FILE_HANDLER.setLevel(logging.DEBUG)

# создадим обработчик который выводит в stderr
# все начиная с уровня ERROR
STREAM_HANDLER = logging.StreamHandler(sys.stderr)
STREAM_HANDLER.setLevel(logging.ERROR)
# создадим форматтер для создания сообщений в формате
# (здесь нельзя использовать F-строки, только %)
# "<дата-время> <уровеньважности> <имямодуля> <сообщение>":
FORMATTER = logging.Formatter("%(asctime)s - %(levelname)-8s - %(module)s - %(message)s")

# подключаем форматтер к обработчикам:
FILE_HANDLER.setFormatter(FORMATTER)
STREAM_HANDLER.setFormatter(FORMATTER)

# добавим обработчики к логгеру:
LOG.addHandler(FILE_HANDLER)
LOG.addHandler(STREAM_HANDLER)

# установим логгеру уровень, с которого писать в лог-файл
# сам логгер будет пропускать все, начиная с DEBUG:
LOG.setLevel(logging.DEBUG)


# для отладки:
if __name__ == "__main__":
    LOG.debug("Отладочная информация")
    LOG.info("Информационное сообщение")
    LOG.warning("Предупреждение")
    LOG.error("Сообщение об ошибке")
    LOG.critical("Критическое сообщение")

