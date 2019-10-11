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
import configparser
import os

from common.logger import logger

#获取配置文件中的值
#setting_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))),"conf\setting.ini")
setting_path = os.path.join(os.path.abspath('conf'),'setting.ini')
conf = configparser.ConfigParser()
conf.read(setting_path,encoding="utf-8")
usercenter_api = conf.get("api_analyze","usercenter_api")
headers = {"Content-type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest"}
confreport_api = conf.get("api_analyze","confReport_api")
loss_time = int(conf.get("api_analyze","loss_time"))
delay_percent = float(conf.get("api_analyze","delay_percent"))
cpu_percent = float(conf.get("api_analyze","cpu_percent"))
ErrorCode = {
            1:"终端上行网络丟包、抖动",
            2:"终端上行网络丟包",
            3:"终端上行网络抖动",
            11:"终端下行网络丟包、抖动",
            22:"终端下行网络丟包",
            33:"终端下行网络抖动",
            4:"终端CPU过载"
        }

class GetUserInfo(object):

    @retry(stop_max_attempt_number=3,wait_fixed=2000)
    def GetUserInfoApi(self,url,params,header):
        try:
            UserParams = {"service": "searchAccount", "params": {"nubeNumbers": params}}
            UserStr = urllib.parse.urlencode(UserParams)
            Url = url + "?" + UserStr
            request = urllib.request.Request(url=Url, headers=header)
            response = urllib.request.urlopen(request, timeout=60)
        except Exception:
            print("重新调用用户中心的接口")
            logger().error("重新调用用户中心的接口")
            raise Exception(10040)
        else:
            response_result = response.read().decode('utf-8')
            response_dict = json.loads(response_result)
            return response_dict

class send_api(object):
    #调用API接口，获取返回值
    def Post_Data_Api(self,url,params,headers):
        try:
            r = requests.post(url=url,data=params,headers=headers)
        except requests.exceptions.ConnectionError as e:
            if "10054" in str(e.args[0]):
                raise Exception(10054)
            elif "10061" in str(e.args[0]):
                raise Exception(10061)
        else:
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
        try:
            GetUserInfo_Api = GetUserInfo()
            print("开始调用用户中心接口")
            logger().info("开始调用用户中心接口")
            GetUserInfoResult = GetUserInfo_Api.GetUserInfoApi(url=usercenter_api, params=number_list,
                                                               header=headers)
        except Exception as e:
            if e.args[0] == 10040:
                return 10041
        else:
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
            print("用户中心接口调用完毕,视频号和昵称匹配完毕")
            logger().info("用户中心接口调用完毕,视频号和昵称匹配完毕")
            return number_usercenter_list

    #根据响应的内容进行数据的整理和端到端总体合格率的计算
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
                logger().info("开始匹配会议名称")
                if excel_data == None:
                    MeetingName = "临时会议" + "(" + k + ")"
                else:
                    #视频号转成会议名称
                    MeetingName = self.Number_to_Meeting(k,excel_data)
                #kk为时间段
                for kk,vv in v.items():
                    if vv:
                        c2c_dict = vv["c2c"]
                        if c2c_dict != {}:
                            #获取端到端总数个数
                            ptop_count = self.PtoP_Count(list(vv["c2c"].keys()))
                            print("开始匹配会议的起始时间和结束时间")
                            logger().info("开始匹配会议的起始时间和结束时间")
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
                                logger().info("开始匹配会议的参会人数")
                                meeting_number_count = self.Get_Meeting_Number(all_number_list)[1]
                                #空音包丢包率
                                Sound_Package_Percent = self.Sound_Package_Percent(vvv["eBadNum"],vvv["eAllNum"])
                                #判断端到端合格个数
                                is_Good = self.Good_PtoP(vvv["eBadNum"],Sound_Package_Percent,vvv["lostBadNum"])
                                if is_Good == 1:
                                    is_Good_Count+=1
                                else:
                                    print("将不合格的端到端添加到列表")
                                    logger().info("将不合格的端到端添加到列表")
                                    unqualified_list.append(kkk)
                            print("开始求端到端总体合格率")
                            logger().info("开始求端到端总体合格率")
                            #求端到端总体合格率
                            PtoP_Count_Percent = str(round(is_Good_Count / ptop_count * 100,2)) + "%"
                            print("开始匹配视频号对应的昵称")
                            logger().info("开始匹配视频号对应的昵称")
                            # 将视频号和用户中心的昵称进行匹配，匹配结果为"视频号_别名"
                            meeting_number_end_list = self.number_and_usercenter(meeting_number_list)
                            if meeting_number_end_list != 10041:
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
                                result_list = {
                                    "Meeting_Number": k,
                                    "Meeting_Name": MeetingName,
                                    "Start_Time": start_time,
                                    "End_Time": end_time,
                                    "Number_Count": 10041
                                }
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
                    else:
                        start_time = self.Time_Split(kk)[0]
                        end_time = self.Time_Split(kk)[1]
                        result_list = {
                            "Meeting_Number": k,
                            "Meeting_Name": MeetingName,
                            "Start_Time": start_time,
                            "End_Time": end_time,
                            "Number_Count": 0,
                            "Percent": "",
                            "Number_List": "",
                            "Unqualified_List": ""
                        }
            return result_list
        else:
            raise Exception("接口请求响应有问题",)

