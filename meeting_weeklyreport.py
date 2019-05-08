#!/usr/bin/env python
#_*_ coding:utf-8 _*_
'''
@auther: tanglei
@contact: tanglei_0315@163.com
@file: meeting_weeklyreport.py
@time: 2019/4/25 10:34
'''
import os
import configparser
import time
import json

from common.logger import logger
from file_format.file_format import DeleteBOM_UTF8,file_format
from api_analyze.api import send_api
from excel.excel_code import ExcelHandle

#获取配置文件中的值
setting_path = os.path.join(os.path.abspath('conf'),'setting.ini')
#DeleteBOM_UTF8(setting_path)

conf = configparser.ConfigParser()
conf.read(setting_path,encoding='utf-8')
#json文件的路径
json_path = conf.get("file_format","file_path")
#商业用户名称
business_name = conf.get("file_format","business_name")
#需要匹配的excel文件名称
excel_name = os.path.join(json_path,conf.get("excel","excel_name"))
#是否进行excel的比对
is_excel = int(conf.get("excel","is_excel"))
#接口访问的地址
http_api = conf.get("api_analyze","api")
#是否开启数据压缩
is_gzip = conf.get("api_analyze","is_gzip")
#当前时间，用于备份文件用
today_time = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
#生成的excel报表文件名称
excel_file = os.path.join(json_path,"%s报表.xlsx" % (business_name))
#excel备份目录路径
excel_backup_dir = os.path.join(json_path,"backup")
#excel备份文件名称
excel_backup_file = "%s报表%s.xlsx" % (business_name,today_time)
'''
#模拟请求的参数数据
response_data = {
  "state": {
    "resultCode": 0,
    "msg": "根据您的输入条件【服务器耗时:17秒，结果大小:1KB1019Byte】"
  },
  "result": {
    "90400707": {
      "2019-02-18 08:40:55->2019-02-18 10:37:38": {
        "c2c": {
          "630106744->63010673": {
            "lostBadNum": 0,
            "lost0To2": 784,
            "eBadNum": 1,
            "eAllNum": 223,
            "lost2To100": 2
          },
          "630106711->63010673": {
            "lostBadNum": 0,
            "lost0To2": 784,
            "eBadNum": 200,
            "eAllNum": 223,
            "lost2To100": 2
          },
          "63010699->63010673": {
            "lostBadNum": 0,
            "lost0To2": 92,
            "eBadNum": 44,
            "eAllNum": 48,
            "lost2To100": 3
          }
        },
        "count": {
          "info": {
            "userNum": 4,
            "consumeTime": 11216,
            "qosTableAllNum": 7,
            "qosTableCountNum": 7,
            "recordNum": 12814
          }
        }
      }
    },
    "80457157": {
      "2019-02-15 08:01:00->2019-02-15 10:08:36": {
        "c2c": {
          "69900031->69900034": {
            "lostBadNum": 0,
            "lost0To2": 574,
            "eBadNum": 4,
            "eAllNum": 576,
            "lost2To100": 1
          },
          "69900031->69900033": {
            "lostBadNum": 0,
            "lost0To2": 690,
            "eBadNum": 4,
            "eAllNum": 688,
            "lost2To100": 1
          }
        },
        "count": {
          "info": {
            "userNum": 444,
            "consumeTime": 1908,
            "qosTableAllNum": 6,
            "qosTableCountNum": 5,
            "recordNum": 3913
          }
        }
      },
      "2019-02-15 09:00:00->2019-02-15 10:08:36": {
        "c2c": {
          "69900031->69900034": {
            "lostBadNum": 0,
            "lost0To2": 574,
            "eBadNum": 4,
            "eAllNum": 576,
            "lost2To100": 1
          },
          "69900038->69900077": {
            "lostBadNum": 0,
            "lost0To2": 690,
            "eBadNum": 4,
            "eAllNum": 688,
            "lost2To100": 1
          }
        },
        "count": {
          "info": {
            "userNum": 10,
            "consumeTime": 4155,
            "qosTableAllNum": 6,
            "qosTableCountNum": 5,
            "recordNum": 3913
          }
        }
      }
    }
  }
}
'''
if __name__ == "__main__":

    #将json文件进行合并,并格式化成api接口形式的数据格式
    ff = file_format(file_path=json_path,business_name=business_name)
    ff_list = ff.json_file_extract()
    #判断是否进行excel的匹配
    if is_excel != 1:
        json_info = ff.remove_lshy()
        json_data = ff.api_json_format(source_data=json_info,isgzip=is_gzip)
        print(json_data)
    else:
        # 读取excel文件后的数据信息
        excel_handle = ExcelHandle(excel_path=excel_name,is_excel=is_excel)
        excel_info = excel_handle.read_excel()
        json_info = ff.remove_lshy()
        source_list = ff.Name_to_Number(json_info=json_info,excel_info=excel_info)
        json_data = ff.api_json_format(source_data=source_list,isgzip=is_gzip)
        print(json_data)

    #会议总数
    print("会议分析程序启动的时间%s" % (today_time))
    meeting_count = len(json_data["data"])
    response_api_Analyze_list = []
    for item in range(meeting_count):
        print("总共需要分析的会议个数:%s" % (meeting_count))
        print("剩余未分析的会议个数:%s" % (meeting_count - item))
        meeting_data = json.dumps({"gzip":is_gzip,"data":[json_data["data"][item]]})
        #将json_data当做参数传进api接口，获取响应的数据
        headers = {
          "content-type":"application/json"
        }
        api_data = send_api()
        print("开始调用分析接口分析%s会议" % (json_data["data"][item]["mid"]))
        response_data = api_data.Post_Data_Api(url=http_api,params=meeting_data,headers=headers)
        print("分析%s会议的接口调用完毕" % (json_data["data"][item]["mid"]))
        print("分析接口的响应数据%s" % (response_data))
        print("开始对%s会议响应的数据进行数据整理" % (json_data["data"][item]["mid"]))
        #判断响应的数据是否需要和excel进行匹配
        if is_excel == 1:
            response_api_Analyze = json.loads(json.dumps(api_data.Analyze_Response(response_data=response_data,excel_data=excel_info)).strip("[]"))
        else:
            response_api_Analyze = json.loads(json.dumps(api_data.Analyze_Response(response_data=response_data)).strip("[]"))
        print("%s会议的数据整理完毕" % (json_data["data"][item]["mid"]))
        response_api_Analyze_list.append(response_api_Analyze)
        print("程序暂停2秒钟")
        time.sleep(2)

    print("开始将整理的全部数据都写入到excel")
    #将响应的数据格式化后写入到excel中
    excel_into = ExcelHandle(excel_path=excel_name, is_excel=is_excel)
    excel_into.set_excel_data(excel_file=excel_file,excel_backup_dir=excel_backup_dir,excel_backup_file=excel_backup_file,response_list=response_api_Analyze_list)
    print("写入excel数据完毕")