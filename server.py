import socket, threading

s = socket.socket()
s.bind(("", 8888))
s.listen()
tasks = {}

def client(c, a):
    tasks[a] = []
    c.send("Команды: ДОБАВИТЬ, УДАЛИТЬ, ВЫПОЛНИТЬ, СПИСОК, ВЫХОД\n".encode())
    while True:
        d = c.recv(1024).decode()
        if not d: break
        cmd = d.split()
        if cmd[0] == "ДОБАВИТЬ":
            tasks[a].append([d[9:], False])
            c.send(f"Успешно добавлено: {d[9:]}\n{show_tasks(tasks[a])}".encode())
        elif cmd[0] == "УДАЛИТЬ":
            deleted = tasks[a].pop(int(cmd[1])-1)
            c.send(f"Успешно удалено: {deleted[0]}\n{show_tasks(tasks[a])}".encode())
        elif cmd[0] == "ВЫПОЛНИТЬ":
            tasks[a][int(cmd[1])-1][1] = True
            c.send(f"Отмечено как выполненное!\n{show_tasks(tasks[a])}".encode())
        elif cmd[0] == "СПИСОК":
            c.send(show_tasks(tasks[a]).encode())
            continue
        elif cmd[0] == "ВЫХОД":
            c.send("До свидания!".encode())
            break
        else:
            c.send("Неизвестная команда".encode())
    c.close()
    del tasks[a]

def show_tasks(t):
    if not t:
        return "📋 Список задач пуст"
    return "\n".join(f"{i}. {'✓' if task[1] else '○'} {task[0]}" for i, task in enumerate(t, 1))

print("Сервер запущен на localhost:8888")
while 1:
    c, a = s.accept()
    threading.Thread(target=client, args=(c, a)).start()