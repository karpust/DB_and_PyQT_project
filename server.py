import argparse
import configparser
import os.path
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
from threading import Thread, Lock
from server_database import ServerDb
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from server_gui import MainWindow, HistoryWindow, ConfigWindow, \
    gui_create_model, create_stat_model


# cсылка на созданный логгер,
# Инициализация логирования сервера:
SERVER_LOGGER = logging.getLogger('server')

# Флаг, что был подключён новый пользователь, нужен чтобы не мучать BD
# постоянными запросами на обновление
new_connection = False
conflag_lock = Lock()


@log
def cmd_arg_parse(default_port, default_address):
    """
    Парсер аргументов коммандной строки
    """
    parser = argparse.ArgumentParser()  # создаем объект парсер
    # описываем аргументы которые парсер будет считывать из cmd:
    parser.add_argument('-p', default=default_port, type=int, nargs='?')  # описываем именные аргументы
    parser.add_argument('-a', default=default_address, nargs='?')
    # nargs='?' значит: если присутствует один аргумент – он будет сохранён,
    # иначе – будет использовано значение из ключа default
    namespace = parser.parse_args(sys.argv[1:])  # все кроме имени скрипта
    listen_address = namespace.a
    listen_port = namespace.p

    # if listen_address != '':
    #     try:
    #         ip_address(listen_address)
    #     except ValueError:
    #         SERVER_LOGGER.critical(f'Попытка запуска сервера с указанием ip-адреса {listen_address}. '
    #                                f'Адрес некорректен')
    #         sys.exit(1)
    # SERVER_LOGGER.info(f'Сервер запущен: ip-адрес для подключений: {listen_address}, '
    #                    f'номер порта для подключений: {listen_port}')
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
                    recv_data_lst, send_data_lst, err_lst = \
                        select(self.clients, self.clients, [], 0)
                    # на чтение, на отправку, на возврат ошибки
            except OSError as err:
                SERVER_LOGGER.error(f'Ошибка работы с сокетами: {err}')

            # проверяем есть ли получающие клиенты,
            # если есть, то добавим словарь-сообщение в очередь,
            # если нет сообщения - отключим клиента:
            if recv_data_lst:
                for client_with_msg in recv_data_lst:
                    try:
                        self.check_msg(recieve_msg(client_with_msg), client_with_msg)
                    except OSError:
                        SERVER_LOGGER.info(f'Клиент {client_with_msg.getpeername()} '
                                           f'отключился от сервера.')
                        # удалим клиента из активных в бд:
                        for name in self.names:
                            if self.names[name] == client_with_msg:
                                self.database.user_logout(name)
                                # удалим имя клиента из словаря:
                                del self.names[name]
                                break
                        self.clients.remove(client_with_msg)

            # если есть сообщения то обрабатываем каждое:
            for msg in self.messages:
                try:
                    self.send_to_msg(msg, send_data_lst)
                except (ConnectionAbortedError, ConnectionError,
                        ConnectionResetError, ConnectionRefusedError):
                    SERVER_LOGGER.info(f'Связь с клиентом с именем {msg[DESTINATION]} была потеряна ')
                    self.clients.remove(self.names[msg[DESTINATION]])
                    del self.names[msg[DESTINATION]]
                self.messages.clear()

    @log
    def check_msg(self, message, client):
        """
        обработчик сообщений от клиентов
        принимает словарь, проверяет корректность,
        отправляет словарь-ответ если нужно
        """
        global new_connection
        SERVER_LOGGER.debug(f'Разбор сообщения от клиента {message}.')
        # если это сообщение о присутствии и ок, ответим {RESPONSE: 200}:
        if ACTION in message and TIME in message \
                and USER in message and message[ACTION] == PRESENCE:
            # если такой пользователь еще не зарегистрирован,
            # регистрируем иначе ошибка:
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                send_msg(client, RESPONSE_200)
                with conflag_lock:
                    new_connection = True
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
            # в бд у отправленных и полученных увеличится счетчик на +1:
            self.database.message_transfer(message[SENDER], message[DESTINATION])
            return
        # если клиент выходит:
        elif ACTION in message and ACCOUNT_NAME in message and message[ACTION] == EXIT:
            self.database.user_logout(message[ACCOUNT_NAME])
            SERVER_LOGGER.info(
                f'Клиент {message[ACCOUNT_NAME]} корректно отключился от сервера.')
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            with conflag_lock:
                new_connection = True
            return
        # если это запрос списка контактов:
        elif ACTION in message and USER in message and message[ACTION] == GET_USER_CONTACTS and \
                self.names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_user_contacts(message[USER])
            send_msg(client, response)
        # если это запрос на добавление контакта:
        elif ACTION in message and USER in message and message[ACTION] == ADD_CONTACT and \
                ACCOUNT_NAME in message and self.names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            send_msg(client, RESPONSE_200)
        # если это запрос на удаление контакта:
        elif ACTION in message and USER in message and message[ACTION] == DELETE_CONTACT and \
                ACCOUNT_NAME in message and self.names[message[USER]] == client:
            self.database.delete_contact(message[USER], message[ACCOUNT_NAME])
            send_msg(client, RESPONSE_200)
        # если это запрос всех известных пользователей:
        elif ACTION in message and message[ACTION] == GET_USERS and \
                ACCOUNT_NAME in message and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0] for user in self.database.all_users_list]
            send_msg(client, response)

        else:
            response = RESPONSE_400
            response[ERROR] = 'запрос некорректен'
            send_msg(client, response)
            return

    @log
    def send_to_msg(self, message, listen_socks):
        """
        функция адресной отправки сообщения конкретному клиенту.
        принимает словарь-сообщение, список зарегистрированных пользователей
        и слушающие сокеты. Ничего не возвращает.
        """
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in listen_socks:
            send_msg(self.names[message[DESTINATION]], message)
            SERVER_LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                               f'от пользователя {message[SENDER]}')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            SERVER_LOGGER.error(f'Пользователь {message[DESTINATION]} не зарегистророван '
                                f'на сервере. Отправка сообщения невозможна.')


