# coding=utf-8

import time

import mosquitto
import serial
import modbus_tk
from modbus_tk import modbus_rtu
import datetime
import process_signals
import ser_port_worker
import sms_storage

# logger = modbus_tk.utils.create_logger(name="console", record_format="%(message)s")

# Инициализация для wirenboard 5
rs485_mdbPort = modbus_rtu.RtuMaster(
    serial.Serial('/dev/ttyAPP2', baudrate=9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE))
rs485_mdbPort.set_timeout(1.3)
rs485_mdbPort.set_verbose(True)

process_signals.dev_PLC.portMaster = rs485_mdbPort
process_signals.dev_VentSystem.portMaster = rs485_mdbPort

ser_port_thread = ser_port_worker.SerialPortThread()


# =================================================
# Конфигурирование опроса по Modbus
#
# проверка калорифера
def checkHeaterType():
    heaterType = process_signals.sig_VentHeaterType.ReadSignalFromDev()
    NowspeedFanState = process_signals.sig_VentSpeed.data
    boiler_on_flag = process_signals.sig_DiselBoilerOn.data or process_signals.sig_PelletBoilerOn
    process_signals.sig_PLC_VentPump.wrtSignalToDev((heaterType == 1) and NowspeedFanState > 0 and boiler_on_flag)


# чтение аварий
def readAlarms():
    ##
    '''
    MDB_ALARMCODE_w.0 := NOT DI_MAIN_POWER_CONTROL ;
    MDB_ALARMCODE_w.1 := BOILERS_LINE_TEMP_fb._ERR >0;
    MDB_ALARMCODE_w.2 := HEATING_LINE_TEMP_fb._ERR >0;
    MDB_ALARMCODE_w.3 := INDOOR_TEMP_fb._ERR >0;
    MDB_ALARMCODE_w.4 := PRESSURE_BOILERS_LINE_fb._ERR > 0 ;
    '''
    # обрывы датчиков и питания
    process_signals.sig_PLC_Alarms.ReadSignalFromDev()
    # Connect signal for PLC
    if not process_signals.dev_VentSystem.lostDev:
        process_signals.dev_PLC.WrtReg(347, 1)
    # Контроль связи с ПЛК. Для отображения на дисплее
    process_signals.dev_PLC.WrtReg(340, 1)


def readBoilersInDI(*arg):
    regPLC_DI = process_signals.sig_PLC_DInputs.data
    if regPLC_DI is not None:
        process_signals.sig_PelletBoilerOn.data = regPLC_DI & 0b10 > 0
        process_signals.sig_DiselBoilerOn.data = regPLC_DI & 0b100 > 0


# Формирование циклических действий для опросчика
# Если сигнал доступен для опроса
ser_port_thread.listSignCycleRead = [checkHeaterType, readAlarms] + [sign for sign in process_signals.Signals.group if
                                                                     sign.canModbusWork]


# =================================================
# Кофигурация работы с mqtt сервером

# Вспомогательный таймер на выключение
class TON(object):
    def __init__(self, interval=0, itercount=None):
        self._startTime = 0
        self.interval = interval
        self._inWork = False
        self.itercount = itercount
        self.iter = 0

    def restart(self, interval=None, restartIter=False):
        if interval is not None:
            self.interval = interval
        self._startTime = time.time()
        self._inWork = True
        if self.itercount is not None and self.iter <= self.itercount:
            self.iter += 1
        if restartIter and self.itercount is not None:
            self.iter = 0

    @property
    def OUT(self):
        if self._inWork:
            self._inWork = time.time() - self._startTime < self.interval
        return not self._inWork and (self.itercount is None or self.iter <= self.itercount)


# Блокирующие таймеры
# Нужно немного выждать опрос всех устройств, прежде чем отправить ответ пользователю
sendSMSAnswerBanTON = TON(5)


