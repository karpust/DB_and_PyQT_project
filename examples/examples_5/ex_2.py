"""Обработчики сигналов"""

import sys
from PyQt5.QtWidgets import QApplication, QPushButton


def on_clicked(param):
    print(f"Вы нажали кнопку. Выполнена функция on_clicked() с параметром {param}")


class HandClass:
    def __init__(self, my_param=0):
        self.my_param = my_param

    def __call__(self):
        """Метод реализует вызов экземпляра"""
        print("Вы нажали кнопку. Выполнен метод HandClass.__call__()")
        print(f'my_param = {self.my_param}')

    def on_clicked(self):
        print("Вы нажали кнопку. Выполнен метод HandClass.on_clicked()")


HC_OBJ = HandClass()
APP = QApplication(sys.argv)
BTN = QPushButton("Нажмите")
# Обработчик-функция
BTN.clicked.connect(lambda: on_clicked(6))
# Обработчик-метод класса
BTN.clicked.connect(HC_OBJ.on_clicked)
# Обработчик-ссылка на экземпляр класса
BTN.clicked.connect(HandClass(10))
# Обработчик-анонимная функция
BTN.clicked.connect(lambda: HandClass(5)())
BTN.show()
sys.exit(APP.exec_())
