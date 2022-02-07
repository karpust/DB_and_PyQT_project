import argparse
import configparser
import os.path
import sys
from common.variables import *
import logging
from decos import log
from server.core import ServSock
from server.database import ServerDb
from PyQt5.QtWidgets import QApplication
from server.main_window import MainWindow
from PyQt5.QtCore import Qt


# cсылка на созданный логгер,
# Инициализация логирования сервера:
logger = logging.getLogger('server')


@log
def cmd_arg_parse(default_port, default_address):
    """
    Парсер аргументов коммандной строки
    """
    parser = argparse.ArgumentParser()  # создаем объект парсер
    # описываем аргументы которые парсер будет считывать из cmd:
    parser.add_argument('-p', default=default_port, type=int, nargs='?')  # описываем именные аргументы
    parser.add_argument('-a', default=default_address, nargs='?')
    # parser.add_argument('--no_gui', action='store_true')
    # nargs='?' значит: если присутствует один аргумент – он будет сохранён,
    # иначе – будет использовано значение из ключа default
    namespace = parser.parse_args(sys.argv[1:])  # все кроме имени скрипта
    listen_address = namespace.a
    listen_port = namespace.p
    # gui_flag = namespace.no_gui
    logger.debug('Аргументы коммандной строки успешно загружены')
    return listen_address, listen_port


@log
def config_load():
    """
    Парсер конфигурационного ini-файла
    """
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server+++.ini'}")
    # Если конфиг файл загружен правильно, запускаемся,
    # иначе конфиг по умолчанию.
    if 'SETTINGS' in config:
        return config
    else:
        config.add_section('SETTINGS')
        config.set('SETTINGS', 'Default_port', str(PORT_DEFAULT))
        config.set('SETTINGS', 'Listen_Address', '')
        config.set('SETTINGS', 'Database_path', '')
        config.set('SETTINGS', 'Database_file', 'server_database.db3')
        return config


def main():
    # загрузка файла конфигурации сервера:
    config = config_load()

    # Загрузка параметров командной строки:
    listen_address, listen_port = cmd_arg_parse(
        config['SETTINGS']['Default_port'],
        config['SETTINGS']['Listen_Address']
    )

    # Инициализация базы данных:
    database = ServerDb(os.path.join(config['SETTINGS']['Database_path'],
                                     config['SETTINGS']['Database_file']))

    # Создание экземпляра класса - сервера и его запуск:
    server = ServSock(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # создаем графическое окружение для сервера:
    server_app = QApplication(sys.argv)
    server_app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
    main_window = MainWindow(database, server, config)

    # запуск GUI:
    server_app.exec_()
    # остановка обработчика сообщений:
    server.running = False


if __name__ == '__main__':
    main()
