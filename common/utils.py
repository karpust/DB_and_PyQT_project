import json
import sys
from socket import socket
from .variables import ENCODING, MAX_PACKAGE_LENGTH
from errors import *
from decos import log
sys.path.append('../')


class Sock(socket):
    def __init__(self, family, type):
        # конструктор класса, family и type заданы в родителе по умолчанию, их не передаем, но передадим
        super().__init__(family, type)  # чтобы обратиться к параметрам родителя и изменить их если нужно

    @staticmethod
    @log
    def send_msg(socket_to, msg_dict):
        """
        принимает словарь
        преобразует его в строку-джейсон
        кодирует в байты, отправляет данные в сокет
        """
        if not isinstance(msg_dict, dict):
            raise NotDictInputError
        msg_json_str = json.dumps(msg_dict)  # dict -> str json
        msg_bytes = msg_json_str.encode(ENCODING)  # сообщение в байты
        socket_to.send(msg_bytes)  # отправка сокет сервера|клиента

    @staticmethod
    @log
    def recieve_msg(socket_from):
        """
        принимает байты
        декодирует
        возвращает словарь-джейсон
        """
        msg_bytes = socket_from.recv(MAX_PACKAGE_LENGTH)  # получили в байтах
        if not isinstance(msg_bytes, bytes):
            raise IncorrectDataRecievedError
        msg_decode = msg_bytes.decode(ENCODING)  # декодировали
        msg_json_dict = json.loads(msg_decode)  # в jsonObj(dict)
        return msg_json_dict


