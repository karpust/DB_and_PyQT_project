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
from threading import Thread, Lock

CLIENT_LOGGER = logging.getLogger('client')

# Объект блокировки сокета и работы с базой данных:
sock_lock = Lock()
db_lock = Lock()


class ClientSender(Thread, metaclass=ClientVerifier):
    # Класс создания и отправки сообщений на сервер и взаимодействия с пользователем.
    def __init__(self, name_account, sock, database):
        super().__init__()
        self.name_account = name_account
        self.sock = sock
        self.database = database

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

        # проверка что получатель существует:
        with db_lock:
            if not self.database.check_user(to_user):
                CLIENT_LOGGER.error(f'Попытка отправить сообщение незарегистрированому получателю: {to}')
                return
        message = {
            ACTION: MESSAGE,
            TIME: time.time(),
            MESSAGE_TEXT: msg,
            DESTINATION: to_user,
            SENDER: self.name_account
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения {message}')
        # сохраняем сообщения для истории:
        with db_lock:
            self.database.s
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


def contact_list_req(sock, name):
    """
    ф-ция запроса списка контактов
    """
    CLIENT_LOGGER.debug(f'Запрос контакт листа для пользователя {name}')
    req = {
        ACTION: GET_USER_CONTACTS,
        TIME: time.time(),
        USER: name
    }
    CLIENT_LOGGER.debug(f'Сформирован запрос {req}')
    send_msg(sock, req)
    ans = recieve_msg(sock)
    CLIENT_LOGGER.debug(f'Получен ответ {ans}')
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


def add_contact(sock, username, contact):
    """
    ф-ция добавления юзера в список контактов
    """
    CLIENT_LOGGER.debug(f'Создание контакта {contact}')
    req = {
        ACTION: ADD_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_msg(sock, req)
    ans = recieve_msg(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Не удалось создать контакт. Ошибка')
    print('Создан новый контакт')


def user_list_req(sock, username):
    """
    ф-ция запроса всех юзеров
    """
    CLIENT_LOGGER.debug(f'Запрос списка всех пользователей {username}')
    req = {
        ACTION: GET_USERS,
        TIME: time.time(),
        ACCOUNT_NAME: username
    }
    send_msg(sock, req)
    ans = recieve_msg(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        return ans[LIST_INFO]
    else:
        raise ServerError


def delete_contact(sock, username, contact):
    """
    ф-ция удаления юзера из списка контактов
    """
    CLIENT_LOGGER.debug(f'Создание контакта {contact}')
    req = {
        ACTION: DELETE_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_msg(sock, req)
    ans = recieve_msg(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError(f'Ошибка удаления клиента')
    print(f'Клиент удален')


def db_load(sock, database, username):
    """
    ф-ция загружает данные с сервера в базу данных
    """
    # загрузка списка всех известных юзеров:
    try:
        users_list = user_list_req(sock, username)
    except ServerError:
        CLIENT_LOGGER.error(f'Ошибка запроса списка известных пользователей')
    else:
        database.add_users(users_list)

    # загрузка списка контактов:
    try:
        contacts_list = contact_list_req(sock, username)
    except ServerError:
        CLIENT_LOGGER.error(f'Ошибка запроса списка контактов')
    else:
        for contact in contacts_list:
            database.add_contact(contact)


@log
def main():
    # Сообщаем о запуске
    print('Консольный месседжер. Клиентский модуль.')

    # Загружаем параметы коммандной строки:
    server_address, server_port, client_name = cmd_arg_parse()

    # если имя пользователя не было задано, запросить:
    if not client_name:
        client_name = input('Введите имя пользователя: ')
    else:
        print(f'Клиентский модуль запущен с именем: {client_name}')

    CLIENT_LOGGER.info(f'Запущен клиент с параметрами: адрес сервера: {server_address}, '
                       f'порт {server_port}, имя пользователя: {client_name}.')

    # Инициализация сокета и сообщение серверу о появлении клиента:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Таймаут 1 секунда, необходим для освобождения сокета:
        sock.settimeout(1)


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
        # Инициализация клиентской БД:
        database = ClientDB(client_name)
        db_load(sock, database, client_name)

        # если соединение с сервером установлено корректно,
        # запускаем поток отправки сообщений и взаимодействия с пользователем:
        sender = ClientSender(client_name, sock, database)
        sender.daemon = True
        sender.start()
        CLIENT_LOGGER.debug('Запущены процессы')

        # затем клиентский поток приема сообщений:
        reciever = ClientReader(client_name, sock, database)
        reciever.daemon = True
        reciever.start()

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


