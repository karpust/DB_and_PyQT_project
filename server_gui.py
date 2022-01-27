import sys
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QLabel, \
    QTableView, QDialog, QPushButton, QLineEdit, QFileDialog, QMessageBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt
import os


# класс основного окна:
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        # кнопка выхода:
        exitAction = QAction('Выход', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(qApp.quit)

        # кнопка обновить список клиентов:
        self.refresh_btn = QAction('Обновить список', self)

        # кнопка настроек сервера:
        self.config_btn = QAction('Настройки сервера', self)

        # кнопка вывести историю сообщений:
        self.show_history_btn = QAction('История сообщений клиентов', self)

        # статусбар:
        self.statusBar()

        # тулбар:
        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(exitAction)
        self.toolbar.addAction(self.refresh_btn)
        self.toolbar.addAction(self.config_btn)
        self.toolbar.addAction(self.show_history_btn)

        # настройка геометрии основного окна (фикс):
        self.setFixedSize(800, 600)
        self.setWindowTitle('Messaging Server alpha release')

        # надпись, что ниже список подключенных клиентов:
        self.label = QLabel('Список подключенных клиентов: ', self)
        self.label.setFixedSize(240, 15)
        self.label.move(10, 27)

        # окно со списком подключенных клиентов:
        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 45)
        self.active_clients_table.setFixedSize(780, 400)

        # отображаем окно:
        self.show()


# класс окна с историей пользователей:
class HistoryWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        # настройка окна:
        self.setWindowTitle('Статистика клиентов')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # кнопка закрытия окна:
        self.close_btn = QPushButton('Закрыть', self)
        self.close_btn.move(250, 650)
        self.close_btn.clicked.connect(self.close)

        # лист с историей:
        self.history_table = QTableView(self)
        self.history_table.move(10, 10)
        self.history_table.setFixedSize(580, 620)

        self.show()


# класс окна настроек:
class ConfigWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        # насторойки окна:
        self.setFixedSize(390, 260)
        self.setWindowTitle('Настройки сервера')

        # метка о файле базы данных:
        self.db_path_label = QLabel('Путь к файлу базы данных: ', self)
        self.db_path_label.move(10, 10)
        self.db_path_label.setFixedSize(240, 15)

        # поле с путем к бд:
        self.db_path = QLineEdit(self)
        self.db_path.setFixedSize(250, 20)
        self.db_path.move(10, 30)
        self.db_path.setReadOnly(True)

        # кнопка выбора пути:
        self.db_path_select = QPushButton('Обзор...', self)
        self.db_path_select.move(285, 26)

        # окно выбора папки:
        def open_file_window():
            # global dialog
            dialog = QFileDialog(self)
            path = dialog.getExistingDirectory()
            path = path.replace('/', '\\')
            self.db_path.insert(path)
        self.db_path_select.clicked.connect(open_file_window)

        # метка с именем поля файла базы данных:
        self.db_file_label = QLabel('Имя файла базы данных: ', self)
        self.db_file_label.move(10, 68)
        self.db_file_label.setFixedSize(180, 15)

        # поле для ввода имени файла базы данных:
        self.db_file = QLineEdit(self)
        self.db_file.move(220, 66)
        self.db_file.setFixedSize(160, 20)

        # метка с номером порта:
        self.port_label = QLabel('Номер порта для соединений: ', self)
        self.port_label.move(10, 108)
        self.port_label.setFixedSize(180, 15)

        # поле для ввода номера порта:
        self.port = QLineEdit(self)
        self.port.move(220, 108)
        self.port.setFixedSize(160, 20)

        # метка с адресом для соединений:
        self.ip_label = QLabel('С какого IP принимаем соединения: ', self)
        self.ip_label.move(10, 148)
        # self.ip_label.setFixedSize(190, 15)

        # метка с напоминанием о пустом поле:
        self.ip_label_note = QLabel('оставьте это поле пустым, чтобы \nпринимать '
                                    'соединения с любых адресов', self)
        self.ip_label_note.move(10, 170)
        self.ip_label_note.setFixedSize(500, 30)

        # поле для ввода IP:
        self.ip = QLineEdit(self)
        self.ip.move(220, 148)
        self.ip.setFixedSize(160, 20)

        # кнопка сохранения настроек:
        self.save_btn = QPushButton('Сохранить', self)
        self.save_btn.move(190, 220)

        # кнопка закрытия окна:
        self.close_btn = QPushButton('Закрыть', self)
        self.close_btn.move(290, 220)
        self.close_btn.clicked.connect(self.close)

        self.show()


def gui_create_model(database):
    """
    ф-ция создания таблицы QModel для отображения в окне программы
    """
    list_users = database.active_users_list()
    list_table = QStandardItemModel()
    list_table.setHorizontalHeaderLabels(
        ['Имя Клиента', 'IP-адрес', 'Порт', 'Время подключения']
    )
    for row in list_users:
        user, ip, port, time = row
        user = QStandardItem(user)
        user.setEditable(False)
        ip = QStandardItem(ip)
        ip.setEditable(False)
        port = QStandardItem(str(port))
        port.setEditable(False)
        # уберём миллисекунды из времени:
        time = QStandardItem(str(time.replace(microsecond=0)))
        time.setEditable(False)

        list_table.appendRow(
            [user, ip, port, time]
        )
    return list_table


def create_stat_model(database):
    # список записей из бд:
    history_list = database.message_history()
    # объект модели данных:
    list_table = QStandardItemModel()
    list_table.setHorizontalHeaderLabels(
        ['Имя Клиента', 'Последний раз входил', 'Сообщений отправлено',
         'Сообщений получено']
    )
    for row in history_list:
        user, last_seen, sent, recvd = row
        user = QStandardItem(user)
        user.setEditable(False)
        last_seen = QStandardItem(str(last_seen.replace(microsecond=0)))
        last_seen.setEditable(False)
        sent = QStandardItem(str(sent))
        sent.setEditable(False)
        recvd = QStandardItem(str(recvd))
        recvd.setEditable(False)
        list_table.appendRow(
            [user, last_seen, sent, recvd]
        )
    return list_table


if __name__ == "__main__":

    # app = QApplication(sys.argv)
    # main_window = MainWindow()
    # main_window.statusBar().showMessage('Это статусбар')
    # test_list = QStandardItemModel(main_window)
    # test_list.setHorizontalHeaderLabels(
    #     ['Имя клиента', 'IP-адрес', 'Порт', 'Время подключения']
    # )
    # test_list.appendRow(
    #     [QStandardItem('test1'), QStandardItem('192.168.1.1'),
    #      QStandardItem('23232'), QStandardItem('20:21:01')]
    # )
    # main_window.active_clients_table.setModel(test_list)
    # main_window.active_clients_table.resizeColumnsToContents()
    # app.exec_()


    # app = QApplication(sys.argv)
    # window = HistoryWindow()
    # test_list = QStandardItemModel(window)
    # test_list.setHorizontalHeaderLabels(
    #     ['Имя клиента', 'Последний раз входил', 'Отправлено', 'Получено']
    # )
    # test_list.appendRow(
    #     [QStandardItem('test1'), QStandardItem('Sat Nov 21 16:33:20 1981'),
    #      QStandardItem('10'), QStandardItem('11')]
    # )
    # window.history_table.setModel(test_list)
    # window.history_table.resizeColumnsToContents()
    # app.exec_()


    app = QApplication(sys.argv)
    dial = ConfigWindow()
    app.exec_()

