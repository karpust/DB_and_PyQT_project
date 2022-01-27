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
from client_database import ClientDb

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
        # s = self.init_sock()

    # def init_sock(self):
    #     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     return sock


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
        message = input('Введите текст сообщения: ')

        # проверка что получатель существует:
        with db_lock:
            if not self.database.check_user(to_user):
                CLIENT_LOGGER.error(f'Попытка отправить сообщение незарегистрированому получателю: {to_user}')
                return
        msg_dict = {
            ACTION: MESSAGE,
            TIME: time.time(),
            MESSAGE_TEXT: message,
            DESTINATION: to_user,
            SENDER: self.name_account
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения {msg_dict}')
        # сохраняем сообщения для истории:
        with db_lock:
            self.database.save_message(self.name_account, to_user, message)
        # нужно дождаться освобождения сокета для отправки сообщения:
        with sock_lock:
            try:
                send_msg(self.sock, msg_dict)  # это сокет клиента
                CLIENT_LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
            except OSError as err:
                if err.errno:
                    print(f'err.errno: {err.errno}')
                    CLIENT_LOGGER.critical('Потеряно соединение с сервером')
                    exit(1)
                else:
                    CLIENT_LOGGER.error('Не удалось передать сообщение.'
                                        'Таймаут соединения')

    def run(self):
        """
        Осуществляет взаимодействие пользователей:
        запрашивает команды, отправляет сообщения
        """
        self.output_help()  # сначала выводим справку
        while True:
            command = input('Введите команду: ')
            # если отправка сообщения:
            if command == 'message':
                self.create_message_msg()
            # если вывод помощи:
            elif command == 'help':
                self.output_help()
            # если выход:
            elif command == 'exit':
                with sock_lock:
                    try:
                        send_msg(self.sock, self.create_exit_msg())
                    except Exception as ex:
                        print(ex)
                        pass
                    print('Завершение работы')
                    CLIENT_LOGGER.info(f'Пользователь завершил работу')
                time.sleep(0.5)  # задержка чтобы успело уйти сообщение
                break
            # если запрос списка контактов:
            elif command == 'contacts':
                with db_lock:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)

            # если редактирование контактов:
            elif command == 'edit':
                self.edit_contact()

            # если запрос истории сообщений:
            elif command == 'history':
                self.print_history()

            else:
                print('Неизвестная команда, попробуйте снова. '
                      'Для справки введите \'help\'.')

    def output_help(self):
        """Функция выводящяя справку по использованию"""
        print('Поддерживаемые команды:')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')
        print('message - отправить сообщение. '
              'Кому и текст будет запрошены отдельно.')
        print('edit - редактирование списка контактов')
        print('history - история сообщений')
        print('contacts - список контактов')

    def print_history(self):
        with db_lock:
            ask = input('Показать входящие сообщения - in, исходящие - out,'
                        'все - Enter: ')
            if ask == 'in':
                history_list = self.database.get_history(to_user=self.name_account)
                for message in history_list:
                    # от кого, дата, сообщение:
                    print(f'\nСообщение от пользователя: '
                          f'{message[0]} от {message[3]}:\n{message[2]}')
            elif ask == 'out':
                history_list = self.database.get_history(from_user=self.name_account)
                for message in history_list:
                    # кому, дата, сообщение:
                    print(f'\nСообщение пользователю: '
                          f'{message[1]} от {message[3]}:\n{message[2]}')

            else:
                history_list = self.database.get_history()
                for message in history_list:
                    # от кого, кому, дата, сообщение:
                    print(f'\nСообщение от пользователя: {message[0]} '
                          f'пользователю {message[1]} '
                          f'от {message[3]}:\n{message[2]}')

    def edit_contact(self):
        """
        ф-ция редактирования контактов
        """
        ans = input('Для удаления введите del, для добавления add: ')
        if ans == 'del':
            edit = input('Введите имя удаляемого контакта: ')
            with db_lock:
                if self.database.check_contact(edit):
                    self.database.del_contact(edit)
                else:
                    CLIENT_LOGGER.error('Попытка удалить несущестующий контакт')
        elif ans == 'add':
            edit = input('Введите имя создаваемого контакта: ')
            # есть ли вообще такой пользователь:
            if self.database.check_user(edit):
                with db_lock:
                    # если его еще нет в списке контактов:
                    if not self.database.check_contact(edit):
                        self.database.add_contact(edit)
                    else:
                        CLIENT_LOGGER.info('Попытка повторного добавления контакта.')
                        return
                with sock_lock:
                    try:
                        add_contact(self.sock, self.name_account, edit)
                    except ServerError:
                        CLIENT_LOGGER.error('Не удалось отправить информацию на сервер.')


class ClientReader(Thread, metaclass=ClientVerifier):
    def __init__(self, name_account, sock, database):
        super().__init__()
        self.name_account = name_account
        self.sock = sock
        self.database = database
        # s = self.init_sock()

    # def init_sock(self):
    #     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     return sock

    @log
    def run(self):
        """
        Обрабатывает сообщения других
        пользователей, которые приходят с сервера
        обязятельно должны быть и отправитель и получатель
        """
        while True:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # если не сделать тут задержку, то второй поток
            # может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with sock_lock:
                try:
                    message = recieve_msg(self.sock)
                # принято некорректное сообщение:
                except IncorrectDataRecievedError:
                    CLIENT_LOGGER.error(f'Не удалось декодировать полученное сообщение')

                # Вышел таймаут соединения если errno = None, иначе обрыв соединения.
                except OSError as err:
                    if err.errno:
                        CLIENT_LOGGER.critical('Потеряно соединение с сервером.')
                        break

                # Проблемы соединения:
                except (ConnectionAbortedError, ConnectionError,
                        ConnectionResetError, json.JSONDecodeError):
                    CLIENT_LOGGER.critical(f'Потеряно соединение с сервером')
                    break

                # Если пакет корретно получен выводим в консоль и записываем в базу:
                else:
                    if ACTION in message and SENDER in message \
                            and DESTINATION in message and MESSAGE_TEXT in message \
                            and message[ACTION] == MESSAGE and message[DESTINATION] == self.name_account:
                        print(f'Получено сообщение от пользователя {message[SENDER]}: '
                              f'\n{message[MESSAGE_TEXT]}')

                        # сохраняем сообщение в бд:
                        with db_lock:
                            try:
                                self.database.save_message(message[SENDER], self.name_account,
                                                           message[MESSAGE_TEXT])
                            except Exception as ex:
                                print(ex)
                                CLIENT_LOGGER.error('Ошибка взаимодействия с базой данных.')
                        CLIENT_LOGGER.info(f'Получено сообщение от пользователя {message[SENDER]}: '
                                           f'\n{message[MESSAGE_TEXT]}')
                    else:
                        CLIENT_LOGGER.error(f'От сервера получено некорректное сообщение {message}:')


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
    if RESPONSE in ans and ans[RESPONSE] == 202:
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
        database = ClientDb(client_name)
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


