"""
Написать функцию host_range_ping_tab(), возможности которой основаны на
функции из примера 2. Но в данном случае результат должен быть итоговым
по всем ip-адресам, представленным в табличном формате (использовать
модуль tabulate). Таблица должна состоять из двух колонок и выглядеть
примерно так: hw_1/img.png
"""

from tabulate import tabulate
from task_2 import host_range_ping


def host_range_ping_tab():
    """
    ф-ция принимает список кортежей
    и выводит данные в табличном виде
    """
    dict_lst = host_range_ping()
    print(tabulate(dict_lst, headers='keys', tablefmt='grid'))


if __name__ == '__main__':
    host_range_ping_tab()

