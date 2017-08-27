# coding=utf-8
##############

import time

import modbus_tk.defines as mdef

"""
For **additional params
max
min
mqttlink
smsNameIn
smsNameOut
mdbAddr
"""

class Signals(object):
    group = []
    def __init__(self, name, type, mdbdev=None, **additional):
        """
        :type name : str
        :type type: str
        :type limits : dict
        """
        if type not in ('bool','float', 'int', 'str') :
                raise ValueError("Wrong parametr 'type'  - need 'float' , 'int', 'str'")
        self.__useLimits = type in ('float', 'int')
        self.name = str(name)
        self.type = type
        self._data = None
        self.OnChangedData = None
        self.max, self.min = additional.get("max"), additional.get("min")
        self.mqttlink = str(ToUnicodeAll(additional.get('mqttlink')))
        self.smsNameIn = ToUnicodeAll(additional.get('smsNameIn'))
        self.smsNameOut = ToUnicodeAll(additional.get('smsNameOut'))
        self.smsOutPostfix = ToUnicodeAll(additional.get('smsOutPostfix'))
        self.convertFunc = additional.get('convertFunc')
        mdbAddr_ = additional.get('mdbAddr')
        self.mdbDev = mdbdev
        self.mdbAddr = None if mdbAddr_ == None else int(mdbAddr_)
 #   data = property()
    @property
    def data(self):
        return self._data
    @data.setter
    def data(self, value):
        #print 'property setter works'
        if value == None :
            pass
            #self._data = None
        elif self.type == 'bool':
            if value in [u'on', u'вкл']:
                value = True
            elif value in [u'off',u'выкл']:
                value = False
            else:
                value = bool(value)
        elif self.type == 'float':
            value = self.limit(float(value))
        elif self.type == 'int':
            value = self.limit(int(value))
        elif self.type == 'str':
            value = str(value)
        self._data = value
        if callable(self.OnChangedData):
            self.OnChangedData(self)

    def convertDataForModbus(self, value):
        if self.type in ['bool', 'float', 'int']:
            try:
                return self.limit(int(value))
            except:
                print('Error in convertDataForModbus() for data {}'.format(value))

    def ReadSignalFromDev(self):
        if self.canModbusWork:
            self.mdbDev.ReadSignalFromDev(self)
            if not self.mdbDev.lostDev:
                print('<-- read from device {} = {}'.format(self.name, self.data))
                return self.data
        return None

    def wrtSignalToDev(self, newVal, refreshSignal = False):
        if self.canModbusWork:
            print('--> try to write command {} = {}'.format(self.name, newVal))
            self.mdbDev.wrtSignalToDev(self, newVal, refreshSignal)
            if not self.mdbDev.lostDev:
                return self.data
        print('xx--> error to write command {} = {}'.format(self.name, newVal))
        return None

    @property
    def mqttData(self):
        if self.type == 'bool':
                return str(ToUnicodeAll(int(self.data)))
        return str(ToUnicodeAll(self.data))

    @property
    def smsOutData(self):
        if self.data is None:
            return u'н/д'
        if self.type == 'bool':
                return u'вкл' if self.data else u'выкл'
        return ToUnicodeAll(self.data)

    @property
    def canModbusWork(self):
        return self.mdbAddr is not None and self.mdbDev is not None

    def limit(self, value):
        """
        :rtype: None or Float or Int
        """
        if self.__useLimits and value is not None :
            if value > self.max and self.max is not None:
                return self.max
            if value < self.min and self.min is not None :
                return self.min
            return value
        else:
            return value

    @staticmethod
    def NewSignalToGroup(name, typ, mdbDev=None, **additional):
        obj = Signals(name, typ, mdbDev,  **additional)
        Signals.group.append(obj)
        return obj

#Преобразование числа к дополнительному коду опредленной длины
def twos_complement_convert(val, size=16):
    return ~(val ^ int('F' * (size / 4), 16)) if val >> size-1 else val


def isSmsNamesMatches(str1, names):
    if names is None:
        return False
    if type(names) not in [str, unicode, list]:
        raise TypeError('type of agr \'names\' need str, unicode, list of str or unicode ')
    str1 = str1.decode('utf8').lower() if type(str1) is str else str1.lower()
    names = names if type(names) is list else [names]
    for name in names:
        if type(name) not in [str, unicode]:
            raise TypeError('type of agr \'names\' need str, unicode, list of str or unicode ')
        name = name.decode('utf8').lower() if type(name) is str else name.lower()
        if name == str1:
                return True
    return False

