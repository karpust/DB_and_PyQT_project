"""
Написать функцию host_range_ping() для перебора ip-адресов
из заданного диапазона. Меняться должен только последний
октет каждого адреса. По результатам проверки должно
выводиться соответствующее сообщение.
"""

# from task_1 import host_ping, check_is_ip
from task_1_thread import host_ping, check_is_ip


def host_range_ping(make_ping=True):
    """
    ф-ция генерирует ip-адреса из заданного
    диапазона для последнего октета.
    возвращает список строк ip-адресов
    """
    while True:
        start_ip = input('Введите начальный ip-адрес: ')
        start_ip = '192.168.56.1' if start_ip == '' else start_ip
        try:
            start_ipv4 = check_is_ip(start_ip)
            break
        except Exception as e:
            print(e)
    while True:
        try:
            range_ip = input('Введите число, обозначающее диапазон(количество) ip-адресов: ')
            range_ip = 4 if range_ip == '' else int(range_ip)
            break
        except ValueError:
            print('Некоррекное значение')
    last_oct = int(start_ip.split('.')[3])
    if last_oct > 255:
        print(f'Данный диапазон выходит за рамки последнего октета ip-адреса')
    else:
        lst_ip = [str(start_ipv4 + ip) for ip in range(range_ip)]
        if make_ping:
            return host_ping(lst_ip)
        else:
            print(lst_ip)


if __name__ == '__main__':
    host_range_ping(False)

