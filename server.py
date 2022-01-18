import argparse
import sys
from ipaddress import ip_address
from select import select
from common.variables import *
from socket import SOL_SOCKET, SO_REUSEADDR
import logging
import logs.server_log_config
from decos import log
from common.utils import recieve_msg, send_msg
import socket
from metaclasses import ServerVerifier
from descriptors import Port
from threading import Thread
from server_database import ServerDb


# cсылка на созданный логгер,
# Инициализация логирования сервера:
SERVER_LOGGER = logging.getLogger('server')


@log
def cmd_arg_parse():
    """
    Парсер аргументов коммандной строки
    """
    parser = argparse.ArgumentParser()  # создаем объект парсер
    # описываем аргументы которые парсер будет считывать из cmd:
    parser.add_argument('-p', default=8888, type=int, nargs='?')  # описываем именные аргументы
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


# класс сервера:
class ServSock(Thread, metaclass=ServerVerifier):
    listen_port = Port()

    def __init__(self, address, port, database):
        super().__init__()  # наследуем все от Thread
        # ничего не передаем, тк в родителе все задано по умолчанию
        # параметры подключения:
        self.listen_address = address
        self.listen_port = port
        # сокет:
        self.sock = self.init_socket()
        # база данных сервера:
        self.database = database
        # список подключенных клиентов:
        self.clients = []
        # список сообщений на отправку:
        self.messages = []
        # словарь с именами и соотв им сокетами:
        self.names = dict()

    def init_socket(self):
        SERVER_LOGGER.info(
            f'Запущен сервер, порт для подключений: {self.listen_address}, '
            f'адрес с которого принимаются подключения: {self.listen_port}.'
            f' Если адрес не указан, принимаются соединения с любых адресов.')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        sock.bind((self.listen_address, self.listen_port))
        sock.settimeout(0.5)
        sock.listen(MAX_CONNECTION)
        return sock

    @log
    def run(self):
        SERVER_LOGGER.debug('Сервер в ожидании клиента')
        while True:  # ждем подключения клиента, если подключится - добавим в список клиентов
            try:
                print('-------------------------------------accept-------------------------------')
                client, client_addr = self.sock.accept()
            except OSError:  # если таймаут вышел, ловим исключение
                pass
            else:
                self.clients.append(client)
                SERVER_LOGGER.debug(f'Сервер соединен с клиентом {client_addr}')
            recv_data_lst = []  # список клиентов которые получают на чтение
            send_data_lst = []  # список клиентов которые отправляют
            err_lst = []  # список клиентов на возврат ошибки

            # проверяем есть ли ожидающие клиенты:
            try:
                if self.clients:
                    recv_data_lst, send_data_lst, err_lst = select(self.clients, self.clients, [], 0)
                    # на чтение, на отправку, на возврат ошибки
            except OSError:
                pass

            # проверяем есть ли получающие клиенты,
            # если есть, то добавим словарь-сообщение в очередь,
            # если нет сообщения - отключим клиента:
            if recv_data_lst:
                for client_with_msg in recv_data_lst:
                    try:
                        self.check_msg(recieve_msg(client_with_msg), self.messages,
                                       client_with_msg, self.clients, self.names)
                    except Exception:
                        SERVER_LOGGER.info(f'Клиент {client_with_msg.getpeername()} '
                                           f'отключен от сервера.')
                        self.clients.remove(client_with_msg)

            # если есть сообщения то обрабатываем каждое:
            for msg in self.messages:
                try:
                    self.send_to_msg(msg, self.names, send_data_lst)
                except Exception:
                    SERVER_LOGGER.info(f'Связь с клиентом с именем {msg[DESTINATION]} была потеряна ')
                    self.clients.remove(self.names[msg[DESTINATION]])
                    del self.names[msg[DESTINATION]]
                self.messages.clear()

    @log
    def check_msg(self, message, client):
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
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
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
            self.messages.append(message)
            return
        # если клиент выходит:
        elif ACTION in message and ACCOUNT_NAME in message and message[ACTION] == EXIT:
            self.database.user_logout(message[ACCOUNT_NAME])
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            return
        else:
            response = RESPONSE_400
            response[ERROR] = 'запрос не корректен'
            send_msg(client, response)
            return

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
    database = ServerDb()
    server = ServSock(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    while True:
        command = input('Введите команду: ')
        if command == 'help':
            print('Поддерживаемые комманды:')
            print('users - список известных пользователей')
            print('connected - список подключённых пользователей')
            print('loghist - история входов пользователя')
            print('exit - завершение работы сервера.')
            print('help - вывод справки по поддерживаемым командам')
        elif command == 'exit':
            break
        elif command == 'users':
            for user in sorted(database.all_users_list()):
                print(f'Пользователь {user[0]}, последний вход: {user[1]}')
        elif command == 'connected':
            for user in sorted(database.active_users_list()):
                print(f'Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}')
        elif command == 'loghist':
            name = input('Введите имя пользователя для просмотра истории. '
                         'Для вывода всей истории, просто нажмите Enter: ')
            for user in sorted(database.login_history()):
                print(f'Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}')
        else:
            print('Команда не распознана.')


if __name__ == '__main__':
    main()