def ToUnicodeAll(argument):
    t = type(argument)
    if t is unicode:
        return argument
    if t is str:
        return argument.decode('utf8')
    if argument is None:
        return u''
    if t is list:
        l = []
        for elem in argument:
            l.append(ToUnicodeAll(elem))
        return l
    else:
        return unicode(argument)

class MdbDevice(object) :
    def __init__(self, addr, portMaster=None, reconnectTimeout=10):
        self.addr = addr
        #self.signals = []
        self.__timeLastConnect = 0
        self.portMaster = portMaster
        self.__reconnectTimeout = reconnectTimeout
        self._lostDev = False

    def wrtSignalToDev(self, sign, newVal, refreshSignal = False):
        assert isinstance(sign, Signals)
        # old_data_ = self.ReadReg(sign.mdbAddr)
        # if old_data_ is not None:
        #         result = self.WrtReg(sign.mdbAddr, newVal)
        #         if result == 0 and refreshSignal:
        #             sign.data = newVal

        # Попробуем запись без предварительного чтения
        result = self.WrtReg(sign.mdbAddr, newVal)
        if result == 0 and refreshSignal:
                sign.data = newVal

    def ReadSignalFromDev(self, sign):
        assert isinstance(sign, Signals)
        new_data_ = self.ReadReg(sign.mdbAddr)
        if new_data_ is not None:
                    sign.data = new_data_ if not callable(sign.convertFunc) else sign.convertFunc(new_data_)

    def WrtReg(self, reg, newval):
        if self._canConnect() and self.portMaster is not None:
                try:
                    self.portMaster.execute(self.addr, mdef.WRITE_SINGLE_REGISTER, reg, output_value=newval)
                    self.lostDev = False
                    return 0
                except:
                    self.lostDev = True
                    return -1
        return -2

    def ReadReg(self, reg):
        if self._canConnect() and self.portMaster is not None:
            try:
                rg = self.portMaster.execute(self.addr, mdef.READ_HOLDING_REGISTERS, reg, 1)[0]
                self.lostDev = False
                return rg
            except:
                self.lostDev = True
                return None
        return None
    @property
    def lostDev(self):
        return self._lostDev
    @lostDev.setter
    def lostDev(self, val):
        if val == True :
            self.__timeLastConnect = time.time()
        self._lostDev = val
    def _canConnect(self):
        return time.time() - self.__timeLastConnect > self.__reconnectTimeout


dev_PLC = MdbDevice(1)
dev_VentSystem = MdbDevice(2)

RATIO_INT = 0.1
def word_to_int(val):
    return twos_complement_convert(val, 16) * RATIO_INT


sig_DiselBoilerTrigOn = Signals.NewSignalToGroup(
    "DiselBoilerTrigOn",
     "bool",
     dev_PLC,
     mqttlink="/devices/mdb/Boilers/Disel/controls/trigOn",
     mdbAddr=350,
     smsNameIn=[u"Disel", u'дизель', 'диз', 'дизельный котел', 'дизельный']
     #smsNameOut="Дизельный котел"
                                                 )
sig_PressureBoilersLine = Signals.NewSignalToGroup(
    "PressureBoilersLine",
    "float",
    dev_PLC,
    mqttlink="/devices/mdb/Sensors/controls/PressureBoilersLine",
    mdbAddr=434,
    convertFunc=word_to_int,
    smsNameOut="Давление в котлах",
    smsOutPostfix='ед'

                                )

sig_TempBoilersLine = Signals.NewSignalToGroup(
    "TempBoilersLine",
    "float",
    dev_PLC,
    mqttlink="/devices/mdb/Sensors/controls/TempBoilersLine" ,
    mdbAddr=428,
    convertFunc=word_to_int,
    smsNameOut=u"Температура котлов",
    smsOutPostfix='\xe2\x84\x83'
                                          )

sig_TempHeatingLine = Signals.NewSignalToGroup(
    "TempHeatingLine",
    "float",
    dev_PLC,
    mqttlink="/devices/mdb/Sensors/controls/TempHeatingLine",
    mdbAddr=430,
    convertFunc=word_to_int,
    smsNameOut=u"Температура отопления",
    smsOutPostfix='\xe2\x84\x83'
                                          )

sig_TempIndoor = Signals.NewSignalToGroup(
    "TempIndoor",
    "float",
    dev_PLC,
    mqttlink="/devices/mdb/Sensors/controls/TempIndoor",
    mdbAddr=432,
    convertFunc=word_to_int,
    smsNameOut="Температура помещения",
    smsOutPostfix='\xe2\x84\x83'
                                          )

