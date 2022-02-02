import sys
sys.path.append('../')

import logging
from PyQt5.QtWidgets import QDialog, QComboBox, QLabel, \
    QPushButton, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel

logger = logging.getLogger('client')


# диалог выбора контакта для добавления:
class AddContactDialog(QDialog):
    def __init__(self, transport, database):
        super().__init__()
        self.transport = transport
        self.database = database

        self.setFixedSize(350, 120)
        self.setWindowTitle('Выберите контакт для добавления: ')
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)

        self.selector_label = QLabel('Вфберите контакт для добавления: ', self)
        self.selector_label.setFixedSize(200, 20)
        self.selector_label.move(10, 0)

        self.selector = QComboBox(self)
        self.selector.setFixedSize(200, 20)
        self.selector.move(10, 30)

        self.btn_refresh = QPushButton('Обновить список', self)
        self.btn_refresh.setFixedSize(100, 30)
        self.btn_refresh.move(60, 60)

        self.btn_ok = QPushButton('Добавить', self)
        self.btn_ok.setFixedSize(100, 30)
        self.btn_ok.move(230, 20)

        self.btn_cancel = QPushButton('Отмена', self)
        self.btn_cancel.setFixedSize(100, 30)
        self.btn_cancel.move(230, 60)
        self.btn_cancel.clicked.connect(self.close)

        # заполнение списка возможных контактов:
        self.possible_contacts_update()
        # назначение действия на кнопку обновить:
        self.btn_refresh.clicked.connect(self.update_possible_contacts)

    def possible_contacts_update(self):
        """
        ф-ция заполняет список возможных контактов
        """
        self.selector.clear()
        # множества контактов и пользователей:
        contacts_list = set(self.database.get_contacts())
        users_list = set(self.database.get_users())
        # чтобы не добавить в список самого себя, удалим:
        users_list.remove(self.transport.username)
        # добавим список возможных контактов:
        self.selector.addItems(users_list - contacts_list)

    def update_possible_contacts(self):
        try:
            self.transport.user_list_update()
        except OSError:
            pass
        else:
            logger.debug('Выполнено обновление списка пользователей с сервера')
        self.possible_contacts_update()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    from database import ClientDb
    database = ClientDb('test1')
    from transport import ClientTransport
    transport = ClientTransport(7777, '127.0.0.1', database, 'test1')
    window = AddContactDialog(transport, database)
    window.show()
    app.exec_()