def main():
    # загрузка файла конфигурации сервера:
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f'{dir_path}/{"server.ini"}')

    # Загрузка параметров командной строки:
    listen_address, listen_port = cmd_arg_parse(
        config['SETTINGS']['Default_port'],
        config['SETTINGS']['Listen_Address']
    )

    # Инициализация базы данных:
    database = ServerDb(os.path.join(
        config['SETTINGS']['Database_path'],
        config['SETTINGS']['Database_file']
    )
    )

    # Создание экземпляра класса - сервера и его запуск:
    server = ServSock(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # создаем графическое окружение для сервера:
    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    # иниц параметров в окна:
    main_window.statusBar().showMessage('Server Working')
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    def list_update():
        """
        ф-ция проверяет флаг подключения,
        обновляет список подключенных
        """
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(
                gui_create_model(database)
            )
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False

    def show_statistics():
        """
        ф-ция показывает окно со статистикой клиентов
        """
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    def server_config():
        """
        ф-ция показывает окно с настройками сервера
        """
        global config_window
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['Database_path'])
        config_window.db_file.insert(config['SETTINGS']['Database_file'])
        config_window.port.insert(config['SETTINGS']['Default_port'])
        config_window.ip.insert(config['SETTINGS']['Listen_Address'])
        config_window.save_btn.clicked.connect(save_server_config)

    def save_server_config():
        """
        ф-ция сохранения настроек сервера
        """
        global config_window
        message = QMessageBox()
        config['SETTINGS']['Database_path'] = config_window.db_path.text()
        config['SETTINGS']['Database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            config['SETTINGS']['Listen_Address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['Default_port'] = str(port)
                print(port)
                with open('server.ini', 'w') as conf:
                    config.write(conf)
                    message.information(
                        config_window, 'OK', 'Настройки успешно сохранены'
                    )
            else:
                message.warning(
                    config_window, 'Ошибка', 'Порт должен быть от 1024 до 65536'
                )

    # Таймер обновляет список клиентов раз в секунду:
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # связываем кнопки с процедурами:
    main_window.refresh_btn.triggered.connect(list_update)
    main_window.show_history_btn.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    # запуск GUI:
    server_app.exec_()


if __name__ == '__main__':
    main()





