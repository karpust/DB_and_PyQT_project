import argparse
import sys

from PyQt5.QtWidgets import QApplication

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
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    if server_port < 1024 or server_port > 65535:
        logger.critical(f'Попытка запуска клиента с указанием порта: {server_port}. '
                        f'Адрес порта должен быть в диапазоне от 1024 до 65535')
        exit(1)
    return server_address, server_port, client_name


def main():
    # Загружаем параметы коммандной строки:
    server_address, server_port, client_name = cmd_arg_parse()

    # создаем клиентское приложение:
    client_app = QApplication(sys.argv)

    # если имя пользователя не было задано в коммандной строке, запросить:
    if not client_name:
        start_dialog = UserNameDialog()
        client_app.exec_()

        # если пользователь ввел имя и нажал ОК,
        # то сохраним имя и удалим объект, иначе выход:
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            del start_dialog
        else:
            exit(0)

        logger.info(
            f'Запущен клиент с парамертами: адрес сервера: {server_address}, '
            f'порт: {server_port}, имя пользователя: {client_name}')

        # Создаём объект базы данных:
        database = ClientDb(client_name)

        # создаем объект-транспорт и запускаем транспортный поток:
        try:
            transport = ClientTransport(server_port, server_address, database,
                                        client_name)
        except ServerError as err:
            print(err.text)
            exit(1)
        transport.setDaemon(True)
        transport.start()

        # создаем GUI:
        main_window = ClientMainWindow(database, transport)
        main_window.make_connection(transport)
        main_window.setWindowTitle(f'Пользователь - {client_name}')
        client_app.exec_()

        # после закрытия графической оболочки закрываем транспорт:
        transport.transport_shutdown()
        transport.join()


if __name__ == '__main__':
    main()


