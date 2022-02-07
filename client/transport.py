import binascii
import hashlib
import hmac
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
    message_205 = pyqtSignal()


    def __init__(self, port, ip_address, database, username, passwd, keys):
        Thread.__init__(self)
        QObject.__init__(self)

        # база данных:
        self.database = database
        # имя пользователя:
        self.username = username
        # сокет для работы с сервером:
        self.transport = None
        # наборы ключей для шифрования:
        self.keys = keys
        # пароль:
        self.passwd = passwd
        # установка соединения:
        self.init_connection(port, ip_address)
        # обновление таблицы известных пользователей и контактов:
        try:
            self.user_list_update()
            self.contact_list_update()
        except OSError as err:
            if err.errno:
                logger.critical('Lost connection to server')
                raise ServerError('Lost connection to server')
            logger.error("Connection timeout when updating users list")
        except json.JSONDecoder:
            logger.critical('Lost connection to server')
            raise ServerError('Lost connection to server')
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
            logger.info(f'Connection attempt №{i + 1}')
            try:
                self.transport.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                logger.debug("Connection established.")
                break
            time.sleep(1)

        # если не соединились:
        if not connected:
            logger.critical('Failed to connect to server')
            raise ServerError('Failed to connect to server')
        logger.debug('Starting auth dialog.')

        # авторизация: получение хэша пароля:
        passwd_bytes = self.passwd.encode('utf-8')
        salt = self.username.lower().encode('utf-8')
        passwd_hash = hashlib.pbkdf2_hmac('sha512', passwd_bytes, salt, 10000)
        passwd_hash_string = binascii.hexlify(passwd_hash)
        logger.debug(f'Passwd hash ready: {passwd_hash_string}')

        # получаем публичный ключ и декодируем его из байтов:
        pubkey = self.keys.publickey().export_key().decode('ascii')

        # авторизация на сервере;
        # отправка серверу presence-сообщения:
        with socket_lock:
            try:
                send_msg(self.transport, self.presence_msg(pubkey))
                ans = recieve_msg(self.transport)
                logger.debug(f'Server response: {ans}')
                if ans[RESPONSE] == 400:
                    raise ServerError(ans[ERROR])
                elif ans[RESPONSE] == 511:
                    ans_data = ans[DATA]
                    hash = hmac.new(passwd_hash_string, ans_data.encode('utf-8'),
                                    'MD5')
                    digest = hash.digest()
                    my_ans = RESPONSE_511
                    my_ans[DATA] = binascii.b2a_base64(digest).decode('ascii')
                    send_msg(self.transport, my_ans)
                    self.check_server_msg(recieve_msg(self.transport))
            except (OSError, json.JSONDecodeError) as err:
                logger.debug(f'Connection error.', exc_info=err)
                raise ServerError(f'Connection failure during authorization process.')

        # если всё хорошо, сообщение о установке соединения:
        logger.info('Server connection successfully established.')

    def presence_msg(self, pub_key):
        """
        Создает сообщение-присутствие(словарь),
        подтверждающее, что пользоватьель онлайн.
        """
        msg = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username,
                PUBLIC_KEY: pub_key
            }
        }
        logger.debug(f'Message-{PRESENCE} '
                     f'by user {self.username}')
        return msg

    def check_server_msg(self, message):
        """
        Ф-ция обрабатывает сообщение от сервера
        """
        logger.debug(f'Parsing a message from the server {message}')

        # если это подтверждение чего-то:
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 400:
                raise ServerError(f'{message[ERROR]}')
            elif message[RESPONSE] == 205:
                self.user_list_update()
                self.message_205.emit()
            else:
                logger.debug(f'Unknown verification code received '
                             f'{message[RESPONSE]}')

        # если это сообщение от пользователя:
        elif ACTION in message and SENDER in message and DESTINATION in message \
                and MESSAGE_TEXT in message and message[ACTION] == MESSAGE \
                and message[DESTINATION] == self.username:
            logger.debug(f'Message received from user '
                         f'{message[SENDER]}: {message[MESSAGE_TEXT]}')
            self.new_message.emit(message)

    def contact_list_update(self):
        """
        ф-ция обновления списка контактов
        """
        logger.debug(f'Request a contact list for a user {self.username}')
        req = {
            ACTION: GET_USER_CONTACTS,
            TIME: time.time(),
            USER: self.username
        }
        logger.debug(f'Request generated {req}')
        with socket_lock:
            send_msg(self.transport, req)
            ans = recieve_msg(self.transport)
        logger.debug(f'Answer received {ans}')
        if RESPONSE in ans and ans[RESPONSE] == 202:
            for contact in ans[LIST_INFO]:
                self.database.add_contact(contact)
        else:
            logger.error('Failed to update contact list.')

    def user_list_update(self):
        """
        ф-ция обновления таблицы всех пользователей
        """
        logger.debug(f'Request a list of all known users {self.username}')
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
            logger.error('Failed to update list of known users.')

    def add_contact(self, contact):
        """
        ф-ция сообщает серверу о добавлении нового контакта
        """
        logger.debug(f'Create a contact {contact}')
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
        logger.debug(f'Create a contact {contact}')
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
            logger.debug('Transport shuts down.')
            time.sleep(0.5)

    def send_message(self, to, message):
        msg_dict = {
            ACTION: MESSAGE,
            SENDER: self.username,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        logger.debug(f'The message dictionary is generated: {msg_dict}')
        # освобождаем сокет:
        with socket_lock:
            send_msg(self.transport, msg_dict)
            self.check_server_msg(recieve_msg(self.transport))
            logger.info(f'Sent message to user {to}')

    def run(self):
        logger.debug('The process that receives messages from '
                     'the server is running.')
        while self.running:
            # делаем задержку для освобождения сокета:
            time.sleep(1)
            with socket_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = recieve_msg(self.transport)
                except OSError as err:
                    if err.errno:
                        logger.critical(f'Lost connection to server.')
                        self.running = False
                        self.lost_connection.emit()
                except (ConnectionRefusedError, ConnectionError,
                        ConnectionAbortedError, json.JSONDecodeError, TypeError):
                    logger.debug(f'Lost connection to server.')

                # если сообщение получено:
                else:
                    logger.debug(f'Message received from server: {message}')
                    self.check_server_msg(message)
                finally:
                    self.transport.settimeout(5)




