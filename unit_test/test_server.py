import unittest
import sys
import os
# from pprint import pprint
# pprint(sys.path)
sys.path.append(os.path.join(os.getcwd(), '..'))  # добавили путь в корневую дир - на дир выше текущей
# getcwd - get current working directory
# pprint(sys.path)
from common.variables import ACTION, PRESENCE, TIME, TYPE, STATUS, USER, ACCOUNT_NAME, RESPONSE, ERROR
from server import server
check_presence_msg = server.check_presence_msg


class TestServer(unittest.TestCase):
    """
    создает тестовый случай
    """
    res_ok = {RESPONSE: 200}
    res_err = {RESPONSE: 400, ERROR: 'Bad request'}

    def setUp(self) -> None:
        """выполняет настройку теста"""
        pass

    def tearDown(self) -> None:
        """выполняет завершающие действия"""
        pass

    def test_msg_ok(self):
        """корректный ли запрос от клиента"""
        self.assertEqual(check_presence_msg({ACTION: PRESENCE, TIME: 1.1, TYPE: STATUS,
                                             USER: {ACCOUNT_NAME: 'Guest', STATUS: "I'm online"}}), self.res_ok)

    def test_msg_no_action(self):
        """ошибка если нет ACTION"""
        self.assertEqual(check_presence_msg({TIME: 1.1, TYPE: STATUS,
                                             USER: {ACCOUNT_NAME: 'Guest', STATUS: "I'm online"}}), self.res_err)

    def test_msg_wrong_action(self):
        """ошибка неверное действие"""
        self.assertEqual(check_presence_msg({ACTION: 'Wrong', TIME: 1.1, TYPE: STATUS,
                                             USER: {ACCOUNT_NAME: 'Guest', STATUS: "I'm online"}}), self.res_err)

    def test_msg_no_time(self):
        """ошибка если нет TIME"""
        self.assertEqual(check_presence_msg({ACTION: PRESENCE, TYPE: STATUS,
                                             USER: {ACCOUNT_NAME: 'Guest', STATUS: "I'm online"}}), self.res_err)

    def test_msg_no_user(self):
        """ошибка если нет пользователя"""
        self.assertEqual(check_presence_msg({ACTION: PRESENCE, TIME: 1.1, TYPE: STATUS}), self.res_err)

    def test_msg_is_not_guest(self):
        """ошибка если пользователь не Guest"""
        self.assertEqual(check_presence_msg({ACTION: PRESENCE, TIME: 1.1, TYPE: STATUS,
                                             USER: {ACCOUNT_NAME: 'Other', STATUS: "I'm online"}}), self.res_err)


if __name__ == '__main__':
    unittest.main()


