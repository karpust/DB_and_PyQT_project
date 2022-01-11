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



