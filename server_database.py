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


class ServerDb:
    # класс-хранилище для серверной стороны
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

    class UserHistory:
        # историй всех пользователей:
        def __init__(self, user, login_date, user_ip, user_port):
            self.id = None
            self.user = user
            self.login_time = login_date
            self.ip_address = user_ip
            self.port = user_port

    # ----------------------создание движка базы данных:--------------------------
    def __init__(self):
        # Создаём движок базы данных:
        self.database_engine = create_engine(SERVER_DATABASE, echo=False, pool_recycle=7200)
        # echo=False - отключает вывод на экран sql-запросов)
        # pool_recycle - по умолчанию соединение с БД через 8 часов простоя обрывается
        # Чтобы этого не случилось необходимо добавить pool_recycle=7200 (переустановка
        # соединения через каждые 2 часа)

        self.metadata = MetaData()  # что конкретно?
        # ------------------------подготовка создания таблиц-------------------------
        # всех пользователей:
        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),  # имя колонки должно совпадать с именем поля класса
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
        users_history_table = Table('Login_history', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('Users.id')),  # пользователи повторяются
                                    Column('login_time', DateTime),
                                    Column('ip_address', String),
                                    Column('port', Integer)
                                    )

        # -------------------создание таблиц:------------------------
        self.metadata.create_all(self.database_engine)

        # создание отображения:
        # связываем данные и таблицы:
        mapper(self.User, users_table)
        mapper(self.ActivUser, active_users_table)
        mapper(self.UserHistory, users_history_table)

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
        # запись в таблицу активных юзеров о входе:
        new_user = self.ActivUser(user.id, ip_address, port, datetime.datetime.now())
        print(new_user.ip_address)
        self.session.add(new_user)
        # сохранить вход в таблице истории:
        history = self.UserHistory(user.id, datetime.datetime.now(), ip_address, port)
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

    def all_history(self):
        users = self.session.query(self.User.name,
                                   self.UserHistory.login_time,
                                   self.UserHistory.ip_address,
                                   self.UserHistory.port,).join(self.User)
        return users.all()


if __name__ == '__main__':
    db_1 = ServerDb()
    db_1.user_login('Vasiliy', '192.168.1.1', 7777)
    db_1.user_login('Petia', '192.168.1.2',  8886)
    # print(db_1.ActivUser)
    db_1.user_logout('Petia')
    print(db_1.active_users_list())
    print(db_1.all_users_list())
    print(db_1.all_history())
