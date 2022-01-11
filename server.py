import argparse
import sys
import time
from ipaddress import ip_address
from select import select
from common.variables import ACTION, TIME, USER, PRESENCE, ACCOUNT_NAME, RESPONSE, ERROR, \
    MAX_CONNECTION, PORT_DEFAULT, SERVER_ADDRESS_DEFAULT, MESSAGE, MESSAGE_TEXT, SENDER, \
    DESTINATION, EXIT, RESPONSE_200, RESPONSE_400
from socket import SOL_SOCKET, SO_REUSEADDR
import logging
import logs.server_log_config
import json
from errors import *
from decos import log
from common.utils import recieve_msg, send_msg
import socket
from metaclasses import ServerVerifier
from descriptors import Port


# cсылка на созданный логгер:
SERVER_LOGGER = logging.getLogger('server')


@log
def cmd_arg_parse():
    """
    Парсер аргументов коммандной строки
    """
    parser = argparse.ArgumentParser()  # создаем объект парсер
    # описываем аргументы которые парсер будет считывать из cmd:
    parser.add_argument('-p', default=7777, type=int, nargs='?')  # описываем именные аргументы
    parser.add_argument('-a', default='', nargs='?')
    # nargs='?' значит: если присутствует один аргумент – он будет сохранён,
    # иначе – будет использовано значение из ключа default
    namespace = parser.parse_args(sys.argv[1:])  # все кроме имени скрипта
    listen_address = namespace.a
    listen_port = namespace.p

    if listen_address != '':
        try:
            ip_address(listen_address)
        except ValueError:
            SERVER_LOGGER.critical(f'Попытка запуска сервера с указанием ip-адреса {listen_address}. '
                                   f'Адрес некорректен')
            sys.exit(1)
    SERVER_LOGGER.info(f'Сервер запущен: ip-адрес для подключений: {listen_address}, '
                       f'номер порта для подключений: {listen_port}')
    return listen_address, listen_port


class ServSock(metaclass=ServerVerifier):  # metaclass=ServerVerifier
    listen_port = Port()

    def __init__(self, address, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_address = address
        self.listen_port = port

    @log
    def check_msg(self, message, message_lst, client, clients, names):
        """
        проверяет сообщение клиента:
        если это сообщение о присутствии - отправить ответ клиенту,
        если это сообщение др клиенту - добавить сообщение в очередь
        """
        # если это сообщение о присутствии и ок, ответим {RESPONSE: 200}
        SERVER_LOGGER.debug(f'Разбор сообщения от клиента {message}.')
        if ACTION in message and TIME in message \
                and USER in message and message[ACTION] == PRESENCE:
            # если такой пользователь еще не зарегистрирован,
            # регистрируем иначе ошибка:
            if message[USER][ACCOUNT_NAME] not in names.keys():
                names[message[USER][ACCOUNT_NAME]] = client
                send_msg(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_msg(client, response)
                client.remove(client)
                client.close()
            return
        # если это обычное сообщение, добавим его в очередь
        elif ACTION in message and TIME in message and DESTINATION in message \
                and MESSAGE_TEXT in message and SENDER in message and message[ACTION] == MESSAGE:
            message_lst.append(message)
            return
        # если клиент выходит:
        elif ACTION in message and ACCOUNT_NAME in message and message[ACTION] == EXIT:
            clients.remove(names[message[ACCOUNT_NAME]])
            names[message[ACCOUNT_NAME]].close()
            del names[message[ACCOUNT_NAME]]
            return
        else:
            response = RESPONSE_400
            response[ERROR] = 'запрос не корректен'
            send_msg(client, response)
            return

    @log
    def server_connect(self):  # сервер, клиент
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.sock.bind((self.listen_address, self.listen_port))
        self.sock.settimeout(1)  # будет ждать подключений указанное время
        self.sock.listen(MAX_CONNECTION)
        SERVER_LOGGER.debug('Сервер в ожидании клиента')

        clients = []  # список клиентов
        messages = []  # очередь сообщений
        names = dict()  # словарь с именами клиентов

        while True:  # ждем подключения клиента, если подключится - добавим в список клиентов
            try:
                client, client_addr = self.sock.accept()
            except OSError:  # если таймаут вышел, ловим исключение
                pass
            else:
                clients.append(client)
                SERVER_LOGGER.debug(f'Сервер соединен с клиентом {client_addr}')
            recv_data_lst = []  # список клиентов которые получают на чтение
            send_data_lst = []  # список клиентов которые отправляют
            err_lst = []  # список клиентов на возврат ошибки

            # проверяем есть ли ожидающие клиенты:
            try:
                if clients:
                    recv_data_lst, send_data_lst, err_lst = select(clients, clients, [], 0)
                    # на чтение, на отправку, на возврат ошибки
            except OSError:
                pass

            # проверяем есть ли получающие клиенты,
            # если есть, то добавим словарь-сообщение в очередь,
            # если нет сообщения - отключим клиента:
            if recv_data_lst:
                for client_with_msg in recv_data_lst:
                    try:
                        self.check_msg(recieve_msg(client_with_msg), messages, client_with_msg, clients, names)
                    except Exception:
                        SERVER_LOGGER.info(f'Клиент {client_with_msg.getpeername()} '
                                           f'отключен от сервера.')
                        clients.remove(client_with_msg)

            # если есть сообщения то обрабатываем каждое:
            for msg in messages:
                try:
                    self.send_to_msg(msg, names, send_data_lst)
                except Exception:
                    SERVER_LOGGER.info(f'Связь с клиентом с именем {msg[DESTINATION]} была потеряна ')
                    clients.remove(names[msg[DESTINATION]])
                    del names[msg[DESTINATION]]
                messages.clear()

    @log
    def send_to_msg(self, message, names, listen_socks):
        """
        функция адресной отправки сообщения конкретному клиенту.
        принимает словарь-сообщение, список зарегистрированных пользователей
        и слушающие сокеты. Ничего не возвращает.
        """
        if message[DESTINATION] in names and names[message[DESTINATION]] in listen_socks:
            send_msg(names[message[DESTINATION]], message)
            SERVER_LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                               f'от пользователя {message[SENDER]}')
        elif message[DESTINATION] in names and names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            SERVER_LOGGER.error(f'Пользователь {message[DESTINATION]} не зарегистророван '
                                f'на сервере. Отправка сообщения невозможна.')


def main():
    listen_address, listen_port = cmd_arg_parse()
    server = ServSock(listen_address, listen_port)
    server.server_connect()


if __name__ == '__main__':
    main()





