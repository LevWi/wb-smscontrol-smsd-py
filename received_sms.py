# coding=utf-8
#  !/usr/bin/env python

import mosquitto

import process_signals as signalsDB
import sms_storage


def is_number(str):
    try:
        float(str)
        return True
    except ValueError:
        return False

# def ParseSMS1(stri):
#     answer = ''
#     if stri == '0421043E043E043104490435043D0438043500200434043E0441044204300432043B0435043D043E':
#         print 'message received'
#         return ''
#     stri = stri.lower()
#     if stri == 'reboot':
#         answer = 'reboot'
#         return answer
#     if stri == 'status':
#         answer = ''
#         if 'loVen' in Alarms.status: #ВОТ ТАК ИСПОЛЬЗОВАТЬ
#             answer += 'HET Ventilyac\n'
#         else:
#             answer += '{} = {}\n'.format(VentStaRead.place, VentStaRead.status) #ВОТ ТАК ИСПОЛЬЗОВАТЬ
#         if 'LostPWR' in Alarms.status: #ВОТ ТАК ИСПОЛЬЗОВАТЬ
#             answer += 'HET PLC\n'
#         else:
#             if 'LostPWR' in Alarms.status: #ВОТ тАК ЛУЧШЕ
#                 answer += 'HET PITANIA\n'
#             if (devices.Alarms[2].find('SenBrk') >= 0):
#                 answer += 'Obryv Datchik\n'
#             else:
#                 answer += '{} = {}\n'.format(devices.TempSensor[0], devices.TempSensor[2])
#                 answer += '{} = {}\n'.format(devices.BoilerTempSet[0], devices.BoilerTempSet[2])
#             if (devices.Alarms[2].find('PmpAL1') >= 0) and (devices.Alarms[2].find('PmpAL2') >= 0):
#                 answer += 'Avar Nasos1+2\n'
#             elif (devices.Alarms[2].find('PmpAL2') >= 0):
#                 answer += 'Avar Nasos2\n'
#             elif (devices.Alarms[2].find('PmpAL1') >= 0):
#                 answer += 'Avar Nasos1\n'
#         return answer

def ParseSMS(stri):
    answer = ''
    stri = stri.lower()
    if stri == 'reboot':
        answer = 'reboot'
        return answer
    if stri == 'status':
        #mqttc.publish(signalsDB.sig_ReceivedSMS.mqttlink, 'STATUS_NEED')
        return 'status_need'
        '''
        if (devices.Alarms[2].find('loVen') >= 0):
            answer += 'HET Ventilyac\n'
        else:
            answer += '{} = {}\n'.format(devices.VentStaRead[0], devices.VentStaRead[2])
        if (devices.Alarms[2].find('loPLC') >= 0):
            answer += 'HET PLC\n'
        else:
            if (devices.Alarms[2].find('LostPWR') >= 0):
                answer += 'HET PITANIA\n'
            if (devices.Alarms[2].find('SenBrk') >= 0):
                answer += 'Obryv Datchik\n'
            else:
                answer += '{} = {}\n'.format(devices.TempSensor[0], devices.TempSensor[2])
                answer += '{} = {}\n'.format(devices.BoilerTempSet[0], devices.BoilerTempSet[2])
            if (devices.Alarms[2].find('PmpAL1') >= 0) and (devices.Alarms[2].find('PmpAL2') >= 0):
                answer += 'Avar Nasos1+2\n'
            elif (devices.Alarms[2].find('PmpAL2') >= 0):
                answer += 'Avar Nasos2\n'
            elif (devices.Alarms[2].find('PmpAL1') >= 0):
                answer += 'Avar Nasos1\n'
        '''
        return answer
    commands = stri.strip(', ').replace('\n', '')
    commands = commands.split(',')
    for command in commands:
        elems = command.strip(' ').split('=')
        if len(elems) != 2:
            return 'bad_format'
        smsNamePar = elems[0].strip(' ')
        parValue = elems[1].strip(' ')
        for dev in signalsDB.Signals.group:
            assert isinstance(dev, signalsDB.Signals)
            if signalsDB.isSmsNamesMatches( smsNamePar ,  dev.smsNameIn) :
                try:
                    dev.data = parValue
                    public_topic_on_web_serv(dev.mqttlink, dev.mqttData)
                    answer = 'refresh_data'
                    break
                except:
                    return 'bad_format'
                    # if dev.type == "int":
                    #     if elems[1].isdigit():
                    #         set_ = int(elems[1])
                    #         # print dev[2]+'/on,' + str(set)
                    #         answer += dev[0] + ' = ' + str(set_) + '\n'
                    #         mqttc.publish(dev[1] + '/on', str(set_))
                    # elif dev.type == "bool":
                    #     if elems[1] == 'on':
                    #         # print dev[2]+'/on,' + '1'
                    #         answer += dev[0] + ' on\n'
                    #         mqttc.publish(dev[1] + '/on', "1")
                    #     elif elems[1] == 'off':
                    #         # print dev[2]+'/on,' + '0'
                    #         answer += dev[0] + ' off\n'
                    #         mqttc.publish(dev[1] + '/on', "0")
    return answer

def msg_on_web_serv(msg):
    mqttc.publish( signalsDB.sig_ReceivedSMS.mqttlink, msg)

def public_topic_on_web_serv(mqttlink, topic):
    try:
        mqttc.publish(mqttlink, topic)
    except:
        print 'Error public topic'

if __name__ == "__main__":
            mqttc = mosquitto.Mosquitto()
            #mqttc.on_message = on_message
            #mqttc.on_connect = on_connect
            #mqttc.on_publish = on_publish
            #mqttc.on_subscribe = on_subscribe
            #mqttc.subscribe([(list[0][1], 0), (list[1][1], 0), (list[2][1], 0), (list[3][1], 0), (list[4][1], 0)])
            #mqttc.loop_start()
            phonelist = []
            phonelist = sms_storage.readphones_from_file()
            if len(phonelist) == 0:
                    msg_on_web_serv('Phonelist wrong...')
                    exit()
            smsArr = sms_storage.readAllSms()
            if len(smsArr) > 0 :
                mqttc.connect("localhost", 1883, 60)
                for sms_elem in smsArr :
                    sms_str = sms_elem.get('message')
                    number_str = sms_storage.UserPhone.FormatNumber(sms_elem.get('number'))
                    if sms_str is not None and number_str is not None:
                         for users in phonelist :
                             if number_str in users.number:
                                 prs = ParseSMS(sms_str)
                                 if len(prs) > 0:
                                     msg_on_web_serv(number_str + "**" + prs)
                             break




