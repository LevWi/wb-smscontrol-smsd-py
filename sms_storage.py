# coding=utf-8

# For gammu smsd demon

import datetime
import json
import os

# INBOX_PATH = 'inbox/'
INBOX_PATH = '/mnt/tmpfs-spool/gammu/inbox/'
# OUTBOX_PATH = 'outbox/'
OUTBOX_PATH = '/mnt/tmpfs-spool/gammu/outbox/'
ERROR_PATH = '/mnt/tmpfs-spool/gammu/error/'
SENT_PATH = '/mnt/tmpfs-spool/gammu/sent/'
PHONE_LIST = '/home/phones.txt'

# Какой тип SMS будет посылаться устройством
SEND_FALSH_SMS = True


def filePath(path):
    return path if path.endswith('/') else path + '/'


def dellAllFilesInDir(dirPath):
    for fileName in os.listdir(dirPath):
        flPth = filePath(dirPath) + fileName
        os.remove(flPth)


def cleanSentPath():
    dellAllFilesInDir(SENT_PATH)


# return  [{number : ... , message : ... } , ...]
def readAllSms():
    arr = []
    for fileName in os.listdir(INBOX_PATH):
        flPth = filePath(INBOX_PATH) + fileName
        f = open(flPth, 'r')
        if fileName.startswith('IN') and fileName.endswith('.txt'):
            try:
                number = fileName.split('_')[3]
                message = f.read().decode('utf-16')
                arr.append(dict(number=number, message=message))
            except:
                print('Wrong message file {}'.format(fileName))
        f.close()
        os.remove(flPth)
    cleanSentPath()
    return arr



def sendSms(message, tel, flashSMS=SEND_FALSH_SMS):
    tm = datetime.datetime.now()
    if type(message) is not unicode:
        message = message.decode('utf-8')
    message = message.encode('utf-16')
    namefile = 'OUT{}{:02d}{:02d}_{:02d}{:02d}{:02d}_00_{}_{}.txt'.format(tm.year,
                                                                          tm.month,
                                                                          tm.day,
                                                                          tm.hour,
                                                                          tm.minute,
                                                                          tm.second,
                                                                          tel,
                                                                          str(tm.microsecond)[:3]
                                                                          )
    if flashSMS:
        namefile += 'f'
    f = open(OUTBOX_PATH + namefile, 'w')
    f.write(message)
    f.close()


class UserPhone(object):
    def __init__(self, rights, number):
        self.rights = rights
        self.number = number

    @property
    def fullnumber(self):
        return '+7' + self.number if len(self.number) == 10 else self.number

    @staticmethod
    def FormatNumber(str):
        if str == None:
            return None
        str = str.lstrip('+').lstrip('~')
        if len(str) == 11 and str.startswith('8'):
            str = str.replace("8", '', 1)
        elif len(str) == 11 and str.startswith('7'):
            str = str.replace("7", '', 1)
        return str

    @staticmethod
    def CreateFromDict(dictt, format_number):
        assert isinstance(dictt, dict)
        number = dictt.get('number')
        if format_number:
            number = UserPhone.FormatNumber(number)
        rights = dictt.get('rights')
        return UserPhone(rights, number)


def readphones_from_file():
    usersphones = []
    f = open(PHONE_LIST, 'r')
    json_string = f.read().replace("'", "\"") \
        # .replace('\n', ' ')\
    # .replace('\r', ' ')
    buffer = json.loads(json_string)
    f.close()
    for element in buffer:
        try:
            if type(element) is dict:
                new_phone = UserPhone.CreateFromDict(element, True)
                usersphones.append(new_phone)
        except:
            print("Error riding phone : {}".format(element))
    print 'Phone List : {}'.format(usersphones)
    return usersphones
