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
from file_format.file_format import DeleteBOM_UTF8,file_format,list_comparison_list
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
#用户中心的接口地址
usercenter_api = conf.get("api_analyze","usercenter_api")
#当前时间，用于备份文件用
today_time = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
#生成的excel报表文件名称
excel_file = os.path.join(json_path,"%s报表.xlsx" % (business_name))
#excel备份目录路径
excel_backup_dir = os.path.join(json_path,"backup")
#excel备份文件名称
excel_backup_file = "%s报表%s.xlsx" % (business_name,today_time)
#失败的视频号对应名称的会议号信息存储文件
fail_tempfile = os.path.join(os.path.abspath("data/%s" % (business_name)),"视频号对应名称失败的会议号信息.txt")
#分析服务宕掉后,存储未分析的会议号信息文件
fail_meetingfile = os.path.join(os.path.abspath("data/%s" % (business_name)),"服务宕掉后剩余未分析的会议号信息.txt")

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
    print("会议分析程序启动的时间:%s" % (today_time))
    program_starttime = int(time.time())
    meeting_count = len(json_data["data"])
    meeting_data_list = []
    response_api_Analyze_list = []
    fail_usercenter_api_list = []
    for item in range(meeting_count):
        print("总共需要分析的会议个数:%s" % (meeting_count))
        print("剩余未分析的会议个数:%s" % (meeting_count - item))
        meeting_data = json.dumps({"gzip":is_gzip,"data":[json_data["data"][item]]})
        meeting_data_temp = json_data["data"][item]
        #将json_data当做参数传进api接口，获取响应的数据
        headers = {
          "content-type":"application/json"
        }
        api_data = send_api()
        print("开始调用分析接口分析%s会议" % (json_data["data"][item]["mid"]))
        try:
            response_data = api_data.Post_Data_Api(url=http_api,params=meeting_data,headers=headers)
        except Exception as e:
            if e.args[0] == 10061:
                print("分析服务接口无法访问,请查看分析服务是否正常,配置文件是否正确")
                break
            elif e.args[0] == 10054:
                list_comparison_list(json_data["data"],meeting_data_list,fail_meetingfile)
                print("分析服务于%s宕掉了,剩余未被分析的会议号信息存放在%s" % (today_time,fail_meetingfile))
                break
        else:
            print("分析%s会议的接口调用完毕" % (json_data["data"][item]["mid"]))
            print("响应数据%s" % (response_data))
            print("开始对%s会议响应的数据进行数据整理" % (json_data["data"][item]["mid"]))
            #判断响应的数据是否需要和excel进行匹配
            if is_excel == 1:
                response_api_Analyze = json.loads(json.dumps(api_data.Analyze_Response(response_data=response_data,excel_data=excel_info)).strip("[]"))
            else:
                response_api_Analyze = json.loads(json.dumps(api_data.Analyze_Response(response_data=response_data)).strip("[]"))
            print("%s会议的数据整理完毕" % (json_data["data"][item]["mid"]))
            print(response_api_Analyze)
            if response_api_Analyze["Number_Count"] == 10041:
                print("用户中心接口调用失败，导致视频号无法对应昵称")
                fail_usercenter_api_dict = {"name":response_api_Analyze["Meeting_Number"],"begTS":response_api_Analyze["Start_Time"],"endTS":response_api_Analyze["End_Time"]}
                fail_usercenter_api_list.append(fail_usercenter_api_dict)
            else:
                response_api_Analyze_list.append(response_api_Analyze)
                meeting_data_list.append(meeting_data_temp)
            print("程序暂停2秒钟")
            time.sleep(2)

    #判断分析整理完的数据是否为空，不为空的话讲数据写入到excel中
    if response_api_Analyze_list == []:
        pass
    else:
        print("开始将整理的全部数据都写入到excel")
        #将响应的数据格式化后写入到excel中
        excel_into = ExcelHandle(excel_path=excel_name, is_excel=is_excel)
        excel_into.set_excel_data(excel_file=excel_file,excel_backup_dir=excel_backup_dir,excel_backup_file=excel_backup_file,response_list=response_api_Analyze_list)
        print("写入excel数据完毕")

    #判断用户中心名称匹配失败的列表是否为空，不为空的话将失败的会议号信息写入到txt中，已备重新分析
    if fail_usercenter_api_list == []:
        pass
    else:
        #将不合格的数据写入到tmp文件，准备进行手动重试
        fail_list_str = json.dumps(fail_usercenter_api_list)
        print("开始往文件中写入失败的会议号信息")
        with open(fail_tempfile,"w") as f:
            f.truncate()
            f.write(fail_list_str)
        print("失败会议号的信息写入完毕")
    program_endtime = int(time.time())
    count_time = program_endtime - program_starttime
    m,s = divmod(count_time,60)
    h,m = divmod(m,60)
    count_time_time = ("%02d:%02d:%02d" % (h, m, s))
    print("会议分析程序结束的时间:%s,总共用时%s" % (today_time,count_time_time))
