"""
Начать реализацию класса «Хранилище» для серверной стороны. Хранение необходимо
осуществлять в базе данных. В качестве СУБД использовать sqlite. Для
взаимодействия с БД можно применять ORM.

Опорная схема базы данных:
На стороне сервера БД содержит следующие таблицы:
a) вcе клиенты:
* логин;
* дата последнего входа (last login_time).
b) история клиентов:
* id-клиента;
* login_time;
* ip-адрес.
* port
c) список активных клиентов:
* id_клиента;
* ip-адрес;
* port;
* login_time.
"""

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker
from common.variables import *
import datetime


# класс-хранилище для серверной стороны
class ServerDb:
    # создание классов для отображения таблиц:
    class User:
        # всех пользователей:
        def __init__(self, user_name):
            self.name = user_name
            self.last_login = datetime.datetime.now()
            self.id = None

    class ActivUser:
        # всех активных пользователей:
        def __init__(self, user_id, ip_address, port, login_time):
            self.id = None
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time  # когда залогинился или время актив?

    class LoginHistory:
        # историй всех пользователей:
        def __init__(self, user, login_date, user_ip, user_port):
            self.id = None
            self.user = user
            self.login_time = login_date
            self.ip_address = user_ip
            self.port = user_port

    class ContactsList:
        # списка контактов юзера:
        def __init__(self, name, contact):
            self.id = None
            self.name = name
            self.contact = contact

    class ActionHistory:
        # истории всех действий юзера:
        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.recvd = 0

    # ----------------------создание движка базы данных:--------------------------
    def __init__(self, path):
        # Создаём движок базы данных:
        self.database_engine = create_engine(SERVER_DATABASE, echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})
        # echo=False - отключает вывод на экран sql-запросов)
        # pool_recycle - по умолчанию соединение с БД через 8 часов простоя обрывается
        # Чтобы этого не случилось необходимо добавить pool_recycle=7200 (переустановка
        # соединения через каждые 2 часа)

        self.metadata = MetaData()  # что конкретно?
        # ------------------------подготовка создания таблиц-------------------------
        # всех пользователей:
        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),  # имя колонки должно совпадать с полем класса
                            Column('name', String, unique=True),
                            Column('last_login', DateTime)
                            )

        # всех активных пользователей:
        active_users_table = Table('Active_users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('Users.id'), unique=True),
                                   Column('ip_address', String),
                                   Column('port', Integer),
                                   Column('login_time', DateTime)
                                   )

        # историй всех пользователей:
        users_login_table = Table('Login_history', self.metadata,
                                  Column('id', Integer, primary_key=True),
                                  Column('user', ForeignKey('Users.id')),  # пользователи повторяются
                                  Column('login_time', DateTime),
                                  Column('ip_address', String),
                                  Column('port', Integer)
                                  )

        contacts_list_table = Table('Contacts_list', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('name', ForeignKey('Users.id')),
                                    Column('contact', ForeignKey('Users.id'))
                                    )

        users_action_table = Table('Actions_history', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('Users.id')),
                                   Column('sent', Integer),
                                   Column('recvd', Integer)
                                   )

        # -------------------создание таблиц:------------------------
        self.metadata.create_all(self.database_engine)

        # создание отображения:
        # связываем данные и таблицы:
        mapper(self.User, users_table)
        mapper(self.ActivUser, active_users_table)
        mapper(self.LoginHistory, users_login_table)
        mapper(self.ContactsList, contacts_list_table)
        mapper(self.ActionHistory, users_action_table)

        # создание сессии:
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # при установке соединений очищаем таблицу активных пользователей:
        self.session.query(self.ActivUser).delete()
        self.session.commit()

    # функции: фикс вход, фикс выход, список активных, история входов
    # Функция возвращает список известных пользователей
    # со временем последнего входа.

    def user_login(self, username, ip_address, port):
        """
        ф-ция входа
        """
        print(username, ip_address, port)
        # ищем в таблице пользователя с именем user_name
        user = self.session.query(self.User).filter_by(name=username)
        # если такой пользователь есть:
        if user.count():
            user = user.first()
            # обновляем время последнего логина
            user.last_login = datetime.datetime.now()
        else:
            # создаем юзера (во время его первого логина):
            user = self.User(username)
            self.session.add(user)
            # чтобы присвоить новому юзеру id:
            self.session.commit()
            user_history = self.ActionHistory(user.id)
            self.session.add(user_history)
        # запись в таблицу активных юзеров о входе:
        new_user = self.ActivUser(user.id, ip_address, port, datetime.datetime.now())
        print(new_user.ip_address)
        self.session.add(new_user)
        # сохранить вход в таблице истории:
        history = self.LoginHistory(user.id, datetime.datetime.now(), ip_address, port)
        self.session.add(history)
        # сохранить изменения:
        self.session.commit()

    def user_logout(self, username):
        """
        ф-ция выхода
        """
        # выбираем юзера по имени:
        user = self.session.query(self.User).filter_by(name=username).first()
        # удаляем его из активных:
        self.session.query(self.ActivUser).filter_by(user=user.id).delete()
        self.session.commit()

    def active_users_list(self):
        """
        показывает список всех активных юзеров
        """
        users = self.session.query(self.User.name, self.ActivUser.ip_address,
                                   self.ActivUser.port,
                                   self.ActivUser.login_time).join(self.User)
        return users.all()

    def all_users_list(self):
        """
        показывает список всех юзеров которые когда-либо были
        """
        users = self.session.query(self.User.name, self.User.last_login)
        return users.all()

    def login_history(self, username=None):
        users = self.session.query(self.User.name,
                                   self.LoginHistory.login_time,
                                   self.LoginHistory.ip_address,
                                   self.LoginHistory.port, ).join(self.User)
        if username:
            # история для конкретного пользователя:
            users = users.filter(self.User.name == username)
        return users.all()

    def add_contact(self, name, contact):
        """
        ф-ция добавляет контакт юзера
        """
        # юзер с именем name:
        user_name = self.session.query(self.User).filter_by(name=name).first()
        # юзер с именем contact:
        user_contact = self.session.query(self.User).filter_by(name=contact).first()
        # если нет юзера с именем contact или он уже записан в таблице контактов:
        if not user_contact or self.session.query(self.ContactsList)\
                .filter_by(name=user_name.id, contact=user_contact.id).count():
            return
        # иначе добавляем в таблицу контактов:
        contact = self.ContactsList(user_name.id, user_contact.id)
        self.session.add(contact)
        self.session.commit()

    def delete_contact(self, name, contact):
        """
        ф-ция удаляет контакт юзера
        """
        # юзер с именем name:
        user_name = self.session.query(self.User).filter_by(name=name).first()
        # юзер с именем contact:
        user_contact = self.session.query(self.User).filter_by(name=contact).first()
        # если нет такого юзера:
        if not user_contact:
            return
        # иначе удаляем:
        self.session.query(self.ContactsList).filter(self.ContactsList.name == user_name.id,
                                                     self.ContactsList.contact == user_contact.id).delete()
        self.session.commit()

    def get_user_contacts(self, username):
        """
        ф-ция возвращает контакты конкретного юзера
        """
        # юзер чьи контакты
        user = self.session.query(self.User).filter_by(name=username).one()
        query = self.session.query(self.ContactsList, self.User.name)\
            .filter_by(name=user.id)\
            .join(self.User, self.ContactsList.contact == self.User.id)
        # выбираем имена контактов:
        print([contact[1] for contact in query.all()])
        return [contact[1] for contact in query.all()]

    def message_transfer(self, sender, reciever):
        """
        ф-ция-счетчик полученных и принятых сообщений
        """
        # получаем id отправителя:
        sender = self.session.query(self.User).filter_by(name=sender).first().id
        # получаем id получателя:
        reciever = self.session.query(self.User).filter_by(name=reciever).first().id
        # Запрашиваем строки из истории и увеличиваем счётчики:
        sender_row = self.session.query(self.ActionHistory).filter_by(user=sender).first()
        sender_row.sent += 1
        reciever_row = self.session.query(self.ActionHistory).filter_by(user=reciever).first()
        reciever_row.recvd += 1
        self.session.commit()

    def message_history(self):
        """
        ф-ция возвращает кол-во переданных и полученных сообщений
        """
        query = self.session.query(self.User.name,
                                   self.User.last_login,
                                   self.ActionHistory.sent,
                                   self.ActionHistory.recvd,
                                   ).join(self.User)
        return query.all()


if __name__ == '__main__':
    db_1 = ServerDb()
    db_1.user_login('Vasiliy', '192.168.1.1', 7777)
    db_1.user_login('Petia', '192.168.1.2', 8886)
    db_1.user_login('Maria', '192.168.1.2', 8886)
    print(db_1.active_users_list())
    db_1.user_logout('Petia')
    print(db_1.active_users_list())
    print(db_1.all_users_list())
    print(db_1.login_history())
    print(db_1.login_history('Vasiliy'))
    db_1.add_contact('Vasiliy', 'Petia')
    db_1.add_contact('Vasiliy', 'Maria')
    db_1.get_user_contacts('Vasiliy')
    db_1.delete_contact('Vasiliy', 'Maria')
    db_1.get_user_contacts('Vasiliy')
    db_1.message_transfer('Vasiliy', 'Petia')
    print('db_1.message_history: ', db_1.message_history())

