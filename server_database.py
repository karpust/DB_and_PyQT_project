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
            self.id = None
            self.name = user_name
            self.last_login = datetime.datetime.now()

    class UserHistory:
        # историй всех пользователей:
        def __init__(self, user_id, login_date, user_ip, user_port):
            self.user = user_id
            self.date = login_date
            self.ip = user_ip
            self.port = user_port
            self.id = None  # зачем тут юзер ид?

    class ActivUser:
        # всех активных пользователей:
        def __init__(self, user_id, user_ip, user_port, user_login_time):
            self.user = user_id
            self.ip = user_ip
            self.port = user_port
            self.login_time = user_login_time  # когда залогинился или время актив?
            self.id = None

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
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('last_login', DateTime)
                            )

        # историй всех пользователей:
        users_history_table = Table('Login_history', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('Users.id'), unique=True),
                                    Column('login_time', DateTime),
                                    Column('ip_address', String),
                                    Column('port', Integer)
                                    )

        # всех активных пользователей:
        active_users_table = Table('Active_users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('name', ForeignKey('Users.id'), unique=True),
                                   Column('ip_address', String),
                                   Column('port', Integer),
                                   Column('login_time', DateTime)
                                   )

        # -------------------создание таблиц:------------------------
        self.metadata.create_all(self.database_engine)

        # создание отображения:
        # связываем данные и таблицы:
        mapper(self.User, users_table)
        mapper(self.UserHistory, users_history_table)
        mapper(self.ActivUser, active_users_table)

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
        self.session.add(new_user)
        # сохранить вход в таблице истории:
        history = self.UserHistory(user.id, datetime.datetime.now(), ip_address, port)
        self.session.add(history)
        # сохранить изменения:
        self.session.commit()


if __name__ == '__main__':
    db_1 = ServerDb()
    db_1.user_login('Vasiliy', '192.168.1.1', 7771)
    db_1.user_login('Petia', '192.168.1.2', 8888)
