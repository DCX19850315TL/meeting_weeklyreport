#!/usr/bin/env python
#_*_ coding:utf-8 _*_
'''
@auther: tanglei
@contact: tanglei_0315@163.com
@file: api.py
@time: 2019/4/26 9:41
'''
import requests
import urllib.request
import urllib.parse
from urllib.error import URLError
from urllib.error import HTTPError
from urllib.error import ContentTooShortError
import json
from retrying import retry

from common.logger import logger

#用户中心的接口
usercenter_api = "http://103.25.23.99/EnterpriseUserCenter/eucService"
headers = {"Content-type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest"}

class GetUserInfo(object):

    def GetUserInfoApi(self,url,params,header):
        UserParams = {"service":"searchAccount","params":{"nubeNumbers":params}}
        UserStr = urllib.parse.urlencode(UserParams)
        Url = url + "?" + UserStr
        request = urllib.request.Request(url=Url,headers=header)
        try:
            response = urllib.request.urlopen(request,timeout=1)
        except URLError as e:
            print(e.reason)
        else:
            response_result = response.read().decode('utf-8')
            response_dict = json.loads(response_result)
            return response_dict

#user_api = GetUserInfo()
#user_api.GetUserInfoApi(url=usercenter_api,params=["69900307"],header=headers)

class send_api(object):
    #调用API接口，获取返回值
    def Post_Data_Api(self,url,params,headers):
        r = requests.post(url=url,data=params,headers=headers)
        return r.json()

    #求会议号列表
    def Meeting_List(self,Meeting_Number):
        Meeting_Count_list = []
        Meeting_Count_list.append()

    #求空音包率
    def Sound_Package_Percent(self,eBadNum,eAllNum):
        if eAllNum != 0:
            Percent = round(eBadNum / eAllNum * 100,2)
        else:
            Percent = 0
        return Percent

    #求是否合格
    def Good_PtoP(self,Sound_Package_Number,Sound_Package_Percent,Loss_Package_Number):
        if Sound_Package_Number > 10 and Sound_Package_Percent > 5.0 or Loss_Package_Number >= 3:
            is_Good = 0
        else:
            is_Good = 1
        return is_Good

    #求端到端的总数
    def PtoP_Count(self,Number_List):
        PtoP_Number = len(Number_List)
        return PtoP_Number

    #拆分起始时间和结束时间
    def Time_Split(self,TimeData):
        TimeDataList = TimeData.split("->")
        StartTime = TimeDataList[0]
        EndTime = TimeDataList[1]
        return (StartTime,EndTime)

    #将会议号转换成会议名称
    def Number_to_Meeting(self,response_meeting_number,excel_number_name):
        for i in excel_number_name:
            for k,v in i.items():
                if int(response_meeting_number) == v:
                    meeting_name = k
                    return meeting_name
                else:
                    meeting_name = "临时会议" + "(" + response_meeting_number + ")"
                    return meeting_name

    #提取会议号中的参会终端视频号和个数
    def Get_Meeting_Number(self,number_list):
        formatList = list(set(number_list))
        formatList.sort(key=number_list.index)
        formatList_len = len(formatList)
        return (formatList,formatList_len)


    #视频号和用户中心的名称进行匹配
    def number_and_usercenter(self,number_list):

        GetUserInfo_Api = GetUserInfo()
        print("开始调用用户中心接口")
        GetUserInfoResult = GetUserInfo_Api.GetUserInfoApi(url=usercenter_api, params=number_list,
                                                           header=headers)
        number_usercenter_list = []
        for i in number_list:
            for j in range(len(GetUserInfoResult["users"])):
                UserInfoNumber = GetUserInfoResult["users"][j]["nubeNumber"]
                if "nickName" in GetUserInfoResult["users"][j].keys():
                    nickName = GetUserInfoResult["users"][j]["nickName"]
                else:
                    nickName = "未命名"
                if i == UserInfoNumber:
                    usercenter_number = "%s_%s" % (i,nickName)
                    number_usercenter_list.append(usercenter_number)
        print("用户中心接口调用完毕,视频号和匿名匹配完毕")
        return number_usercenter_list

    #根据响应的内容进行数据的这整理和端到端总体合格率的计算
    def Analyze_Response(self,response_data,excel_data=None):
        data_dict = response_data
        is_Good_Count = 0
        all_number_list = []
        result_list = []
        unqualified_list = []
        #判断响应状态是否正常
        if data_dict["state"]["resultCode"] == 0:
            #k为会议号
            for k,v in data_dict["result"].items():
                print("开始匹配会议名称")
                if excel_data == None:
                    MeetingName = "临时会议" + "(" + k + ")"
                else:
                    #视频号转成会议名称
                    MeetingName = self.Number_to_Meeting(k,excel_data)
                #kk为时间段
                for kk,vv in v.items():
                    c2c_dict = vv["c2c"]
                    if c2c_dict != {}:
                        #获取端到端总数个数
                        ptop_count = self.PtoP_Count(list(vv["c2c"].keys()))
                        print("开始匹配会议的起始时间和结束时间")
                        #获取起始时间和结束时间
                        start_time = self.Time_Split(kk)[0]
                        end_time = self.Time_Split(kk)[1]
                        #kkk为端到端的视频号11111111->22222222,vvv为丢包率的详细信息
                        for kkk,vvv in vv["c2c"].items():
                            #将每个时间段内的视频号添加到一个列表中
                            for item in kkk.split("->"):
                                all_number_list.append(item)
                            #获取会议内终端视频号和视频号个数
                            meeting_number_list = self.Get_Meeting_Number(all_number_list)[0]
                            print("开始匹配会议的参会人数")
                            meeting_number_count = self.Get_Meeting_Number(all_number_list)[1]
                            #空音包丢包率
                            Sound_Package_Percent = self.Sound_Package_Percent(vvv["eBadNum"],vvv["eAllNum"])
                            #判断端到端合格个数
                            is_Good = self.Good_PtoP(vvv["eBadNum"],Sound_Package_Percent,vvv["lostBadNum"])
                            if is_Good == 1:
                                is_Good_Count+=1
                            else:
                                print("将不合格的端到端添加到列表")
                                unqualified_list.append(kkk)
                        print("开始求端到端总体合格率")
                        #求端到端总体合格率
                        PtoP_Count_Percent = str(round(is_Good_Count / ptop_count * 100,2)) + "%"
                        print("开始匹配视频号对应的昵称")
                        # 将视频号和用户中心的昵称进行匹配，匹配结果为"视频号_别名"
                        meeting_number_end_list = self.number_and_usercenter(meeting_number_list)
                        result_dict = {
                            "Meeting_Number": k,
                            "Meeting_Name": MeetingName,
                            "Start_Time":start_time,
                            "End_Time":end_time,
                            "Number_Count":meeting_number_count,
                            "Percent":PtoP_Count_Percent,
                            "Number_List":meeting_number_end_list,
                            "Unqualified_List":unqualified_list
                        }
                        result_list.append(result_dict)
                        all_number_list = []
                        is_Good_Count = 0
                        unqualified_list = []
                    else:
                        result_list = [{
                            "Meeting_Number": k,
                            "Meeting_Name": MeetingName,
                            "Start_Time": self.Time_Split(kk)[0],
                            "End_Time": self.Time_Split(kk)[1],
                            "Number_Count": 0,
                            "Percent": "",
                            "Number_List": "",
                            "Unqualified_List": ""
                        }]
                return result_list

        else:
            raise Exception("接口请求响应有问题",)