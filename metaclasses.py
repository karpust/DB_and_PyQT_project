"""
1. Реализовать метакласс ClientVerifier, выполняющий базовую проверку класса
«Клиент» (для некоторых проверок уместно использовать модуль dis):

    отсутствие вызовов accept и listen для сокетов;
    использование сокетов для работы по TCP;

2. Реализовать метакласс ServerVerifier, выполняющий базовую проверку класса «Сервер»:

    отсутствие вызовов connect для сокетов;
    использование сокетов для работы по TCP.
"""

import dis


class ClientVerifier(type):
    def __init__(cls, clsname, bases, clsdict):
        """
        метакласс, выполняющий базовую проверку класса «Клиент»
        на отсутствие вызовов accept и listen для сокетов;
        на использование сокетов для работы по TCP;
        """
        # clsname - экземпляр метакласса - Server
        # bases - кортеж базовых классов - ()
        # clsdict - словарь атрибутов и методов экземпляра метакласса
        absente_methods = ('accept', 'listen')
        methods = []
        attrs = []
        for func in clsdict:
            try:
                ret_val = dis.get_instructions(clsdict[func])
            # если это не функция(порт):
            except TypeError:
                pass
            # если это функция:
            else:
                for i in ret_val:
                    # opname - имя для операции
                    # если это метод:
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            # заполняем список методами класса
                            methods.append(i.argval)
                    # если это атрибут:
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            # заполняем список атрибутами класса
                            attrs.append(i.argval)
        for command in ('accept', 'listen'):
            if command in methods:
                raise TypeError(f'There must be no such attribute in the class: '
                                f'{command}')
        # if 'SOCK_STREAM' not in attrs:
        #     raise TypeError(f'Socket is not correctly initialized: '
        #                     f'{attrs}')
        print(f'methods: {methods}')
        print('==============================')
        print(f'attrs: {attrs}')
        # вызываем конструктор предка:
        super().__init__(clsname, bases, clsdict)















