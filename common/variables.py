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
LIST_INFO = 'data_list'

# База данных для хранения данных сервера:
SERVER_DATABASE = 'sqlite:///server_base.db3'
# Текущий уровень логирования
LOGGING_LEVEL = logging.DEBUG

RESPONSE_400 = {RESPONSE: 400, ERROR: 'Bad request'}
RESPONSE_200 = {RESPONSE: 200}
RESPONSE_202 = {RESPONSE: 202, LIST_INFO: None}