def on_message(mosq, obj, msg):
    if msg.topic in process_signals.sig_ReceivedSMS.mqttlink:
        print('New message from mqtt : {} {}'.format(msg.topic, msg.payload))
        process_signals.sig_ReceivedSMS.data = msg.payload
        return
    for sign in process_signals.Signals.group:
        if msg.topic in sign.mqttlink and sign.canModbusWork:
                # Формируем команду для Modbus устройства
                newdata = sign.convertDataForModbus(msg.payload)
                if newdata is not None:
                    print('New message from mqtt : {} {} '.format(msg.topic, msg.payload))
                    ser_port_thread.sendToQueue([sign.wrtSignalToDev, (newdata, True)])
                    sendSMSAnswerBanTON.restart()
                    return


# def on_subscribe(mosq, obj, mid, granted_qos):
#     print("Subscribed: " + str(mid) + " " + str(granted_qos))


mqttc = mosquitto.Mosquitto()
mqttc.on_message = on_message
# mqttc.on_subscribe = on_subscribe
mqttc.connect("localhost", 1883, 60)

# подписываемся к сигналам
# Только к управляемым сигналам
mqttc.subscribe([(signal.mqttlink, 0) for signal in process_signals.Signals.group if
                 (len(signal.mqttlink) > 0 and len(signal.smsNameIn) > 0) or signal is process_signals.sig_ReceivedSMS])


# ===========================================

def createSmsAnswer():
    '''

    :return: string
    '''
    smsAnswer = ''
    reg = process_signals.sig_PLC_Alarms.data
    if not process_signals.dev_PLC.lostDev:
        if reg is not None:
            smsAnswer += u'Аварии:\n'
            if reg & 1 == 1:
                smsAnswer += u"-Нет основного питания\n"
            if reg & 0b10 > 0:
                smsAnswer += u"-Ошибка датчика котельного контура\n"
            if reg & 0b100 > 0:
                smsAnswer += u"-Ошибка датчика контура отопления\n"
            if reg & 0b1000 > 0:
                smsAnswer += u"-Ошибка датчика внутренней температуры\n"
            if reg & 0b1000 > 0:
                smsAnswer += u"-Ошибка датчика давления\n"
        for sign in process_signals.Signals.group:
            if isinstance(sign, process_signals.Signals):
                if sign is not process_signals.sig_VentSpeed and sign.smsNameOut is not None and len(sign.smsNameOut):
                    # print('types {} {} - {}'.format(type(sign.smsNameOut) , type(sign.smsOutData), sign.name))
                    smsAnswer += u'{} : {}\n '.format(sign.smsNameOut, sign.smsOutData + sign.smsOutPostfix)
    else:
        smsAnswer += u'Ошибка связи с ПЛК\n '

    if not process_signals.dev_VentSystem.lostDev:
        sign1 = process_signals.sig_VentSpeed
        smsAnswer += u'{} : {}\n '.format(sign1.smsNameOut, sign1.smsOutData)
    else:
        smsAnswer += u'Ошибка связи с вентустановкой\n'
    return smsAnswer


# Для переодического уведомления
class Alarm(object):
    def __init__(self, condition, mess, tonBlock=None):
        self.condition = condition
        self.message = mess
        self._ton = tonBlock
        self.conditionOld = False

    def readcondition(self):
        res = self.condition()
        if not res and isinstance(self._ton, TON):
            self.restartTimer()
        self.conditionOld = res
        return res

    @property
    def messageStr(self):
        if callable(self.message):
            return self.message()
        else:
            return self.message

    @property
    def OUT(self):
        res = self.readcondition()
        if isinstance(self._ton, TON):
            res = res and self._ton.OUT
        return res

    def blockAlarm(self):
        if isinstance(self._ton, TON):
            self._ton.restart()

    def restartTimer(self):
        if isinstance(self._ton, TON):
            self._ton.restart(restartIter=True)


