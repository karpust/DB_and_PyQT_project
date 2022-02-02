import time
from threading import Thread, Lock
from PyQt5.QtCore import QObject, pyqtSignal
import socket
from common.utils import *
from common.variables import *


# Объект блокировки сокета и логгер:
logger = logging.getLogger('client')
socket_lock = Lock()


# класс transport отвечает за взаимодействие с сервером:
class ClientTransport(Thread, QObject):
    # сигналы: новое сообщение и потеря соединения:
    new_message = pyqtSignal(str)
    lost_connection = pyqtSignal()

    def __init__(self, port, ip_address, database, username):
        Thread.__init__(self)
        QObject.__init__(self)

        # база данных:
        self.database = database
        # имя пользователя:
        self.username = username
        # сокет для работы с сервером:
        self.transport = None
        # установка соединения:
        self.init_connection(port, ip_address)
        # обновление таблицы известных пользователей и контактов:
        try:
            self.user_list_update()
            self.contact_list_update()
        except OSError as err:
            if err.errno:
                logger.critical('Потеряно соединение с сервером')
                raise ServerError('Потеряно соединение с сервером')
            logger.error('Таймаут соединения при обновлении списка'
                         'пользователей')
        except json.JSONDecoder:
            logger.critical('Потеряно соединение с сервером')
            raise ServerError('Потеряно соединение с сервером')
        # флаг продолжения работы транспорта:
        self.running = True

    def init_connection(self, port, ip):
        # инит сокета, сообщение о появлении клиента серверу:
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # таймаут для освобождения сокета:
        self.transport.settimeout(5)
        # попытки соединения, если успешно, то флаг=True:
        connected = False
        for i in range(5):
            logger.info(f'Попытка подключения №{i + 1}')
            try:
                self.transport.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                break
            time.sleep(1)

        # если не соединились:
        if not connected:
            logger.critical('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')
        logger.info('Соединение с сервером установлено')

        # отправка серверу presence-сообщения и получение ответа:
        try:
            with socket_lock:
                send_msg(self.transport, self.create_presence_msg())
                self.check_server_msg(recieve_msg(self.transport))
        except (OSError, json.JSONDecodeError):
            logger.critical('Потеряно соединение с сервером!')
            raise ServerError('Потеряно соединение с сервером!')

        # если всё хорошо, сообщение о установке соединения:
        logger.info('Соединение с сервером успешно установлено.')

    def create_presence_msg(self):
        """
        Создает сообщение-присутствие(словарь),
        подтверждающее, что пользоватьель онлайн.
        """
        msg = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username,
            }
        }
        logger.debug(f'Создано сообщение {PRESENCE} '
                     f'пользователя {self.username}')
        return msg

    def check_server_msg(self, message):
        """
        Ф-ция обрабатывает сообщение от сервера
        """
        logger.debug(f'Разбор сообщения от сервера {message}')

        # если это подтверждение чего-то:
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 400:
                raise ServerError(f'400 : {message[ERROR]}')
            else:
                logger.debug(f'Принят неизвестный код подтверждения '
                             f'{message[RESPONSE]}')

        # если это сообщение от пользователя:
        elif ACTION in message and SENDER in message and DESTINATION in message \
                and MESSAGE_TEXT in message and message[ACTION] == MESSAGE \
                and message[DESTINATION] == self.username:
            logger.debug(f'Получено сообщение от пользователя '
                         f'{message[SENDER]}:{message[MESSAGE_TEXT]}')
            self.database.save_message(message[SENDER], 'in', message[MESSAGE_TEXT])
            logger.debug(f'Сообщение от пользователя сохранено в бд')
            self.new_message.emit(message[SENDER])
            logger.debug(f'self.new_message.emit(message[SENDER])')

    def contact_list_update(self):
        """
        ф-ция обновления списка контактов
        """
        logger.debug(f'Запрос контакт листа для пользователя {self.name}')
        req = {
            ACTION: GET_USER_CONTACTS,
            TIME: time.time(),
            USER: self.username
        }
        logger.debug(f'Сформирован запрос {req}')
        with socket_lock:
            send_msg(self.transport, req)
            ans = recieve_msg(self.transport)
        logger.debug(f'Получен ответ {ans}')
        if RESPONSE in ans and ans[RESPONSE] == 202:
            for contact in ans[LIST_INFO]:
                self.database.add_contact(contact)
        else:
            logger.error('Не удалось обновить список контактов.')

    def user_list_update(self):
        """
        ф-ция обновления таблицы всех пользователей
        """
        logger.debug(f'Запрос списка всех известных пользователей {self.username}')
        req = {
            ACTION: GET_USERS,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        # освобождаем сокет:
        with socket_lock:
            send_msg(self.transport, req)
            ans = recieve_msg(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 202:
            self.database.add_users(ans[LIST_INFO])
        else:
            logger.error('Не удалось обновить список известных пользователей.')

    def add_contact(self, contact):
        """
        ф-ция сообщает серверу о добавлении нового контакта
        """
        logger.debug(f'Создание контакта {contact}')
        req = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        # освобождаем сокет:
        with socket_lock:
            send_msg(self.transport, req)
            self.check_server_msg(recieve_msg(self.transport))

    def delete_contact(self, contact):
        """
        ф-ция удаления пользователя из списка контактов на сервере
        """
        logger.debug(f'Создание контакта {contact}')
        req = {
            ACTION: DELETE_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        # освобождаем сокет:
        with socket_lock:
            send_msg(self.transport, req)
        self.check_server_msg(recieve_msg(self.transport))

    def transport_shutdown(self):
        """
        ф-ция закрытия соединения
        отправляет сообщение о выходе
        """
        self.running = False
        message = {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        # освобождаем сокет:
        with socket_lock:
            try:
                send_msg(self.transport, message)
            except OSError:
                pass
            logger.debug('Транспорт завершает работу.')
            time.sleep(0.5)

    def send_message(self, to, message):
        msg_dict = {
            ACTION: MESSAGE,
            SENDER: self.username,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        logger.debug(f'Сформирован словарь сообщения: {msg_dict}')
        # освобождаем сокет:
        with socket_lock:
            send_msg(self.transport, msg_dict)
            self.check_server_msg(recieve_msg(self.transport))
            logger.info(f'Отправлено сообщение для пользователя {to}!!!!!')

    def run(self):
        logger.debug('Запущен процесс - приёмник собщений с сервера.')
        while self.running:
            # делаем задержку для освобождения сокета:
            time.sleep(1)
            with socket_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = recieve_msg(self.transport)
                except OSError as err:
                    if err.errno:
                        logger.critical(f'Потеряно соединение с сервером.')
                        self.running = False
                        self.lost_connection.emit()
                except (ConnectionRefusedError, ConnectionError,
                        ConnectionAbortedError, json.JSONDecodeError, TypeError):
                    logger.debug(f'Потеряно соединение с сервером.')

                # если сообщение получено:
                else:
                    logger.debug(f'Принято сообщение с сервера: {message}')
                    self.check_server_msg(message)
                finally:
                    self.transport.settimeout(5)