sig_IndoorTempSet = Signals.NewSignalToGroup(
    "IndoorTempSet",
    "int",
    dev_PLC,
    min=0, max=50,
    mqttlink="/devices/mdb/Boilers/controls/TempSet",
    mdbAddr=335,
    smsNameIn=[u"Uctavka", 'уставка'],
    smsNameOut=u"Уставка помещения",
    smsOutPostfix='\xe2\x84\x83'
                                             )
sig_PresenceMode = Signals.NewSignalToGroup(
    "PresenceMode",
    "bool",
    dev_PLC,
    mqttlink="/devices/mdb/Boilers/controls/PresenceMode",
    mdbAddr=337,
    smsNameIn=[u"InHome", u'присутствие', 'дома', 'в доме', 'внутри'],
    smsNameOut=u"Режим присутствия"
                                                )

sig_PLC_VentPump = Signals.NewSignalToGroup(
    "VentPump",
    "int",
    dev_PLC,
    min=0, max=1,
    mqttlink="/devices/mdb/Ventilation/controls/VentPump",
    mdbAddr=333,
)

sig_PLC_Alarms = Signals.NewSignalToGroup(
    "PLC_Alarms",
    "int",
    dev_PLC,
    mqttlink="/devices/mdb/PLC/controls/Alarms",
    mdbAddr=341
)

sig_PLC_DInputs = Signals.NewSignalToGroup(
    "PLC_DInputs",
    "int",
    dev_PLC,
    mqttlink="/devices/mdb/PLC/controls/DInputs",
    mdbAddr=288
)

sig_VentSpeed = Signals.NewSignalToGroup(
    "VentSpeed",
    "int",
    dev_VentSystem,
    min=0, max=3,
    mqttlink="/devices/mdb/Ventilation/controls/speed",
    mdbAddr=100,
    smsNameIn=[u"Vent", 'вентиляция', 'вент'],
    smsNameOut=u"Скор. вентиляции"
)

sig_VentHeaterType = Signals.NewSignalToGroup(
    "VentHeaterType",
    "int",
    dev_VentSystem,
    min=0, max=3,
    mqttlink="/devices/mdb/Ventilation/controls/heaterType",
    mdbAddr=200
)

sig_PelletBoilerTrigOn = Signals.NewSignalToGroup(
    "PelletBoilerTrigOn",
    "bool",
    dev_PLC,
    mqttlink="/devices/mdb/Boilers/Pellet/controls/trigOn",
    mdbAddr=351,
    smsNameIn=[u"Pellet", 'дров', 'пеллетный котел', 'пеллет']
    #smsNameOut="Пелетный котел"
                                                 )
sig_BoilersTrigOff = Signals.NewSignalToGroup(
    "BoilersTrigOff",
    "bool",
    dev_PLC,
    mqttlink="/devices/mdb/Boilers/controls/trigAllOff",
    mdbAddr=352,
    smsNameIn=u"BoilersStop"
                                                )
sig_DiselBoilerOn = Signals.NewSignalToGroup(
    "DiselBoilerOn",
    "bool",
    None,
    smsNameOut=u"Дизельный котел"
)

sig_PelletBoilerOn = Signals.NewSignalToGroup(
    "PelletBoilerOn",
    "bool",
    None,
    smsNameOut=u"Пеллетный котел"
)

sig_ReceivedSMS = Signals.NewSignalToGroup(
    "Received SMS",
    "str",
    None,
    mqttlink="/devices/mdb/Modem/controls/ReceivedSMS"
)



# sig_Alarms = Signals.NewSignalToGroup(
#     "Alarms",
#     "str",
#     mqttlink="/devices/Alarms/controls/Info",
#     smsNameOut=u"Аварии"
# )






# class controlledDev :
#
#      def __int__(self):
#         self.TempSensor = [ "Temp Doma", "/devices/IndoorTemp/controls/Sensor1" , "N/D" , "int"]
#         #self.BoilerONOFF = [ "Kotel", "/devices/Rel_Boiler/controls/OnOff" , "N/D", "bool"]
#         self.Alarms = [ "Status", "/devices/AlarmsDev/controls/Info" , "N/D", "int"]
#         self.BoilerTempSet = [ "Uctavka","/devices/Rel_Boiler/controls/TempSet" , "N/D", "int"]
#         self.VentONOFF = [ "Vent", "/devices/Ventilation/controls/OnOff" , "0", "int"]
#         self.VentStaRead = [ "Ventilyac" , "/devices/Ventilation/controls/Status" , "0" , "int"]




