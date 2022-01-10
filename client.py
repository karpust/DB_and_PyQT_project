import argparse
import json
import sys
import threading
import time
from common.variables import ACTION, PRESENCE, TIME, TYPE, STATUS, USER, \
    ACCOUNT_NAME, RESPONSE, ERROR, CLIENT_ADDRESS_DEFAULT, PORT_DEFAULT, \
    MESSAGE, MESSAGE_TEXT, SENDER, EXIT, DESTINATION
from ipaddress import ip_address
import logging
import logs.client_log_config
from errors import *
from decos import log
import socket
from common.utils import recieve_msg, send_msg
from metaclasses import ClientVerifier

CLIENT_LOGGER = logging.getLogger('client')


class ClientSock(metaclass=ClientVerifier):
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = None
        self.server_port = None
        self.client_name = None

    @log
    def create_exit_msg(self, name_account):
        """
        Создает сообщение(словарь)
        о выходе клиента
        """
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: name_account
        }

    @log
    def check_messages_by_server(self, user_name):
        """
        Обрабатывает сообщения других
        пользователей, которые приходят с сервера
        обязятельно должны быть и отправитель и получатель
        """
        while True:
            try:
                message = recieve_msg(self.sock)
                if ACTION in message and SENDER in message \
                    and DESTINATION in message and MESSAGE_TEXT in message \
                        and message[ACTION] == MESSAGE and message[DESTINATION] == user_name:
                    print(f'Получено сообщение от пользователя {message[SENDER]}: '
                          f'{message[MESSAGE_TEXT]}')
                    CLIENT_LOGGER.info(f'Получено сообщение от пользователя {message[SENDER]}: '
                                       f'{message[MESSAGE_TEXT]}')
                else:
                    CLIENT_LOGGER.error(f'От сервера получено некорректное сообщение {message}:')
            except IncorrectDataRecievedError:                              # почему на некорректных данных не прервались ?
                CLIENT_LOGGER.error(f'Не удалось декодировать полученное сообщение')
            except (OSError, ConnectionAbortedError, ConnectionError,
                    ConnectionResetError, json.JSONDecodeError):
                CLIENT_LOGGER.critical(f'Потеряно соединение с сервером')
                break

    @log
    def create_message_msg(self, name_account='Guest'):
        """
        Создает сообщение(словарь) для
        отправки другому пользователю
        """

        to_user = input('Введите имя получателя: ')
        msg = input('Введите текст сообщения: ')
        message = {
            ACTION: MESSAGE,
            TIME: time.time(),
            MESSAGE_TEXT: msg,
            DESTINATION: to_user,
            SENDER: name_account
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения {message}')
        try:
            send_msg(self.sock, message)              # что это за сокет, откуда или кому ?  это сокет клиента
            CLIENT_LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
        except:
            CLIENT_LOGGER.critical('Потеряно соединение с сервером')
            sys.exit(1)

    def users_interplay(self, user_name):
        """
        Осуществляет взаимодействие пользователей:
        запрашивает команды, отправляет сообщения
        """
        self.output_help()  # сначала выводим справку
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message_msg(user_name)
            elif command == 'help':
                self.output_help()
            elif command == 'exit':
                print('Завершение работы')
                send_msg(self.sock, self.create_exit_msg(user_name))
                CLIENT_LOGGER.info(f'Пользователь {user_name} завершил работу')
                time.sleep(0.5)  # задержка чтобы успело уйти сообщение
                break
            else:
                print('Неизвестная команда, попробуйте снова. Для справки введите \'help\'.')

    @staticmethod
    def output_help():
        """Функция выводящяя справку по использованию"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

    @staticmethod
    @log
    def create_presence_msg(name_account='Guest'):
        """
        Создает сообщение-присутствие(словарь),
        подтверждающее, что пользоватьель онлайн.
        """
        presence_msg = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: name_account,
            }
        }
        CLIENT_LOGGER.debug(f'Создано сообщение {presence_msg} пользователя {name_account}')
        return presence_msg

    @staticmethod
    @log
    def check_server_msg(server_msg):
        """
        Проверяет сообщение от сервера
        возвращает ответ-строку
        """
        CLIENT_LOGGER.debug(f'Разбор сообщения от сервера {server_msg}')
        if RESPONSE in server_msg:
            if server_msg[RESPONSE] == 200:
                return '200: OK'
            elif server_msg[RESPONSE] == 400:
                raise ServerError(f'400 : {server_msg[ERROR]}')
        raise FieldMissingError(RESPONSE)

    @log
    def cmd_arg_parse(self):  # sys.argv = ['client.py', '127.0.0.1', 8888]
        parser = argparse.ArgumentParser()  # создаем объект парсер
        parser.add_argument('addr', default='127.0.0.1', nargs='?')  # описываем позиционные аргументы
        parser.add_argument('port', default=7777, type=int, nargs='?')
        parser.add_argument('-n', '--name', default=None, nargs='?')
        namespace = parser.parse_args(sys.argv[1:])
        server_address = namespace.addr
        server_port = namespace.port
        client_name = namespace.name

        try:
            ip_address(server_address)
        except ValueError:
            CLIENT_LOGGER.critical(f'Попытка запуска клиента с указанием ip-адреса {server_address}. '
                                   f'Адрес некорректен')
            sys.exit(1)

        if server_port < 1024 or server_port > 65535:
            CLIENT_LOGGER.critical(f'Попытка запуска клиента с указанием порта: {server_port}. '
                                   f'Адрес порта должен быть в диапазоне от 1024 до 65535')
            sys.exit(1)
        return server_address, server_port, client_name

    @log
    def client_connect(self):
        # Загружаем параметы коммандной строки:
        self.server_address, self.server_port, self.client_name = self.cmd_arg_parse()

        print(f'Консольный мессенджер. Клиентский модуль. Имя пользователя: {self.client_name}')
        if not self.client_name:  # если имя пользователя не было задано, запросить
            self.client_name = input('Введите имя пользователя: ')

        CLIENT_LOGGER.info(f'Запущен клиент с параметрами: адрес сервера: {self.server_address}, '
                           f'порт {self.server_port}, имя пользователя: {self.client_name}.')
        
        # соединение с сервером:
        try:
            self.sock.connect((self.server_address, self.server_port))
            client_msg = self.create_presence_msg(self.client_name)
            send_msg(self.sock, client_msg)
            server_msg = recieve_msg(self.sock)
            server_ans = self.check_server_msg(server_msg)
            CLIENT_LOGGER.info(f'Установлено соединение с сервером, ответ сервера: {server_ans}')
        except FieldMissingError as missing_err:
            CLIENT_LOGGER.critical(f'В ответе сервера отсутствует необходимое поле:'
                                   f'{missing_err.miss_field}')
            sys.exit(1)
        except json.JSONDecodeError:
            CLIENT_LOGGER.error(f'Клиенту не удалось декодировать json-строку, полученную от сервера')
            sys.exit(1)
        except ServerError as error:
            CLIENT_LOGGER.error(f'При установке соединения сервер вернул ошибку {error.text}')
        except IncorrectDataRecievedError:
            CLIENT_LOGGER.error(f'Серверу не удалось обработать сообщение от клиента {self}. '
                                f'Соединение разорвано.')
            sys.exit(1)
        except (ConnectionRefusedError, ConnectionError):
            CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {self.server_address}:{self.server_port}. '
                                   f'Конечный узел отверг запрос на подключение')
            sys.exit(1)
        # except NotDictInputError as dict_err:
        #     CLIENT_LOGGER.error(f'Полученное клиентом сообщение {dict_err.not_dict} не является словарем. ')
        #     sys.exit(1)

        # если соединение с сервером установлено корректно,
        # то запускаем клиентский поток приема сообщений:
        reciever = threading.Thread(target=self.check_messages_by_server, args=(self.client_name, ))
        reciever.daemon = True
        reciever.start()

        # запускаем поток отправки сообщений и взаимодействия с пользователем:
        user_interface = threading.Thread(target=self.users_interplay, args=(self.client_name, ))
        user_interface.daemon = True
        user_interface.start()
        CLIENT_LOGGER.debug('Запущены процессы')

        # основной цикл:
        # если один из потоков завершен, значит или
        # потеряно соединение или пользователь ввел exit()
        while True:
            time.sleep(1)
            if reciever.is_alive() and user_interface.is_alive():
                continue
            break


client = ClientSock()

if __name__ == '__main__':
    client.client_connect()


