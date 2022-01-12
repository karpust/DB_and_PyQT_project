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
        def __init__(self, user_ip, user_port, user_login_time):
            self.id = None
            self.ip = user_ip
            self.port = user_port
            self.login_time = user_login_time  # когда залогинился или время актив?

    # создание движка базы данных:
    def __init__(self):
        # Создаём движок базы данных:
        self.database_engine = create_engine(SERVER_DATABASE, echo=False, pool_recycle=7200)
        # echo=False - отключает вывод на экран sql-запросов)
        # pool_recycle - по умолчанию соединение с БД через 8 часов простоя обрывается
        # Чтобы этого не случилось необходимо добавить pool_recycle=7200 (переустановка
        # соединения через каждые 2 часа)

        self.metadata = MetaData()  # что конкретно?
        # создание таблиц
        # всех пользователей:
        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('last_login', DateTime)
                            )

        # историй всех пользователей:
        users_history_table = Table('Login_history', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('name', ForeignKey('Users.id'), unique=True),
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

        # создаем таблицы:
        self.metadata.create_all(self.database_engine)

        # создаем отображения:
        # связываем данные и таблицы:
        mapper(self.User, users_table)
        mapper(self.UserHistory, users_history_table)
        mapper(self.ActivUser, active_users_table)

        # создаем сессию:
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()



