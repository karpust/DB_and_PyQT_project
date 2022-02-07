from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, \
    QApplication, QLabel, qApp


# стартовый диалог с выбором имени пользователя:
class UserNameDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.ok_pressed = False

        self.setWindowTitle('Привет!')
        self.setFixedSize(190, 135)

        self.label = QLabel('Введите имя пользователя: ', self)
        self.label.setFixedSize(170, 10)
        self.label.move(10, 10)

        self.client_name = QLineEdit(self)
        self.client_name.setFixedSize(170, 20)
        self.client_name.move(10, 30)

        self.label_passwd = QLabel('Введите пароль: ', self)
        self.label_passwd.setFixedSize(150, 15)
        self.label_passwd.move(10, 55)

        self.client_passwd = QLineEdit(self)
        self.client_passwd.setFixedSize(170, 20)
        self.client_passwd.move(10, 75)

        self.btn_ok = QPushButton('Начать', self)
        self.btn_ok.move(2, 105)
        self.btn_ok.clicked.connect(self.click)

        self.btn_cancel = QPushButton('Выход', self)
        self.btn_cancel.move(95, 105)
        self.btn_cancel.clicked.connect(qApp.exit)

        self.show()

    def click(self):
        """
        обработчик кнопки ОК
        """
        if self.client_name.text():
            # если поле не пустое, то ставим флаг=True
            self.ok_pressed = True
            qApp.exit()


if __name__ == '__main__':
    app = QApplication([])
    dial = UserNameDialog()
    app.exec_()

