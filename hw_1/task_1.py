"""
Написать функцию host_ping(), в которой с помощью утилиты ping будет
проверяться доступность сетевых узлов. Аргументом функции является список,
в котором каждый сетевой узел должен быть представлен именем хоста или
ip-адресом. В функции необходимо перебирать ip-адреса и проверять их
доступность с выводом соответствующего сообщения («Узел доступен»,
«Узел недоступен»). При этом ip-адрес сетевого узла должен создаваться
с помощью функции ip_address().
"""
import os
import platform
from ipaddress import ip_address
from subprocess import Popen, PIPE
import time


DNULL = open(os.devnull, 'w')  # заглушка, чтобы поток не выводился на экран


def check_is_ip(ip):
    """
    ф-ция проверяет ip на корректность,
    возвращает экз. класса ipaddress.IPv4Address
    """
    try:
        ipv4 = ip_address(ip)
    except ValueError:
        raise Exception('некорректный ip-адрес')  # выйти
    return ipv4


def host_ping(lst_ip, print_is_reach=False):
    """
    ф-ция проверяет досупнось сетевых узлов.
    принимает список сетевых узлов
    """
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    tested_dict = dict(Reachable=[], Unreachable=[])
    for addr in lst_ip:
        ip = None
        try:
            ip = str(check_is_ip(addr))
        except Exception as e:
            print(f'{addr} - {e}: доменное имя')
            ip = addr
        finally:
            args = ['ping', param, '2', ip]
            reply = Popen(args, stdout=PIPE, stderr=PIPE)
            if reply.wait() == 0:
                if print_is_reach:
                    print(f'Узел доступен {ip}')
                else:
                    tested_dict['Reachable'].append(ip)
            else:
                if print_is_reach:
                    print(f'Узел недоступен {ip}')
                else:
                    tested_dict['Unreachable'].append(ip)
    if not print_is_reach:
        return tested_dict


if __name__ == '__main__':
    # lst = ['yandex.ru', '192.168.56.1', '0.8.8.8']
    # host_ping(lst, True)

    hosts_list = ['192.168.56.1', '8.8.8.8', 'yandex.ru', 'google.com',
                  '0.0.0.1', '0.0.0.2', '0.0.0.3', '0.0.0.4', '0.0.0.5',
                  '0.0.0.6', '0.0.0.7', '0.0.0.8', '0.0.0.9', '0.0.1.0']
    start = time.time()
    host_ping(hosts_list, True)
    end = time.time()
    print(f'total time: {int(end - start)}')