# Градус цельсия значок не отображается
alarmTempBoilersLine = Alarm(
    lambda: process_signals.sig_TempBoilersLine.data >= 87.5,
    lambda: '!!Внимание!!\nКритическая температура котлового контура: {}'.decode('utf8')
            .format(process_signals.sig_TempBoilersLine.smsOutData + sign.smsOutPostfix),
    TON(60 * 30, 3)
)

alarmIndoorTemp = Alarm(
    lambda: -50 < process_signals.sig_TempIndoor.data < 6,
    lambda: ('!!Внимание!!\nНизкая температура помещения: {}'.decode('utf8')
             .format(process_signals.sig_TempIndoor.smsOutData + sign.smsOutPostfix)),
    TON(60 * 30, 3)
)

alarmTest = Alarm(
    lambda: not (time.time() % 20 * 60) < 1,
    lambda: ('!!Тестовое аварийное сообщение!!\nНизкая температура помещения: {}'.decode('utf8')
             .format(process_signals.sig_TempIndoor.smsOutData + process_signals.sig_TempIndoor.smsOutPostfix)),
    TON(60 * 5, 3)
)


# чтобы избежать конфликтов с именем файлами замедлим создание
# sms файлов
def sendSMSwithInterval(message, number):
    sms_storage.sendSms(message, number)
    time.sleep(1.1)


# Публикация неуправляющих переменных
def publicSignal(signal):
    assert isinstance(signal, process_signals.Signals)
    print('Public message: {} = {}'.format(signal.mqttlink, signal.mqttData))
    try:
        mqttc.publish(signal.mqttlink, signal.mqttData)
    except:
        print 'Error public topic'


# def resetMqttSMScommand():
#     try:
#         mqttc.publish(process_signals.sig_ReceivedSMS.mqttlink, '')
#     except:
#         print 'Error public topic'

for signal in process_signals.Signals.group:
    assert isinstance(signal, process_signals.Signals)
    if len(signal.mqttlink) > 0 and signal.canModbusWork and signal.smsNameIn == '':
        signal.OnChangedData = publicSignal
# Действие будет выполняться при считывании дискретных входов
process_signals.sig_PLC_DInputs.OnChangedData = readBoilersInDI

if __name__ == "__main__":
    mqttc.loop_start()
    phonelist = sms_storage.readphones_from_file()
    ser_port_thread.start()
    while 1:
        # Отправка SMS после истечения интервала в sendSMSAnswerBanTON при приходе нового события on_message
        if sendSMSAnswerBanTON.OUT:
            if process_signals.sig_ReceivedSMS.data is not None and len(process_signals.sig_ReceivedSMS.data) > 1:
                number, smsCommand = None, None
                try:
                    number, smsCommand = process_signals.sig_ReceivedSMS.data.split('**', 1)
                    print('Message readed {} - {}'.format(number, smsCommand))
                except ValueError:
                    print('WrongFormat for "sig_ReceivedSMS.data" , value = {}'
                          .format(process_signals.sig_ReceivedSMS.data))
                if number is not None:
                    if len(number) == 10:
                        number = '+7' + number
                    if smsCommand in ['refresh_data', 'status_need']:
                        message = createSmsAnswer()
                        sendSMSwithInterval(message, number)
                    elif smsCommand == 'bad_format':
                        sendSMSwithInterval(u'Неверный формат сообщения', number)
                process_signals.sig_ReceivedSMS.data = ''
        # Рассылка SMS по авариям
        for al in [alarmIndoorTemp, alarmTempBoilersLine]:
            assert isinstance(al, Alarm)
            if al.OUT:
                for user in phonelist:
                    assert isinstance(user, sms_storage.UserPhone)
                    if 'admin' in user.rights:
                        sendSMSwithInterval(al.messageStr, user.fullnumber)
                        al.blockAlarm()
        if not ser_port_thread.isAlive():
            print 'restart modbus thread'
            ser_port_thread.start()
        time.sleep(0.05)
