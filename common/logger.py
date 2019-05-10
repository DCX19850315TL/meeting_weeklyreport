#!/usr/bin/env python
#_*_ coding:utf-8 _*_
'''
@auther: tanglei
@contact: tanglei_0315@163.com
@file: logger.py
@time: 2019/4/25 11:22
'''
import os
import logging
import logging.config
import logging.handlers
import configparser

#定义setting配置文件路径
#parent_dir = os.path.dirname(os.path.dirname(__file__))
#setting_file = os.path.join(parent_dir,'conf\setting.ini')
setting_file = os.path.join(os.path.abspath('conf'),'setting.ini')
conf = configparser.ConfigParser()
conf.read(setting_file,"utf-8")
#日志名称
LogName = conf.get("log","name")
#LogFile = os.path.join(parent_dir,'logs\{LogName}'.format(LogName=LogName))
LogFile = os.path.join(os.path.abspath('logs'),'%s' % (LogName))
#日志级别
LogLevel = conf.get("log","level")
#单个日志文件的大小
FileSize = int(conf.get("log","file_size"))
#轮训保留的日志文件个数
RotationNumber = int(conf.get("log","rotation_number"))
def logger():

    if not os.path.isfile(LogFile):
        open(LogFile, "w+").close()

    #定义字典内容
    log_setting_dict = {"version":1,
                        "incremental":False,
                        "disable_existing_loggers":True,
                        "formatters":{"precise":
                                          {"format":"%(asctime)s %(filename)s(%(lineno)d - %(processName)s - %(threadName)s - %(funcName)s): %(levelname)s %(message)s",
                                           "datefmt":"%Y-%m-%d %H:%M:%S"}},
                        "handlers":{"handlers_RotatingFile":
                                        {"level": LogLevel,
                                         "formatter": "precise",
                                         "class": "logging.handlers.RotatingFileHandler",
                                         "filename": LogFile,
                                         "mode": "a",
                                         "maxBytes": FileSize*1024*1024,
                                         "backupCount": RotationNumber
                                         }},
                        "loggers":{"logger":
                                       {"level":LogLevel,
                                        "handlers":["handlers_RotatingFile"]}}}
    logging.config.dictConfig(log_setting_dict)

    logger = logging.getLogger("logger")

    return logger