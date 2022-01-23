import sys
import os
import unittest
# from pprint import pprint
# pprint(sys.path)
sys.path.append(os.path.join(os.getcwd(), '..'))  # добавили путь в корневую дир - на дир выше текущей
# getcwd - get current working directory
# pprint(sys.path)
from client import client
from common.variables import ACTION, PRESENCE, TIME, TYPE, STATUS, USER, ACCOUNT_NAME, RESPONSE, ERROR
create_presence_msg = client.create_presence_msg()  # результ-словарь
check_server_msg = client.check_server_msg  # метод класса


class TestClient(unittest.TestCase):
    """создает тестовый случай"""
    create_presence_msg[TIME] = 1.1

    def setUp(self) -> None:
        """выполняет настройку теста"""
        pass

    def tearDown(self) -> None:
        """выполняет завершающие действия"""
        pass

    def test_presence_msg_ok(self):
        """корректен ли запрос(presence?)"""
        self.assertEqual(create_presence_msg, {ACTION: PRESENCE, TIME: 1.1, TYPE: STATUS,
                                USER: {ACCOUNT_NAME: 'Guest', STATUS: "I'm online"}})

    def test_check_server_msg_200(self):
        """проверка разбора корректного ответа 200"""
        self.assertEqual(check_server_msg({RESPONSE: 200}), '200: OK')

    def test_check_server_msg_400(self):
        """проверка разбора корректного ответа 400"""
        self.assertEqual(check_server_msg({RESPONSE: 400, ERROR: 'Bad request'}), '400: Bad request')

    def test_check_server_msg_no_response(self):
        """провекра разбора ответа без параметра RESPONCE"""
        self.assertRaises(ValueError, check_server_msg, {ERROR: 'Bad request'})


if __name__ == '__main__':
    unittest.main()

