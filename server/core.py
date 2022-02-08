import binascii
import hmac
import os
from common.variables import *
import logging
import json
from common.utils import receive_msg, send_msg
import socket
from descriptors import Port
from threading import Thread
from socket import SOL_SOCKET, SO_REUSEADDR
from select import select
import sys
sys.path.append('../')


# cсылка на созданный логгер,
# Инициализация логирования сервера:
logger = logging.getLogger('server')


# класс сервера:
class ServSock(Thread):
    port = Port()

    def __init__(self, address, port, database):
        super().__init__()  # наследуем все от Thread
        # ничего не передаем, тк в родителе все задано по умолчанию
        # параметры подключения:
        self.addr = address
        self.port = port
        # сокеты:
        self.sock = None
        self.listen_sock = None
        self.error_sock = None
        # база данных сервера:
        self.database = database
        # список подключенных клиентов:
        self.clients = []
        # список сообщений на отправку:
        self.messages = []
        # словарь с именами и соотв им сокетами:
        self.names = dict()
        # флаг продолжения работы:
        self.running = True

    def init_socket(self):
        logger.info(
            f'Запущен сервер, порт для подключений: {self.port}, '
            f'адрес с которого принимаются подключения: {self.addr}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)
        self.sock = transport
        self.sock.listen(MAX_CONNECTION)

    def run(self):
        self.init_socket()
        while self.running:  # ждем подключения клиента, если подключится - добавим в список клиентов
            try:
                client, client_addr = self.sock.accept()
            except OSError:  # если таймаут вышел, ловим исключение
                pass
            else:
                logger.debug(f'Сервер соединен с клиентом {client_addr}')
                client.settimeout(5)
                self.clients.append(client)

            recv_data_lst = []  # список клиентов которые получают на чтение
            # send_data_lst = []  # список клиентов которые отправляют
            # err_lst = []  # список клиентов на возврат ошибки

            # проверяем есть ли ожидающие клиенты:
            try:
                if self.clients:
                    recv_data_lst, self.listen_sock, self.error_sock = select(
                        self.clients, self.clients, [], 0)
                    # на чтение, на отправку, на возврат ошибки
            except OSError as err:
                logger.error(f'Ошибка работы с сокетами: {err.errno}')

            # проверяем есть ли получающие клиенты,
            # если есть, то добавим словарь-сообщение в очередь,
            # если нет сообщения - отключим клиента:
            if recv_data_lst:
                for client_with_msg in recv_data_lst:
                    try:
                        self.check_msg(receive_msg(client_with_msg),
                                       client_with_msg)
                    except (OSError, json.JSONDecodeError, TypeError) as err:
                        logger.debug(f'Client exception', exc_info=err)
                        self.remove_client(client_with_msg)

    def remove_client(self, client):
        """
        удаляет клиента с которым прервалась связь
        из списков и базы данных
        """
        logger.info(f'Клиент {client.getpeername()} отключился от сервера.')
        for name in self.names:
            if self.names[name] == client:
                self.database.user_logout(name)
                del self.names[name]
                break
        self.clients.remove(client)
        client.close()

    def send_to_msg(self, message):
        """
        отправка сообщения клиенту
        """
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] \
                in self.listen_sock:
            try:
                send_msg(self.names[message[DESTINATION]], message)
                logger.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                            f'от пользователя {message[SENDER]}')
            except OSError:
                self.remove_client(message[DESTINATION])
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] \
                not in self.listen_sock:
            logger.error(f'Связь с клиентом {message[DESTINATION]} была потеряна.')
            self.remove_client(self.names[message[DESTINATION]])
        else:
            logger.error(f'Пользователь {message[DESTINATION]} не зарегистророван '
                         f'на сервере. Отправка сообщения невозможна.')

    def check_msg(self, message, client):
        """
        обработчик поступающих сообщений
        """
        logger.debug(f'Разбор сообщения от клиента: {message}.')
        # если это сообщение о присутствии, то авторизация:
        if ACTION in message and TIME in message \
                and USER in message and message[ACTION] == PRESENCE:
            self.autorize_user(message, client)

        # если это обычное сообщение, отправим его получателю:
        elif ACTION in message and TIME in message and DESTINATION in message \
                and MESSAGE_TEXT in message and SENDER in message and message[ACTION] == MESSAGE:
            if message[DESTINATION] in self.names:
                # в бд у отправленных и полученных увеличится счетчик на +1:
                self.database.message_transfer(message[SENDER],
                                               message[DESTINATION])
                try:
                    send_msg(client, RESPONSE_200)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Пользователь не зарегистрирован на сервере.'
                try:
                    send_msg(client, response)
                except OSError:
                    pass
            return

        # если клиент выходит:
        elif ACTION in message and ACCOUNT_NAME in message and message[ACTION] == EXIT:
            self.remove_client(client)

        # если это запрос списка контактов:
        elif ACTION in message and USER in message and message[ACTION] == GET_USER_CONTACTS and \
                self.names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_user_contacts(message[USER])
            try:
                send_msg(client, response)
            except OSError:
                self.remove_client(client)

        # если это запрос на добавление контакта:
        elif ACTION in message and USER in message and message[ACTION] == ADD_CONTACT and \
                ACCOUNT_NAME in message and self.names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            try:
                send_msg(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)

        # если это запрос на удаление контакта:
        elif ACTION in message and USER in message and message[ACTION] == DELETE_CONTACT and \
                ACCOUNT_NAME in message and self.names[message[USER]] == client:
            self.database.delete_contact(message[USER], message[ACCOUNT_NAME])
            try:
                send_msg(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)

        # если это запрос всех известных пользователей:
        elif ACTION in message and message[ACTION] == GET_USERS and \
                ACCOUNT_NAME in message and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0] for user in self.database.all_users_list()]
            try:
                send_msg(client, response)
            except OSError:
                self.remove_client(client)

        # если это запрос публичного ключа пользователя:
        elif ACTION in message and ACCOUNT_NAME in message and \
                message[ACTION] == PUBLIC_KEY_REQUEST:
            response = RESPONSE_511
            response[DATA] = self.database.get_pubkey(message[ACCOUNT_NAME])
            # если пользователь не логинился еще то ключа нет:
            if response[DATA]:
                try:
                    send_msg(client, response)
                except OSError:
                    self.remove_client(client)
            else:
                responce = RESPONSE_400
                responce[ERROR] = 'Нет публичного ключа для данного пользователя'
                try:
                    send_msg(client, response)
                except OSError:
                    self.remove_client(client)
        # если непонятно какой запрос:
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен'
            try:
                send_msg(client, response)
            except OSError:
                self.remove_client(client)

    def autorize_user(self, message, client):
        """
        авторизация пользователей
        """
        logger.debug(f'Start authorization process for client {message[USER][ACCOUNT_NAME]}')
        # если имя пользователя уже занято:
        if message[USER][ACCOUNT_NAME] in self.names.keys():
            response = RESPONSE_400
            response[ERROR] = 'Username is already taken'
            logger.debug(f'Response by {message[USER][ACCOUNT_NAME]}: {response}')
            try:
                send_msg(client, response)
            except OSError:
                logger.debug('OS Error')
                pass
            self.clients.remove(client)
            client.close()
        # проверка зарегистрирован ли пользователь на сервере:
        elif not self.database.check_user(message[USER][ACCOUNT_NAME]):
            response = RESPONSE_400
            response[ERROR] = 'User not registered'
            logger.debug(f'Unknown username, {response}')
            try:
                send_msg(client, response)
            except OSError:
                pass
            self.clients.remove(client)
            client.close()

        # иначе проводим авторизацию пользователя:
        else:
            logger.debug('Correct username, starting authorisation')
            message_auth = RESPONSE_511
            # набора байтов в hex-представлении:
            random_str = binascii.hexlify(os.urandom(64))
            # декодируем, в словарь байты нельзя:
            message_auth[DATA] = random_str.decode('ascii')
            # создаем хэш из пароля с рандомной строкой:
            hash_auth = hmac.new(
                self.database.get_hash(message[USER][ACCOUNT_NAME]),
                random_str, 'MD5')
            digest = hash_auth.digest()
            logger.debug(f'Auth message: {message_auth}')
            try:
                send_msg(client, message_auth)
                ans = receive_msg(client)
            except OSError as err:
                logger.debug('Error in authorisation, data: ', exc_info=err)
                client.close()
                return
            client_digest = binascii.a2b_base64(ans[DATA])

            # если ответ клиента корректен:
            if RESPONSE in ans and ans[RESPONSE] == 511 and \
                    hmac.compare_digest(digest, client_digest):
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                try:
                    send_msg(client, RESPONSE_200)
                except OSError:
                    self.remove_client(message[USER][ACCOUNT_NAME])

                # добавляем пользователя в список активных:
                self.database.user_login(
                    message[USER][ACCOUNT_NAME],
                    client_ip,
                    client_port,
                    message[USER][PUBLIC_KEY]
                )
            # если некорректен:
            else:
                response = RESPONSE_400
                response[ERROR] = 'Invalid password'
                try:
                    send_msg(client, response)
                except OSError:
                    pass
                self.clients.remove(client)
                client.close()

    def service_update_lists(self):
        """
        Отправка клиентам сообщения 205
        """
        for client in self.names:
            try:
                send_msg(self.names[client], RESPONSE_205)
            except OSError:
                self.remove_client(self.names[client])
