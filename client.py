import argparse
import json
import sys
import time
from common.variables import *
import logging
import logs.client_log_config
from errors import *
from decos import log
import socket
from common.utils import recieve_msg, send_msg
from metaclasses import ClientVerifier
from threading import Thread

CLIENT_LOGGER = logging.getLogger('client')


class ClientSender(Thread, metaclass=ClientVerifier):
    def __init__(self, name_account, sock):
        super().__init__()
        self.name_account = name_account
        self.sock = self.init_sock()

    def init_sock(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return sock

    @log
    def create_exit_msg(self):
        """
        Создает сообщение(словарь)
        о выходе клиента
        """
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.name_account
        }

    @log
    def create_message_msg(self):
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
            SENDER: self.name_account
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения {message}')
        try:
            send_msg(self.sock, message)  # что это за сокет, откуда или кому ?  это сокет клиента
            CLIENT_LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
        except:
            CLIENT_LOGGER.critical('Потеряно соединение с сервером')
            sys.exit(1)

    def users_interplay(self):
        """
        Осуществляет взаимодействие пользователей:
        запрашивает команды, отправляет сообщения
        """
        self.output_help()  # сначала выводим справку
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message_msg()
            elif command == 'help':
                self.output_help()
            elif command == 'exit':
                print('Завершение работы')
                send_msg(self.sock, self.create_exit_msg())
                CLIENT_LOGGER.info(f'Пользователь завершил работу')
                time.sleep(0.5)  # задержка чтобы успело уйти сообщение
                break
            else:
                print('Неизвестная команда, попробуйте снова. Для справки введите \'help\'.')

    def output_help(self):
        """Функция выводящяя справку по использованию"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')


class ClientReader(Thread, metaclass=ClientVerifier):
    def __init__(self, name_account, sock):
        super().__init__()
        self.name_account = name_account
        self.sock = sock
        self.sock = self.init_sock()

    def init_sock(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return sock

    @log
    def check_messages_by_server(self):
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
                        and message[ACTION] == MESSAGE and message[DESTINATION] == self.name_account:
                    print(f'Получено сообщение от пользователя {message[SENDER]}: '
                          f'{message[MESSAGE_TEXT]}')
                    CLIENT_LOGGER.info(f'Получено сообщение от пользователя {message[SENDER]}: '
                                       f'{message[MESSAGE_TEXT]}')
                else:
                    CLIENT_LOGGER.error(f'От сервера получено некорректное сообщение {message}:')
            except IncorrectDataRecievedError:  # почему на некорректных данных не прервались ?
                CLIENT_LOGGER.error(f'Не удалось декодировать полученное сообщение')
            except (OSError, ConnectionAbortedError, ConnectionError,
                    ConnectionResetError, json.JSONDecodeError):
                CLIENT_LOGGER.critical(f'Потеряно соединение с сервером')
                break


@log
def create_presence_msg(name_account):
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
def cmd_arg_parse():  # sys.argv = ['client.py', '127.0.0.1', 8888]
    """
    Парсер аргументов коммандной строки
    """
    parser = argparse.ArgumentParser()  # создаем объект парсер
    parser.add_argument('addr', default='127.0.0.1', nargs='?')  # описываем позиционные аргументы
    parser.add_argument('port', default=7777, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    if server_port < 1024 or server_port > 65535:
        CLIENT_LOGGER.critical(f'Попытка запуска клиента с указанием порта: {server_port}. '
                               f'Адрес порта должен быть в диапазоне от 1024 до 65535')
        sys.exit(1)
    return server_address, server_port, client_name





@log
def main():
    # Загружаем параметы коммандной строки:
    server_address, server_port, client_name = cmd_arg_parse()

    print(f'Консольный мессенджер. Клиентский модуль. Имя пользователя: {client_name}')
    if not client_name:  # если имя пользователя не было задано, запросить
        client_name = input('Введите имя пользователя: ')

    CLIENT_LOGGER.info(f'Запущен клиент с параметрами: адрес сервера: {server_address}, '
                       f'порт {server_port}, имя пользователя: {client_name}.')

    # соединение с сервером:
    try:
        # sock - это абстрактный сокет!!!!!
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_address, server_port))
        client_msg = create_presence_msg(client_name)
        send_msg(sock, client_msg)
        server_msg = recieve_msg(sock)
        server_ans = check_server_msg(server_msg)
        CLIENT_LOGGER.info(f'Установлено соединение с сервером, ответ сервера: {server_ans}')
        print(f'Установлено соединение с сервером.')
    except FieldMissingError as missing_err:
        CLIENT_LOGGER.critical(f'В ответе сервера отсутствует необходимое поле:'
                               f'{missing_err.miss_field}')
        sys.exit(1)
    except json.JSONDecodeError:
        CLIENT_LOGGER.error(f'Клиенту не удалось декодировать json-строку, полученную от сервера')
        sys.exit(1)
    except ServerError as error:
        CLIENT_LOGGER.error(f'При установке соединения сервер вернул ошибку {error.text}')
    except (ConnectionRefusedError, ConnectionError):
        CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {server_address}:{server_port}. '
                               f'Конечный узел отверг запрос на подключение')
        sys.exit(1)
    else:
        # если соединение с сервером установлено корректно,
        # то запускаем клиентский поток приема сообщений:
        reciever = ClientReader(client_name, sock)
        reciever.daemon = True
        reciever.start()

        # запускаем поток отправки сообщений и взаимодействия с пользователем:
        sender = ClientSender(client_name, sock)
        sender.daemon = True
        sender.start()
        CLIENT_LOGGER.debug('Запущены процессы')

        # основной цикл:
        # если один из потоков завершен, значит или
        # потеряно соединение или пользователь ввел exit()
        while True:
            time.sleep(1)
            if reciever.is_alive() and sender.is_alive():
                continue
            break


if __name__ == '__main__':
    main()


