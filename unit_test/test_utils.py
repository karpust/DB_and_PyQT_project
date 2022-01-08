import os
import sys
import unittest
import json

from old import client

sys.path.append(os.path.join(os.getcwd(), '..'))
from common.variables import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE, ENCODING
from client import client
recieve_msg = client.recieve_msg
send_msg = client.send_msg


class TestSocket:
    """тестовый класс для получения и отправки"""
    def __init__(self, test_dict):
        self.test_dict = test_dict
        self.encoded_msg = None
        self.recieved_msg = None

    def send(self, msg_to_send):
        """
        принимает сообщение закодированное тестируемой ф-ией, сохраняет в self.recieved_msg,
        корректно кодирует тестовое сообщение, сохраняет в self.encoded_msg
        """
        json_test_message = json.dumps(self.test_dict)  # полученный словарь -> json строка
        self.encoded_msg = json_test_message.encode(ENCODING)  # это закодированный здесь тестовый словарь
        self.recieved_msg = msg_to_send  # это сообщение закодированное тестируемой ф-ией

    def recv(self, max_len):
        """получаем сообщение из сокета"""
        json_test_message = json.dumps(self.test_dict)  # полученный словарь -> json строка
        return json_test_message.encode(ENCODING)  # возвращает закодированное сообщение (получ из сокета)


class TestUtils(unittest.TestCase):
    """создали тестовый клас для utils"""
    test_dict_send = {
        ACTION: PRESENCE,
        TIME: 1.1,
        USER: {
            ACCOUNT_NAME: 'test_test'
        }
    }
    test_dict_recv_ok = {RESPONSE: 200}
    test_dict_recv_err = {RESPONSE: 400, ERROR: 'Bad request'}

    def test_send_message_encode(self):
        """тест корректности кодирования
        перед отправкой в тестовый сокет"""
        test_socket = TestSocket(self.test_dict_send)  # создали тестовый сокет, в него передали данные для методов
        send_msg(test_socket, self.test_dict_send)  # запуск тест-мой ф-ии, отправляет тест сообщ в тест сокет
        # проверка корректности кодирования словаря сравниваем то что закодировано ->
        # в тестовой ф-ии(корректно) с тем что закодировано в тестируемой:
        self.assertEqual(test_socket.encoded_msg, test_socket.recieved_msg)

    def test_send_message_not_dict(self):
        """тест проверки корректности типа
        принимаемых данных перед отправкой """
        test_socket = TestSocket(self.test_dict_send)  # экземпляр тестового словаря хранит тестовый словарь
        send_msg(test_socket, self.test_dict_send)  # вызов тестируемой ф-ции, результаты сохран в тестовом сокете
        # проверим генерацию исключения, при не словаре на входе:
        self.assertRaises(TypeError, send_msg, test_socket, "wrong_dictionary")

    def test_get_msg_dict_correct(self):
        """тест корректной расшифровки корректного словаря"""
        test_sock_ok = TestSocket(self.test_dict_recv_ok)  # экземпляр тестового словаря хранит тестовый словарь
        self.assertEqual(recieve_msg(test_sock_ok), self.test_dict_recv_ok)  # сравнили получ от сервера сообщ с тест ок

    def test_get_msg_dict_not_correct(self):
        """тест корректной расшифровки ошибочного словаря"""
        test_sock_err = TestSocket(self.test_dict_recv_err)
        self.assertEqual(recieve_msg(test_sock_err), self.test_dict_recv_err)


if __name__ == '__main__':
    unittest.main()


