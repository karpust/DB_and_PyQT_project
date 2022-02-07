"""константы"""

import logging

# константы для сокетов:
SERVER_ADDRESS_DEFAULT = ''
CLIENT_ADDRESS_DEFAULT = 'localhost'
PORT_DEFAULT = 7777
ENCODING = 'utf-8'
MAX_CONNECTION = 5
MAX_PACKAGE_LENGTH = 1024


#  константы JIM протокола:
ACTION = 'action'
TIME = 'time'
USER = 'user'
ACCOUNT_NAME = 'name_account'
STATUS = 'status'
TYPE = 'type'
PRESENCE = 'presence'
MESSAGE = 'message'
RESPONSE = 'response'
ERROR = 'error'
MESSAGE_TEXT = 'message_text'
SENDER = 'from'
DESTINATION = 'to'
EXIT = 'exit'
ADD_CONTACT = 'add'
DELETE_CONTACT = 'delete'
GET_USER_CONTACTS = 'get_contacts'
GET_USERS = 'get_users'
DATA = 'bin'
LIST_INFO = 'data_list'
PUBLIC_KEY = 'pubkey'
PUBLIC_KEY_REQUEST = 'pubkey_need'


# База данных для хранения данных сервера:
SERVER_DATABASE = 'sqlite:///server_base.db3'
# Текущий уровень логирования
LOGGING_LEVEL = logging.DEBUG

RESPONSE_400 = {RESPONSE: 400, ERROR: None}
RESPONSE_200 = {RESPONSE: 200, LIST_INFO: None}
RESPONSE_202 = {RESPONSE: 202, LIST_INFO: None}
RESPONSE_511 = {RESPONSE: 511, DATA: None}
RESPONSE_205 = {RESPONSE: 205}
