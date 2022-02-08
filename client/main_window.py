import json
import sys

from common.errors import *
from client.add_contact import AddContactDialog
from client.del_contact import DelContactDialog
from client.main_window_conv_from_ui import Ui_MainClientWindow

from PyQt5.QtWidgets import QMainWindow, qApp, QMessageBox, QApplication
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
from PyQt5.QtCore import pyqtSlot, Qt
import base64
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.PublicKey import RSA
from common.variables import *

sys.path.append('../')


logger = logging.getLogger('client')


class ClientMainWindow(QMainWindow):
    """
    класс основного окна
    """
    def __init__(self, database, transport, keys):
        super().__init__()
        self.database = database
        self.transport = transport

        # загрузка конфигурации окна из QT designer:
        self.ui = Ui_MainClientWindow()
        self.ui.setupUi(self)

        # объект - дешифорвщик сообщений с предзагруженным ключём
        self.decrypter = PKCS1_OAEP.new(keys)

        # кнопка выхода:
        self.ui.menu_exit.triggered.connect(qApp.exit)

        # кнопка отправления сообщения:
        self.ui.btn_send.clicked.connect(self.send_message)

        # кнопка добавления контакта:
        self.ui.btn_add_contact.clicked.connect(self.add_contact_window)
        self.ui.menu_add_contact.triggered.connect(self.add_contact_window)

        # кнопка удаления контакта:
        self.ui.btn_remove_contact.clicked.connect(self.delete_contact_window)
        self.ui.menu_del_contact.triggered.connect(self.delete_contact_window)

        # доп аттрибуты:
        self.contacts_model = None
        self.history_model = None
        self.messages = QMessageBox()
        self.current_chat = None
        self.ui.list_messages.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.list_messages.setWordWrap(True)
        self.current_chat_key = None
        self.encryptor = None

        # даблклик по листу контактов, отправление в обработчик:
        self.ui.list_contacts.doubleClicked.connect(self.select_active_user)
        self.clients_list_update()
        self.set_disabled_input()
        self.show()

    def set_disabled_input(self):
        """
        деактивирует поля вывода
        """
        self.ui.label_new_message.setText(
            'To select a recipient, double-click on it in the contact list window')
        self.ui.text_message.clear()
        if self.history_model:
            self.history_model.clear()

        # поле ввода и кнопка отправки неактивны до выбора получателя:
        self.ui.btn_clear.setDisabled(True)
        self.ui.btn_send.setDisabled(True)
        self.ui.text_message.setDisabled(True)

    def history_list_update(self):
        """
        заполняет историю сообщений
        """
        # получение истории, отсортированной по дате:
        list = sorted(self.database.get_history(self.current_chat),
                      key=lambda item: item[3])
        # создание модели, если еще не создана:
        if not self.history_model:
            self.history_model = QStandardItemModel()
            self.ui.list_messages.setModel(self.history_model)
        # очистка от старых записей:
        self.history_model.clear()
        # берется не более 20 последних записей:
        length = len(list)
        start_index = 0
        if length > 20:
            start_index = length - 20
        # входящие и исходящие записи разным фоном
        # записи в обратном порядке, поэтому выбор с конца и не более 20:
        for i in range(start_index, length):
            item = list[i]
            if item[1] == 'in':
                mess = QStandardItem(f'Incoming from {item[3].replace(microsecond=0)}'
                                     f'\n {item[2]}')
                mess.setEditable(False)
                mess.setBackground(QBrush(QColor(255, 213, 213)))
                mess.setTextAlignment(Qt.AlignLeft)
                self.history_model.appendRow(mess)
            else:
                mess = QStandardItem(f'Outgoing from {item[3].replace(microsecond=0)}'
                                     f':\n {item[2]}')
                mess.setEditable(False)
                mess.setTextAlignment(Qt.AlignRight)
                mess.setBackground(QBrush(QColor(204, 255, 204)))
                self.history_model.appendRow(mess)
        self.ui.list_messages.scrollToBottom()

    def select_active_user(self):
        """
        обработчик двойного клика по контакту
        """
        # Выбранный пользователем (даблклик) находится в
        # выделеном элементе в QListView
        self.current_chat = self.ui.list_contacts.currentIndex().data()
        # вызываем основную функцию
        self.set_active_user()

    def set_active_user(self):
        """
        устанавливает активного собеседника
        """
        # request the user's public key,
        # and create an encryption object:
        try:
            self.current_chat_key = self.transport.key_request(
                self.current_chat)
            logger.debug(f'Uploaded public key for {self.current_chat}')
            if self.current_chat_key:
                self.encryptor = PKCS1_OAEP.new(
                    RSA.import_key(self.current_chat_key))
        except (OSError, json.JSONDecodeError):
            self.current_chat_key = None
            self.encryptor = None
            logger.debug(f'Failed to get key for {self.current_chat}')

        # if there is no key, then error that failed to start chat with user:
        if not self.current_chat_key:
            self.messages.warning(
                self, 'Error', 'There is no encryption key for selected user'
            )
            return

        # put the inscription and activate the buttons:
        self.ui.label_new_message.setText(f'Enter a message for '
                                          f'{self.current_chat}:')
        self.ui.btn_clear.setDisabled(False)
        self.ui.btn_send.setDisabled(False)
        self.ui.text_message.setDisabled(False)

        # fill the message history window for the required user:
        self.history_list_update()

    def clients_list_update(self):
        """
        обновляет контакт-лист
        """
        contacts_list = self.database.get_contacts()
        self.contacts_model = QStandardItemModel()
        for i in sorted(contacts_list):
            item = QStandardItem(i)
            item.setEditable(False)
            self.contacts_model.appendRow(item)
        self.ui.list_contacts.setModel(self.contacts_model)

    def add_contact_window(self):
        """
        добавляет контакт
        """
        global select_dialog
        select_dialog = AddContactDialog(self.transport, self.database)
        select_dialog.btn_ok.clicked.connect(
            lambda: self.add_contact_action(select_dialog))
        select_dialog.show()

    def add_contact_action(self, item):
        """
        обработчик добавления, сообщает серверу,
        обновляет таблицу и список контактов
        """
        new_contact = item.selector.currentText()
        self.add_contact(new_contact)
        item.close()

    def add_contact(self, new_contact):
        """
        добавляет контакт в базу данных
        """
        try:
            self.transport.add_contact(new_contact)
        except ServerError as err:
            self.messages.critical(self, 'Server error', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Error', 'Lost connection to server!')
                self.close()
            self.messages.critical(self, 'Error', 'Connection timeout!')
        else:
            self.database.add_contact(new_contact)
            new_contact = QStandardItem(new_contact)
            new_contact.setEditable(False)
            self.contacts_model.appendRow(new_contact)
            logger.info(f'Successfully added contact {new_contact}')
            self.messages.information(self, 'Added', 'Contact added successfully.')

    def delete_contact_window(self):
        """
        удаляет контакт
        """
        global remove_dialog
        remove_dialog = DelContactDialog(self.database)
        remove_dialog.btn_ok.clicked.connect(
            lambda: self.delete_contact(remove_dialog))
        remove_dialog.show()

    def delete_contact(self, item):
        """
        обработчик удаления контакта,
        сообщает на сервер, обновляет таблицу контактов
        """
        selected = item.selector.currentText()
        try:
            self.transport.delete_contact(selected)
        except ServerError as err:
            self.messages.critical(self, 'Server error', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Error', 'Lost connection to server!')
                self.close()
            self.messages.critical(self, 'Error', 'Connection timeout!')
        else:
            self.database.del_contact(selected)
            self.clients_list_update()
            logger.info(f'Successfully deleted contact {selected}')
            self.messages.information(self, 'Deleted', 'Contact successfully removed.')
            item.close()
            # Если удалён активный пользователь, то деактивируем поля ввода.
            if selected == self.current_chat:
                self.current_chat = None
                self.set_disabled_input()

    def send_message(self):
        """
        отправляет сообщение пользователю
        """
        # check that field is not empty, pick up message, clear field:
        message_text = self.ui.text_message.toPlainText()
        self.ui.text_message.clear()
        if not message_text:
            return
        # encrypt message by recipient's key and pack it in base64:
        message_text_encrypted = self.encryptor.encrypt(
            message_text.encode('utf8'))
        message_text_encrypted_base64 = base64.b64encode(
            message_text_encrypted)
        try:
            self.transport.send_message(
                self.current_chat,
                message_text_encrypted_base64.decode('ascii'))
            pass
        except ServerError as err:
            self.messages.critical(self, 'Error', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(
                    self, 'Error', 'Lost connection to server!')
                self.close()
            self.messages.critical(self, 'Error', 'Connection timeout')
        except (ConnectionResetError, ConnectionAbortedError):
            self.messages.critical(
                self, 'Error', 'Lost connection to server!')
            self.close()
        else:
            self.database.save_message(self.current_chat, 'out', message_text)
            logger.debug(
                f'Sent message to {self.current_chat}: {message_text}')
            self.history_list_update()

    # слот приёма новых сообщений:
    @pyqtSlot(dict)
    def message(self, message):
        """
        приём новых сообщений
        """
        # get bytes string:
        encrypted_message = base64.b64encode(message[MESSAGE_TEXT])
        # decode the string, print the message on error and exit:
        try:
            decrypted_message = self.decrypter.decrypt(encrypted_message)
        except (ValueError, TypeError):
            self.messages.warning(
                self, 'Error', 'Failed to decode message')
            return
        # save message to database, update message history
        # or open new chat:
        self.database.save_message(
            self.current_chat, 'in', decrypted_message.decode('utf8'))
        sender = message[SENDER]

        if sender == self.current_chat:
            self.history_list_update()
        else:
            # Проверим есть ли такой пользователь у нас в контактах:
            if self.database.check_contact(sender):
                # Если есть, спрашиваем о желании открыть с ним чат
                # и открываем при желании:
                if self.messages.question(
                        self, 'New message',
                        f'Received a new message from {sender}, '
                        f'open a chat with him?',
                        QMessageBox.Yes,
                        QMessageBox.No) == QMessageBox.Yes:
                    self.current_chat = sender
                    self.set_active_user()
            else:
                print('NO')
                # ask if want to add user to contacts:
                if self.messages.question(
                        self, 'New message ',
                        f'Received a new message from {sender}.\n '
                        f'This user is not on your contact list.\n'
                        f'Add to contacts and open a chat '
                        f'with him?',
                        QMessageBox.Yes,
                        QMessageBox.No) == QMessageBox.Yes:
                    self.add_contact(sender)
                    self.current_chat = sender
                    # re-save the message, otherwise it will be lost,
                    # because there was no contact at the previous call
                    self.database.save_message(
                        self.current_chat, 'in', decrypted_message.decode('utf8')
                    )
                    self.set_active_user()

    # слот потери соединения:
    @pyqtSlot()
    def connection_lost(self):
        """
        выдаёт сообщение об ошибке и завершает работу приложения
        """
        self.messages.warning(self, 'Connection failure',
                              'Lost connection to server. ')
        self.close()

    @pyqtSlot()
    def sig_205(self):
        """
        slot that performs databases updates
        at the command of the server
        """
        if self.current_chat and not self.database.check_user(
                self.current_chat):
            self.messages.warning(
                self, 'Sorry', 'The contact was deleted from server.')
            self.set_disabled_input()
            self.current_chat = None
        self.ckients_list_update()

    def make_connection(self, trans_obj):
        """
        установка соединения
        """
        trans_obj.new_message.connect(self.message)
        trans_obj.lost_connection.connect(self.connection_lost)
        trans_obj.message_205.connect(self.sig_205)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    from database import ClientDb
    database = ClientDb('client1')
    from transport import ClientTransport
    transport = ClientTransport(7777, '127.0.0.1', database, 'test1', 1, 15)
    window = ClientMainWindow(database, transport, 15)
    sys.exit(app.exec_())


