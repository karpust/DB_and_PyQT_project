import argparse
import os.path
import sys
from Cryptodome.PublicKey import RSA
from PyQt5.QtWidgets import QApplication, QMessageBox

from client.database import ClientDb
from client.main_window import ClientMainWindow
from client.start_dialog import UserNameDialog
from client.transport import ClientTransport
from common.variables import *
from common.errors import *
from decos import log

# Инициализация клиентского логера:
logger = logging.getLogger('client')


@log
def cmd_arg_parse():  # sys.argv = ['client.py', '127.0.0.1', 8888]
    """
    Парсер аргументов коммандной строки
    """
    parser = argparse.ArgumentParser()  # создаем объект парсер
    parser.add_argument('addr', default='127.0.0.1', nargs='?')  # описываем позиционные аргументы
    parser.add_argument('port', default=7777, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])

    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name
    client_passwd = namespace.password

    if server_port < 1024 or server_port > 65535:
        logger.critical(f'Попытка запуска клиента с указанием порта: {server_port}. '
                        f'Адрес порта должен быть в диапазоне от 1024 до 65535')
        exit(1)
    return server_address, server_port, client_name, client_passwd


def main():
    # Загружаем параметы коммандной строки:
    server_address, server_port, client_name, client_passwd = cmd_arg_parse()

    # создаем клиентское приложение:
    client_app = QApplication(sys.argv)

    # если имя пользователя или пароль не были указаны, запросить:
    start_dialog = UserNameDialog()
    if not client_name or not client_passwd:
        client_app.exec_()

        # если пользователь ввел имя и нажал ОК,
        # то сохраним имя, иначе выход:
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            client_passwd = start_dialog.client_passwd.text()
            logger.debug(f'Using USERNAME: {client_name}, '
                         f'PASSWD: {client_passwd}.')
        else:
            exit(0)

        logger.info(
            f'Started client with parameters: server address: {server_address}, '
            f'port: {server_port}, username: {client_name}')

        dir_path = os.path.dirname(os.path.realpath(__file__))
        key_file = os.path.join(dir_path, f'{client_name}.key')
        if not os.path.exists(key_file):
            keys = RSA.generate(2048, os.urandom)
            with open(key_file, 'wb') as key:
                key.write(keys.export_key())
        else:
            with open(key_file, 'rb') as key:
                keys = RSA.import_key(key.read())

        # !!!keys.publickey().export_key()
        logger.debug("Keys successfully loaded.")

        # Создаём объект базы данных:
        database = ClientDb(client_name)

        # создаем объект-транспорт и запускаем транспортный поток:
        try:
            transport = ClientTransport(server_port, server_address, database,
                                        client_name, client_passwd, keys)
            logger.debug('Transport is ready')
        except ServerError as err:
            message = QMessageBox()
            message.critical(start_dialog, 'Server error', err.text)
            exit(1)
        transport.setDaemon(True)
        transport.start()

        del start_dialog

        # создаем GUI:
        main_window = ClientMainWindow(database, transport, keys)
        main_window.make_connection(transport)
        main_window.setWindowTitle(f'User - {client_name}')
        client_app.exec_()

        # после закрытия графической оболочки закрываем транспорт:
        transport.transport_shutdown()
        transport.join()


if __name__ == '__main__':
    main()
