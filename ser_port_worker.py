# coding=utf-8


import Queue
import threading
import time

import process_signals

'''
Добавлять очередь каких либо действий с COM портом
Запись, чтение
Запись выполняется в приоритете, может комбинироваться с чтением для подтверждения
Завязка на работу с mqtt сервером
'''


class SerialPortThread(threading.Thread):
    def __init__(self, periodCicle=0):
        # Обязательно инициализируем супер класс (класс родитель)
        super(SerialPortThread, self).__init__()

        # Устанавливаем поток в роли демона, это необходимо что бы по окончании выполнения
        # метода run() поток корректно завершил работу,а не остался висеть в ожидании
        # self.setDaemon(True)

        self.__canWork = False
        self.period = periodCicle
        # очередь циклических действий или сигналов
        self.listSignCycleRead = []
        # очередь действий на запись
        self.queueWrite = Queue.Queue()

    def run(self):
        self.__canWork = True
        index = 0
        while self.__canWork:
            if not self.queueWrite.empty():
                act = self.queueWrite.get()
                callFunction(act)
            else:
                if len(self.listSignCycleRead) > 0:
                    if index > (len(self.listSignCycleRead) - 1):
                        index = 0
                    neda = self.listSignCycleRead[index]
                    index += 1
                    if isinstance(neda, process_signals.Signals):
                        neda.ReadSignalFromDev()
                    elif callable(neda):
                        neda()
                else:
                    time.sleep(0.1)
            time.sleep(self.period)

    def stopWorking(self):
        self.__canWork = False

    # Добавляем действие на запись. Работает приоритетно
    def sendToQueue(self, act):
        self.queueWrite.put(act)

    def readSignals(self):
        pass


# Вызов функции с аргументами вида
# func1
# [ func1 , *arg ]
def callFunction(arg):
    # print('call function {}'.format(arg))
    if callable(arg):
        arg()
    elif type(arg) is list:
        if callable(arg[0]):
            func = arg[0]
            if len(arg) == 2:
                args = arg[1]
                if type(args) is tuple:
                    func(*args)
                    return
                func(args)
                return
            func()