class confReport(object):

    #判断Unqualified_List是否为空来获取对应的Meeting_Number，Start_Time和Unqualified_List的数据
    def GetPostData(self,**kwargs):

        Unqualified_List = kwargs["data"]["Unqualified_List"]
        if Unqualified_List == []:
            return "Null"
        else:
            StartTime = kwargs["data"]["Start_Time"].split( )[0]
            return (kwargs["data"]["Meeting_Number"],StartTime,Unqualified_List)

    #调用ConfReportApi获取数据
    def GetConfReportApi(self,MeetingId,TodayTime):

        params = {"meetingId":MeetingId,"TS":TodayTime}
        r = requests.get(url=confreport_api,params=params)
        return r.json()

    #返回重复的会议号列表
    def response_repeat_number(self, number_list):
        if number_list == 0:
            b = 0
        else:
            repeat_list = []
            b = list(set(number_list))
        return (b)

    #返回不合格的视频号_原因列表
    def AnalysisConfReportData(self,*args,**kwargs):

        #传进来的不合格终端的数量69900242->69900241
        list_len = len(args[0])
        #接口调用后的User数据,列表
        UserList = kwargs["data"]["User"]
        #不合格的原因列表
        Unqualified_Reason_List = []
        #总的不合格的原因列表
        Total_Unqualified_Reason_List= []
        #新的不合格的原因列表
        New_Total_Unqualified_Reason_List = []
        #CPU异常计数
        CpuCount = 0
        #网络异常计数
        NetworkCount = 0
        for i in range(list_len):
            list_i = args[0][i].split("->")
            #主叫的视频号
            caller = list_i[0]
            # 被叫的视频号
            called = list_i[1]
            for j in UserList:
                #User列表下的UserId数据
                UserId = j["UserId"]
                #User列表下的ASReport数据
                ASReport = j["ASReport"]
                #判断上行
                if caller == UserId:
                    #求CPU是否异常
                    TotalTime = j["LastTS"] - j["BegTS"]
                    if j["CpuRate80C"] == 0:
                        CpuException = 0.0
                    elif TotalTime == 0:
                        CpuException = 0.0
                    else:
                        CpuException = round(j["CpuRate80C"] * 5 / TotalTime * 100,2)
                    if CpuException > cpu_percent:
                        Unqualified_Reason_List.append("%s_%s" % (caller, ErrorCode[4]))
                    if ASReport == None:
                        continue
                    else:
                        for k in ASReport:
                            if caller == k["SpeakerId"]:
                                UpToRelayLoss = k["LossRateFinalC"] * 5
                                UpToRelayDelayTotal = k["DelayTimeCnf"] + k["DelayTimeEnt"] + k["DelayTimeFim"] + k["DelayTimeErr"]
                                UpToRelayDelayTemp = k["DelayTimeFim"] + k["DelayTimeErr"]
                                if UpToRelayDelayTemp == 0:
                                    UpToRelayDelay = 0.0
                                else:
                                    UpToRelayDelay = round(UpToRelayDelayTemp / UpToRelayDelayTotal * 100,2)
                                # 上行丢包和延迟问题同时存在
                                if UpToRelayLoss >= loss_time and UpToRelayDelay > delay_percent:
                                    Unqualified_Reason_List.append("%s_%s" % (caller,ErrorCode[1]))
                                #上行丢包问题
                                elif UpToRelayLoss >= loss_time:
                                    Unqualified_Reason_List.append("%s_%s" % (caller, ErrorCode[2]))
                                #上行延迟问题
                                elif UpToRelayDelay > delay_percent:
                                    Unqualified_Reason_List.append("%s_%s" % (caller, ErrorCode[3]))
                    #print(Unqualified_Reason_List)
                    for item in Unqualified_Reason_List:
                        CodeNumber1 = item.split("_")[1]
                        if CodeNumber1 == ErrorCode[4]:
                            CpuCount += 1
                        if CodeNumber1 == ErrorCode[1] or CodeNumber1 == ErrorCode[2] or CodeNumber1 == ErrorCode[3]:
                            NetworkCount += 1
                    if NetworkCount > 0 and CpuCount > 0:
                        continue
                    elif NetworkCount > 0:
                        continue
                    else:
                        for item in UserList:
                            if called == item["UserId"]:
                                # 求CPU是否异常
                                TotalTime = item["LastTS"] - item["BegTS"]
                                if item["CpuRate80C"] == 0:
                                    CpuException = 0.0
                                elif TotalTime == 0:
                                    CpuException = 0.0
                                else:
                                    CpuException = round(item["CpuRate80C"] * 5 / TotalTime * 100, 2)
                                if CpuException > cpu_percent:
                                    Unqualified_Reason_List.append("%s_%s" % (called, ErrorCode[4]))
                                if item["ASReport"] == None:
                                    continue
                                else:
                                    for k in item["ASReport"]:
                                        if k["SpeakerId"] == caller:
                                            DownLoss = k["LossRateFinalC"] * 5
                                            DownDelayTotal = k["DelayTimeCnf"] + k["DelayTimeEnt"] + k["DelayTimeFim"] + k["DelayTimeErr"]
                                            DownDelayTemp = k["DelayTimeFim"] + k["DelayTimeErr"]
                                            if DownDelayTemp == 0:
                                                DownDelay = 0.0
                                            else:
                                                DownDelay = round(DownDelayTemp / DownDelayTotal * 100, 2)
                                            if DownLoss >= loss_time and DownDelay > delay_percent:
                                                Unqualified_Reason_List.append("%s_%s" % (called, ErrorCode[11]))
                                            elif DownLoss >= loss_time:
                                                Unqualified_Reason_List.append("%s_%s" % (called, ErrorCode[22]))
                                            elif DownDelay > delay_percent:
                                                Unqualified_Reason_List.append("%s_%s" % (called, ErrorCode[33]))

            for item in Unqualified_Reason_List:
                Total_Unqualified_Reason_List.append(item)
            Unqualified_Reason_List = []
            CpuCount = 0
            NetworkCount = 0

        #排除同一视频号多个重复故障原因
        Loss_Delay = 0
        for item in Total_Unqualified_Reason_List:
            CodeNumber = item.split("_")[1]
            if CodeNumber == ErrorCode[1] or CodeNumber == ErrorCode[2] or CodeNumber == ErrorCode[3]:
                caller = item.split("_")[0]
            elif CodeNumber == ErrorCode[11] or CodeNumber == ErrorCode[22] or CodeNumber == ErrorCode[33]:
                called = item.split("_")[0]
            else:
                caller = item.split("_")[0]
            if CodeNumber == ErrorCode[1]:
                New_Total_Unqualified_Reason_List.append("%s_%s" % (caller,ErrorCode[1]))
            elif CodeNumber == ErrorCode[11]:
                New_Total_Unqualified_Reason_List.append("%s_%s" % (called,ErrorCode[11]))
            elif CodeNumber == ErrorCode[2]:
                for j in Total_Unqualified_Reason_List:
                    VedioNumber_j = j.split("_")[0]
                    CodeNumber_j = j.split("_")[1]
                    if CodeNumber_j == ErrorCode[3] and VedioNumber_j == caller:
                        Loss_Delay += 1
                    elif CodeNumber_j == ErrorCode[1] and VedioNumber_j == caller:
                        Loss_Delay += 1
                if Loss_Delay >= 1:
                    New_Total_Unqualified_Reason_List.append("%s_%s" % (caller, ErrorCode[1]))
                else:
                    New_Total_Unqualified_Reason_List.append(item)
            elif CodeNumber == ErrorCode[3]:
                for k in Total_Unqualified_Reason_List:
                    VedioNumber_k = k.split("_")[0]
                    CodeNumber_k = k.split("_")[1]
                    if CodeNumber_k == ErrorCode[2] and VedioNumber_k == caller:
                        Loss_Delay += 1
                    elif CodeNumber_k == ErrorCode[1] and VedioNumber_k == caller:
                        Loss_Delay += 1
                if Loss_Delay >= 1:
                    New_Total_Unqualified_Reason_List.append("%s_%s" % (caller, ErrorCode[1]))
                else:
                    New_Total_Unqualified_Reason_List.append(item)
            elif CodeNumber == ErrorCode[22]:
                for jj in Total_Unqualified_Reason_List:
                    VedioNumber_jj = jj.split("_")[0]
                    CodeNumber_jj = jj.split("_")[1]
                    if CodeNumber_jj == ErrorCode[33] and VedioNumber_jj == called:
                        Loss_Delay += 1
                    elif CodeNumber_jj == ErrorCode[11] and VedioNumber_jj == called:
                        Loss_Delay += 1
                if Loss_Delay >= 1:
                    New_Total_Unqualified_Reason_List.append("%s_%s" % (called, ErrorCode[11]))
                else:
                    New_Total_Unqualified_Reason_List.append(item)
            elif CodeNumber == ErrorCode[33]:
                for kk in Total_Unqualified_Reason_List:
                    VedioNumber_kk = kk.split("_")[0]
                    CodeNumber_kk = kk.split("_")[1]
                    if CodeNumber_kk == ErrorCode[22] and VedioNumber_kk == called:
                        Loss_Delay += 1
                    elif CodeNumber_kk == ErrorCode[11] and VedioNumber_kk == called:
                        Loss_Delay += 1
                if Loss_Delay >= 1:
                    New_Total_Unqualified_Reason_List.append("%s_%s" % (called, ErrorCode[11]))
                else:
                    New_Total_Unqualified_Reason_List.append(item)
            elif CodeNumber == ErrorCode[4]:
                New_Total_Unqualified_Reason_List.append(item)
            Loss_Delay = 0

        New_Total_Unqualified_Reason_List = self.response_repeat_number(number_list=New_Total_Unqualified_Reason_List)

        return New_Total_Unqualified_Reason_List

    #求不合格视频号的丢包时长累加，最大时延占比和CPU异常时间的数值
    def AnalysisUnqualifiedData(self,UnqualifiedList,ResponseData):

        # 问题最终保存的地方
        err_dict = {}
        #返回的数据列表信息
        UserList = ResponseData["User"]
        # 上行丢包总的时长初始值
        UpLossTotal = 0
        # 下行丢包总的时长初始值
        DownLossTotal = 0
        # 临时上行延迟列表
        TempUpDelayList = []
        # 临时下行延迟列表
        TempDownDelayList = []
        # CPU不合格的初始数值
        CPU_AbnormalTime = 0
        # CPU不合格的列表
        CPU_AbnormalTime_List = []
        # 不合格视频号_丢包时长累加列表
        Loss_TotalTime_List = []
        # 不合格视频号_最大时延占比列表
        Delay_Max_List = []
        # 总的不合格的原因列表
        Total_Unqualified_Reason_List = []
        for item in UnqualifiedList:
            VideoNumber = item.split("_")[0]
            CodeNumber = item.split("_")[1]
            Total_Unqualified_Reason_List.append("%s_%s" % (VideoNumber,CodeNumber))
        for item in UnqualifiedList:
            CodeNumber = item.split("_")[1]
            if  CodeNumber == ErrorCode[1] or CodeNumber == ErrorCode[2] or CodeNumber == ErrorCode[3]:
                caller = item.split("_")[0]
            elif CodeNumber == ErrorCode[11] or CodeNumber == ErrorCode[22] or CodeNumber == ErrorCode[33]:
                called = item.split("_")[0]
            else:
                caller = item.split("_")[0]
            if CodeNumber == ErrorCode[1]:
                for item in UserList:
                    if caller == item["UserId"]:
                        if item["ASReport"] == None:
                            continue
                        else:
                            for jtem in item["ASReport"]:
                                if jtem["SpeakerId"] == caller:
                                    UpLossTotal += jtem["LossRateFinalC"]
                                    TempUpDelayTwo = jtem["DelayTimeFim"] + jtem["DelayTimeErr"]
                                    if TempUpDelayTwo == 0:
                                        TempUpDelay = 0.0
                                    else:
                                        TempUpDelay = round((jtem["DelayTimeFim"] + jtem["DelayTimeErr"]) / (
                                                jtem["DelayTimeCnf"] + jtem["DelayTimeEnt"] + jtem["DelayTimeFim"] + jtem[
                                            "DelayTimeErr"]) * 100, 2)
                                    TempUpDelayList.append(TempUpDelay)
                Loss_TotalTime_List.append("%s_上行网络丢包累加时长%s秒" % (caller, UpLossTotal * 5))
                if TempUpDelayList != []:
                    Delay_Max_List.append("%s_上行网络最大时延占比%s" % (caller, max(TempUpDelayList)) + "%")
            elif CodeNumber == ErrorCode[2]:
                for item in UserList:
                    if caller == item["UserId"]:
                        if item["ASReport"] == None:
                            continue
                        else:
                            for jtem in item["ASReport"]:
                                if jtem["SpeakerId"] == caller:
                                    UpLossTotal += jtem["LossRateFinalC"]
                Loss_TotalTime_List.append("%s_上行网络丢包累加时长%s秒" % (caller, UpLossTotal * 5))
            elif CodeNumber == ErrorCode[3]:
                for item in UserList:
                    if caller == item["UserId"]:
                        if item["ASReport"] == None:
                            continue
                        else:
                            for jtem in item["ASReport"]:
                                if jtem["SpeakerId"] == caller:
                                    TempUpDelayTwo = jtem["DelayTimeFim"] + jtem["DelayTimeErr"]
                                    if TempUpDelayTwo == 0:
                                        TempUpDelay = 0.0
                                    else:
                                        TempUpDelay = round((jtem["DelayTimeFim"] + jtem["DelayTimeErr"]) / (
                                                jtem["DelayTimeCnf"] + jtem["DelayTimeEnt"] + jtem["DelayTimeFim"] + jtem[
                                            "DelayTimeErr"]) * 100, 2)
                                    TempUpDelayList.append(TempUpDelay)
                if TempUpDelayList != []:
                    Delay_Max_List.append("%s_上行网络最大时延占比%s" % (caller, max(TempUpDelayList)) + "%")
            elif CodeNumber == ErrorCode[11]:
                '''
                for item in UserList:
                    if called == item["UserId"]:
                        for jtem in item["ASReport"]:
                            if jtem["SpeakerId"] == caller:
                                DownLossTotal += jtem["LossRateFinalC"]
                                TempDownDelayTwo = jtem["DelayTimeFim"] + jtem["DelayTimeErr"]
                                if TempDownDelayTwo == 0:
                                    TempDownDelay = 0.0
                                else:
                                    TempDownDelay = round((jtem["DelayTimeFim"] + jtem["DelayTimeErr"]) / (
                                            jtem["DelayTimeCnf"] + jtem["DelayTimeEnt"] + jtem["DelayTimeFim"] + jtem[
                                        "DelayTimeErr"]) * 100, 2)
                                TempDownDelayList.append(TempDownDelay)
                Loss_TotalTime_List.append("%s_下行网络丢包累加时长%s秒" % (called, DownLossTotal * 5))
                if TempDownDelayList != []:
                    Delay_Max_List.append("%s_下行网络最大时延占比%s" % (called, max(TempDownDelayList)) + "%")
                '''
                for item in UserList:
                    if called == item["UserId"]:
                        if item["ASReport"] == None:
                            continue
                        else:
                            for jtem in item["ASReport"]:
                                if jtem["SpeakerId"] != called:
                                    DownLossTotal += jtem["LossRateFinalC"]
                                    TempDownDelayTwo = jtem["DelayTimeFim"] + jtem["DelayTimeErr"]
                                    if TempDownDelayTwo == 0:
                                        TempDownDelay = 0.0
                                    else:
                                        TempDownDelay = round((jtem["DelayTimeFim"] + jtem["DelayTimeErr"]) / (
                                                jtem["DelayTimeCnf"] + jtem["DelayTimeEnt"] + jtem["DelayTimeFim"] + jtem[
                                            "DelayTimeErr"]) * 100, 2)
                                    TempDownDelayList.append(TempDownDelay)
                Loss_TotalTime_List.append("%s_下行网络丢包累加时长%s秒" % (called, DownLossTotal * 5))
                if TempDownDelayList != []:
                    Delay_Max_List.append("%s_下行网络最大时延占比%s" % (called, max(TempDownDelayList)) + "%")
            elif CodeNumber == ErrorCode[22]:
                for item in UserList:
                    if called == item["UserId"]:
                        if item["ASReport"] == None:
                            continue
                        else:
                            for jtem in item["ASReport"]:
                                if jtem["SpeakerId"] != called:
                                    DownLossTotal += jtem["LossRateFinalC"]
                Loss_TotalTime_List.append("%s_下行网络丢包累加时长%s秒" % (called, DownLossTotal * 5))
            elif CodeNumber == ErrorCode[33]:
                for item in UserList:
                    if called == item["UserId"]:
                        if item["ASReport"] == None:
                            continue
                        else:
                            for jtem in item["ASReport"]:
                                if jtem["SpeakerId"] != called:
                                    TempDownDelayTwo = jtem["DelayTimeFim"] + jtem["DelayTimeErr"]
                                    if TempDownDelayTwo == 0:
                                        TempDownDelay = 0.0
                                    else:
                                        TempDownDelay = round((jtem["DelayTimeFim"] + jtem["DelayTimeErr"]) / (
                                                jtem["DelayTimeCnf"] + jtem["DelayTimeEnt"] + jtem["DelayTimeFim"] + jtem[
                                            "DelayTimeErr"]) * 100, 2)
                                    TempDownDelayList.append(TempDownDelay)
                if TempDownDelayList != []:
                    Delay_Max_List.append("%s_下行网络最大时延占比%s" % (called, max(TempDownDelayList)) + "%")
            elif CodeNumber == ErrorCode[4]:
                for item in UserList:
                    if caller == item["UserId"]:
                        CPU_AbnormalTime += item["CpuRate80C"]
                CPU_AbnormalTime_List.append("%s_CPU异常时间%s秒" % (caller, CPU_AbnormalTime * 5))

            CPU_AbnormalTime = 0
            UpLossTotal = 0
            DownLossTotal = 0
            TempUpDelayList = []
            TempDownDelayList = []
        print(Total_Unqualified_Reason_List)
        print(Delay_Max_List)
        print(Loss_TotalTime_List)
        print(CPU_AbnormalTime_List)
        err_dict = {"Unqualified_Reason":Total_Unqualified_Reason_List,"Loss_TotalTime":Loss_TotalTime_List,"Delay_Max":Delay_Max_List,"CPU_AbnormalTime":CPU_AbnormalTime_List}
        print(err_dict)
        return err_dict

"""
        if Delay_Max_List != []:
            Delay_Max_Result= Delay_Max_List
        else:
            Delay_Max_Result = []

        if Loss_TotalTime_List != []:
            DownLossTotal_Result = Loss_TotalTime_List
        else:
            DownLossTotal_Result = []

        if Total_CPU_AbnormalTime_List != []:
            CPU_AbnormalTime_Result = Total_CPU_AbnormalTime_List
        else:
            CPU_AbnormalTime_Result = []

        #print(Unqualified_Reason_List)
        err_dict = {"Unqualified_Reason":self.response_repeat_number(number_list=Total_Unqualified_Reason_List),"Loss_TotalTime":self.response_repeat_number(number_list=DownLossTotal_Result),"Delay_Max":self.response_repeat_number(number_list=Delay_Max_Result),"CPU_AbnormalTime":self.response_repeat_number(number_list=CPU_AbnormalTime_Result)}
        print(err_dict)
"""







