#!/usr/bin/env python
#_*_ coding:utf-8 _*_
'''
@auther: tanglei
@contact: tanglei_0315@163.com
@file: file_format.py
@time: 2019/4/25 11:20
'''
import os
import json
import codecs

from common.logger import logger

#去除BOM_UTF8编码的\xef\xbb\xbf
def DeleteBOM_UTF8(file_name):
    file_temp = []
    f = open(file_name,'r')
    s = f.read()
    u = s.decode("utf-8-sig")
    data = u.encode("utf-8")
    fw = open(file_name,'w')
    fw.truncate()
    fw.write(data)
    fw.close()
    f.close()

#彻底解决UTF-8的BOM问题

class file_format(object):
    #定义json文件路径和企业名称
    def __init__(self,file_path,business_name):
        self.file_path = file_path
        self.business_name = business_name

    #将所有json文件中的内容全部整合到一个列表中
    def json_file_extract(self):
        file_sum_list = []
        for root, dirs, files in os.walk(self.file_path):
            for item in files:
                if "json" in item:
                    file_item = self.file_path + '\\' + item
                    with open(file_item,'r',10,'utf-8') as f:
                        file_all = f.read()
                        file_all_dict = json.loads(file_all)
                        detail_list = file_all_dict["branchReport"]
                        for item in detail_list:
                            file_sum_list.append(item)
        return file_sum_list

    #将会议名称为临时会议进行替换，只剩下会议号码
    def remove_lshy(self):
        file_all = self.json_file_extract()
        for item in range(len(file_all)):
            file_all_name = file_all[item]["name"]
            if "临时会议" in file_all_name:
                file_all[item]["name"] = str(file_all_name).strip("临时会议").strip("(").strip(")")

        return file_all

    #将会议名称和excel进行匹配，将匹配上的会议名称修改为会议号
    def Name_to_Number(self,json_info,excel_info):
        for i in json_info:
            name = i["name"]
            for j in excel_info:
                for k,v in j.items():
                    if name == k:
                        i["name"] = v
        return json_info

    #返回重复的会议号列表
    def response_repeat_number(self,number_list):
        repeat_list = []
        b = set(number_list)
        for each_b in b:
            count = 0
            for each_a in number_list:
                if each_b == each_a:
                    count += 1
                    if count > 1:
                        repeat = True
                        repeat_list.append(each_b)
                    else:
                        repeat = False
        return (repeat,repeat_list)

    #将匹配后的数据修改成接口规范的json格式
    def api_json_format(self,source_data,isgzip):

        source_data_len = len(source_data)
        data_list = []
        for item in range(source_data_len):
            name = source_data[item]["name"]
            starttime = source_data[item]["begTS"]
            endtime = source_data[item]["endTS"]
            data_dict = {"mid": name, "nubes": "", "time": [{"startTime": starttime, "endTime": endtime}]}
            data_list.append(data_dict)

        '''
        source_data_len = len(source_data)
        name_temp_list = []
        for item in range(source_data_len):
            name = source_data[item]["name"]
            name_temp_list.append(name)
        is_repeat = self.response_repeat_number(name_temp_list)[0]
        repeat_name_list = self.response_repeat_number(name_temp_list)[1]
        #将会议号一致开会时间不一致的数据进行整理
        time_list = []
        repeat_meeting_list = []
        print(source_data)
        if is_repeat == True:
            for i in repeat_name_list:
                for j in range(source_data_len):
                    name = source_data[j]["name"]
                    if i == name:
                        repeat_time_dict = {"startTime": source_data[j]["begTS"], "endTime": source_data[j]["endTS"]}
                time_list.append(repeat_time_dict)
                repeat_meeting_dict = {"mid": name, "nubes": "", "time": time_list}
                repeat_meeting_list.append(repeat_meeting_dict)
            #print(repeat_meeting_list)
        else:
            print("False")
        '''
        '''
        if is_repeat == True:
            repeat_name_list = self.response_repeat_number(name_temp_list)[1]
        else:
            print("no")
        #print(repeat_name_list)
        '''
        '''
        for i in range(source_data_len):
            for j in repeat_name_list:
                name = source_data[i]["name"]
                starttime = source_data[i]["begTS"]
                endtime = source_data[i]["endTS"]
                print(type(name))
                print(type(j))
        '''
        '''
        #将同会议号不同时间开的会议进行合并
        mid_list = []
        for item in range(len(data_list)):
            mid = int(data_list[item]["mid"])
            mid_list.append(mid)
        repeat_number_list = self.response_repeat_number(mid_list)
        for i in range(len(data_list)):
            mid = int(data_list[i]["mid"])
            for j in repeat_number_list:
                if mid == j:
                    data_list[i]["time"].append(data_list[i+1]["time"][0])
        print(data_list)
        '''

        params = {
            "gzip": isgzip,
            "data": data_list
        }
        #json_params = json.dumps(params)
        #return json_params
        return params
