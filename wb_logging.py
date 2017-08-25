# coding:utf-8

import logging


logger = logging.getLogger('logger')

consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

consoleHandler.setFormatter(formatter)

