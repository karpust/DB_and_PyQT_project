"""ошибки"""


class IncorrectDataRecievedError(Exception):
    """
    ошибка некорректных данных полученных в сокет
    """
    def __str__(self):
        return "Принято некорректное сообщение от удаленного пользователя"


class NotDictInputError(Exception):
    """
    Исключение: тип данных не словарь
    """
    def __init__(self, not_dict):
        self.not_dict = not_dict

    def __str__(self):
        return "Принят неверный тип данных. Ожидается словарь."


class FieldMissingError(Exception):
    """
    Исключение: в принятом словаре отсутствует обязательное поле
    """
    def __init__(self, miss_field):
        self.miss_field = miss_field

    def __str__(self):
        return f"В принятом словаре отсутствует обязятельное поле: {self.miss_field}"


class ServerError(Exception):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text
