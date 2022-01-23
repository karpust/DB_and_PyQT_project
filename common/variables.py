"""константы"""

# константы для сокетов:
SERVER_ADDRESS_DEFAULT = ''
CLIENT_ADDRESS_DEFAULT = 'localhost'
PORT_DEFAULT = 7777
ENCODING = 'utf-8'
MAX_CONNECTION = 5
MAX_PACKAGE_LENGTH = 4096


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
RESPONSE_400 = {RESPONSE: 400, ERROR: 'Bad request'}
RESPONSE_200 = {RESPONSE: 200}
