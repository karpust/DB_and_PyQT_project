import os
import sys

from sqlalchemy import create_engine, Table, Column, Integer, String, Text, \
    MetaData, DateTime
from sqlalchemy.orm import mapper, sessionmaker
import datetime

sys.path.append('../')


# класс-хранилище клиентской стороны
class ClientDb:
    # создание классов для отображения таблиц:
    # известных юзеров:
    class KnownUser:
        def __init__(self, user_name):
            self.id = None
            self.user_name = user_name

    # истории сообщений:
    class MessageHistory:
        def __init__(self, contact, direction, message):
            self.id = None
            self.direction = direction
            self.contact = contact
            self.message = message
            self.date = datetime.datetime.now()

    # списка контактов:
    class Contacts:
        def __init__(self, contact_name):
            self.id = None
            self.contact_name = contact_name

    def __init__(self, name):
        # Создаём движок базы данных, поскольку разрешено несколько
        # клиентов одновременно, каждый должен иметь свою БД.
        # Поскольку клиент мультипоточный необходимо отключить
        # проверки на подключения с разных потоков,
        # иначе sqlite3.ProgrammingError
        path = os.path.dirname(os.path.realpath(__file__))
        filename = f'client_{name}.db3'
        self.db_engine = create_engine(f'sqlite:///{os.path.join(path, filename)}',
                                       echo=False, pool_recycle=7200,
                                       connect_args={'check_same_thread': False}
                                       )
        self.metadata = MetaData()

        # ------------------------подготовка создания таблиц-------------------------
        # известных пользователей:
        users = Table('known_users', self.metadata,
                      Column('id', Integer, primary_key=True),
                      Column('user_name', String)
                      )

        # истории сообщений:
        message_history = Table('message_history', self.metadata,
                                Column('id', Integer, primary_key=True),
                                Column('contact', String),
                                Column('direction', String),
                                Column('message', Text),
                                Column('date', DateTime)
                                )
        # контактов:
        contacts = Table('contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('contact_name', String, unique=True)
                         )

        # ------------------------------создание таблиц-----------------------------
        self.metadata.create_all(self.db_engine)

        # создаем отображение:
        mapper(self.KnownUser, users)
        mapper(self.MessageHistory, message_history)
        mapper(self.Contacts, contacts)

        # создадим сессию:
        Session = sessionmaker(bind=self.db_engine)
        self.session = Session()

        # очистим таблицу контактов,
        # т.к. при запуске они подгрузятся с сервера:
        self.session.query(self.Contacts).delete()
        self.session.commit()

    # методы класса хранилища клиент:
    def add_contact(self, contact):
        """
        ф-ция добавления контакта
        """
        if not self.session.query(self.Contacts)\
                .filter_by(contact_name=contact).count():
            contact_row = self.Contacts(contact)
            self.session.add(contact_row)
            self.session.commit()

    def del_contact(self, contact):
        """
        ф-ция удаления контакта
        """
        self.session.query(self.Contacts)\
            .filter_by(contact_name=contact).delete()
        self.session.commit()

    def add_users(self, users_list):
        """
        ф-ция добавления известных пользователей из списка
        """
        # удаляем всех юзеров, т.к. их получим с сервера:
        self.session.query(self.KnownUser).delete()
        for user in users_list:
            user_row = self.KnownUser(user)
            self.session.add(user_row)
        self.session.commit()

    def save_message(self, contact, direction, message):
        """
        ф-ция сохранения сообщений
        """
        message_row = self.MessageHistory(contact, direction, message)
        self.session.add(message_row)
        self.session.commit()

    def get_users(self):
        """
        ф-ция возвращает список известных юзеров
        """
        return [user[0] for user in
                self.session.query(self.KnownUser.user_name).all()]

    def get_contacts(self):
        """
        ф-ция возвращает список контактов
        """
        return [contact[0] for contact in
                self.session.query(self.Contacts.contact_name).all()]

    def check_user(self, user):
        """
        ф-ция проверяет наличие юзера в таблице известных юзеров
        """
        if self.session.query(self.KnownUser).filter_by(user_name=user).count():
            return True
        else:
            return False

    def check_contact(self, contact):
        """
        ф-ция проверяет наличие контакта в таблице контактов
        """
        if self.session.query(self.Contacts)\
                .filter_by(contact_name=contact).count():
            return True
        else:
            return False

    def get_history(self, contact):
        """
        ф-ция возвращает историю переписки юзеров
        в виде списка: от кого, кому, сообщения, дата
        """
        query = self.session.query(self.MessageHistory)\
            .filter_by(contact=contact)
        return [(history_row.contact, history_row.direction,
                 history_row.message, history_row.date)
                for history_row in query.all()]


if __name__ == '__main__':
    test_db = ClientDb('test1')
    for i in ['test2', 'test3', 'test4', 'test5']:
        test_db.add_contact(i)
    print(test_db.check_contact('test4'))
    test_db.del_contact('test4')
    print(test_db.check_contact('test4'))
    print(test_db.get_contacts())

    print(test_db.get_users())
    test_db.add_users(['test6', 'test7', 'test8', 'test9'])
    print(test_db.get_users())
    print(test_db.check_user('test7'))

    test_db.save_message('test6', 'test7', 'hello 7! this is 6')
    test_db.save_message('test1', 'test2', 'hello 2! this is 1')
    print(test_db.get_history('test1'))
    print(test_db.get_history('test7'))

















