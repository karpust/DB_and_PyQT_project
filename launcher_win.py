""" Лаунчер для виндовс"""


import subprocess


process = []

while True:
    action = input('Выберите действие: '
                   'q - выход, '
                   's - запустить сервер, '
                   'k - запустить клиенты, '
                   'x - закрыть все окна: ')

    if action == 'q':
        break
    elif action == 's':
        process.append(
            subprocess.Popen('python server.py',
                             creationflags=subprocess.CREATE_NEW_CONSOLE))
    elif action == 'k':
        print('Убедитесь, что на сервере зарегистроровано необходимое '
              'количество клиентов c паролем 123')
        print('Первый запуск может быть долгим из-за генерации '
              'ключей шифрования')
        clients_count = int(
            input('Введите количество клиентов для запуска: '))
        for i in range(clients_count):
            process.append(
                subprocess.Popen(
                    f'python client.py -n client{i+1} -p 123',
                    creationflags=subprocess.CREATE_NEW_CONSOLE))
    elif action == 'x':
        while process:
            process.pop().kill()
