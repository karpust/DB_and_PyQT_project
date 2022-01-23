"""
3. Реализовать дескриптор для класса серверного сокета, а в нем — проверку номера порта.

Это должно быть целое число (>=0). Значение порта по умолчанию равняется 7777.
Дескриптор надо создать в отдельном классе. Его экземпляр добавить в пределах
класса серверного сокета. Номер порта передается в экземпляр дескриптора при
запуске сервера.
"""

import logging
LOGGER = logging.getLogger('server')


# Дескриптор порта:
class Port:
    def __set__(self, instance, value):
        # value - адрес порта
        # print('Зашел в дескриптор порта.')
        if not 1023 < value < 65536:
            LOGGER.critical(
                f'Попытка запуска сервера с указанием неподходящего порта {value}. '
                f'Допустимы адреса с 1024 до 65535.')
            exit(1)
        # Если порт прошёл проверку, добавляем его в список атрибутов экземпляра
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        # name - port
        self.name = name

