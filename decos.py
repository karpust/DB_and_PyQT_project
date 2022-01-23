import inspect
import logging
import sys
import traceback
import logs.server_log_config
import logs.client_log_config
from functools import wraps


def log(func):
    """это декоратор"""
    @wraps(func)  # возвращает имя функции и ее докстринг, но здесь не нужно т.к. к имени обращаемся из обертки?
    def wrapper(*args, **kwargs):
        """это обертка"""
        # определим к какому модулю относится декорируемая ф-я
        # чтобы понять какой регистратор использовать
        if sys.argv[0].find('server.py') == -1:  # если строка не найдена find вернет -1
            LOGGER = logging.getLogger('client')
        else:
            LOGGER = logging.getLogger('server')

        f = func(*args, **kwargs)
        LOGGER.debug(f'Вызов функции {func.__name__} из модуля {func.__module__}. '
                     f'Эта функция вызвана с параметрами {args}, {kwargs}. '
                     f'Функция {func.__name__} вызывается из функции '
                     f'{traceback.format_stack()[0].split()[-1]} ')
                     # f'Вызов из функции {inspect.stack()[1][3]}')  # получение родительской ф-ции вариант 2
        return f
    return wrapper



