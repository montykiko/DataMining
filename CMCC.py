#!/usr/bin/env python3
# coding: utf-8
# create on: 2018-06-19
# created for: 浙江联通升级投诉、账期热点、腾讯大王卡月度等基础函数     

#time: 2018-06-27
#modify: 增添更多模块、重命名（参考google开源项目风格指南） 

#time: 2018-07-26
#modify: 梳理整合复用代码,移交给华诚做自动化

import pandas as pd
from pandas import DataFrame, ExcelWriter
from collections import Counter
import jieba, os, re
jieba.load_userdict('D:/CMCC/table/add_dict.txt') 

class DataDealing(object):
    def __init__(self, date, keywordsfile, column):  
        self.date = date
        self.keywordsfile = keywordsfile
        self.column = column
        self.abpath = 'D:/CMCC/data/'
        self.savepath = 'D:/CMCC/result/'

    def PrepareData(self, filepath):
        '''read normal file and deal with 接触编号'''
        df = pd.read_csv(filepath,engine='python',encoding='gbk')
        df['接触编号'] = df['接触编号'].str.replace('\t','')   
        print(df.shape[0])
        return df

    def ReadFile(self):       
        '''prepare origin data of the date'''    
        folderpath = '{}-1/'.format(self.date)
        filename = '{}-1.txt'.format(self.date)
        filepath = os.path.join(self.abpath,folderpath,filename)
        df = pd.read_table(filepath,engine='python',encoding='utf-8')
        df["接触编号"] = df["接触编号"].str.replace('\t','')
        return df
    
    def ConcatData(self, lastday, month, t):
        '''concat data of whole month'''
        concat_lst = []
        frame = pd.DataFrame()
        for i in range(1,lastday + 1):
            day = str(i).zfill(2)
            if t == 'complaints':
                filepath = self.abpath + '2018-{0}-{1}-1/升级投诉.txt'.format(month,day)
            elif t == 'origin':
                filepath = self.abpath + '2018-{0}-{1}-1/2018-{0}-{1}-1.txt'.format(month,day)
            else:
                pass
            # print(filepath)
            df = pd.read_table(filepath,engine='python',encoding='utf-8')
            newcolumns = list(df.columns.values)
            concat_lst.append(df)
        frame = pd.concat(concat_lst,ignore_index=True)
        frame["接触编号"] = frame["接触编号"].str.replace('\t','')
        frame = frame[newcolumns]
        frame.to_csv(self.savepath + 'concat_{0}_2018{1}.csv'.format(t, month),index=False,sep=',',encoding='utf-8')
        print("本次合成{}数据量: ".format(t),len(frame))
        return frame

    def TencentWang(self, df, month):
        '''filter the data of TencentWang'''
        cond1 = df["通话内容"].str.contains("腾讯")
        cond2 = df["通话内容"].str.contains("大王")
        cond = cond1 & cond2
        wang = df.loc[cond]
        wang.to_csv(self.savepath + "腾讯大王卡2018{}.csv".format(month),index=False,sep=',',encoding='utf-8')
        print("本次腾讯大王卡的数据总量为: ",len(wang))
        print("腾讯王卡相关对话占总对话量的: ",len(wang)/len(df))
        return wang 

    def SplitRole(self, df): 
        '''split role of speakers and select, defaults customer'''            
        with open('result.txt','w',encoding='utf-8') as f:
            for i in range(len(df)):
                contents = df["通话内容"].iloc[i]
                c_id = df["接触编号"].iloc[i]
                c_lst = re.split('【|】',contents)
                c_lst.remove('')
                for role, sentence in zip(c_lst[0::2],c_lst[1::2]):
                    s = '\t'.join([c_id, role, sentence]) + '\n'
                    f.write(s)
        tomerge = pd.read_table('result.txt',names=["接触编号",'角色',"内容"])
        split = df.merge(tomerge,on="接触编号",how='right')
        os.remove('result.txt')
        result = split.query('角色 == "客户"')
        result = result[["接触编号","内容"]].reset_index()
        return result

    def JiebaCut(self,df):
        '''jieba cut sentences''' 
        df['key'] = range(len(df))
        with open('result.txt','w',encoding='utf-8') as f:
            f.write('key' + '\t' + "分词" + '\n')
            for i,sentence in enumerate(df["内容"]):
                cut = jieba.cut(sentence)
                f.write(str(i) + '\t' + '/'.join(cut) + '\n')
        cutlst = pd.read_table('result.txt',engine='python',encoding='utf-8')
        result = df.merge(cutlst,on='key',how='left')
        os.remove('result.txt')
        return result
    
    def FetchPattern(self):
        '''fetch keywords and create regex pattern'''
        with open(self.keywordsfile,'r',encoding='utf-8') as f:
            lst = []
            for word in f.readlines():
                lst.append(word.strip())
        pattern = r'|'.join(lst)    
        return pattern
    
    def MatchKeywords(self,df,data):  
        '''add match keywords examples'''
        pattern = self.FetchPattern()
        matchdata = data.loc[data["分词"].str.contains(pattern)]
        matchdata = matchdata.reset_index()
        matchdata[self.column] = matchdata["分词"].str.findall(pattern)
        matchdata = matchdata[["接触编号",self.column]]
        g = matchdata.groupby("接触编号").sum()
        group = pd.DataFrame(g)
        group = group.reset_index()
        group[self.column] = group[self.column].map(lambda x:list(set(x)))
        group['keywords'] = group[self.column].map(lambda x:'/'.join(x))
        result = df.merge(group,on="接触编号",how='right')
        return result
    
    def StatKeywords(self,df):
        '''statistic frequency of keywords'''
        wordslst = []
        wordsdct = {}
        for line in df[self.column]:
            wordslst.extend(line)
        c = Counter(wordslst)
        for word in c.keys():
            cond = df['keywords'].str.contains(word)
            wordsdct[word] = df.loc[cond].shape[0]
        data = pd.DataFrame(list(wordsdct.items()),columns=[self.column,"提及通话数"])
        return data
    
    def SaveFile(self,df,filetype):
        '''save files according to type'''
        if filetype == 'frequency':
            df.to_excel(self.savepath + '{}_frequency_{}.xlsx'.format(self.column,self.date),index=False,encoding='gbk')
        elif filetype == 'result':
            df["主叫"] = df["主叫"].astype('str') + '\t'
            df["被叫"] = df["被叫"].astype('str') + '\t'
            df["受理时间"] = df["受理时间"].astype('str') + '\t'
            df.drop(['complaints'],axis=1,inplace = True)
            df.to_excel(self.savepath + '{}_result_{}.xlsx'.format(self.column,self.date),index=False,encoding='gbk')
        else:
            pass
    
    def LabelCity(self, df):
        '''deal with the city column'''
        cond = df["地市"].isin(["杭州市","宁波市","温州市","绍兴市","湖州市","嘉兴市","金华市","衢州市","舟山市","丽水市","台州市"])
        df.loc[~cond,"地市"] = "其他"
        return df
    
    def LabelComplaints(self, df, c):
        '''label 1 if complaints, else 0'''
        c_num = c["接触编号"].tolist()
        cond = df["接触编号"].isin(c_num)
        df.loc[cond,"是否投诉"] = 1
        df.loc[~cond,"是否投诉"] = 0
        print("腾讯王卡中有升级投诉倾向的: ",df["是否投诉"].sum())
        return df

    def TencentWangStat(self, df):
        '''basic statistic of TencentWang'''
        writer = pd.ExcelWriter(self.savepath + "腾讯王卡总体情况.xlsx")
        as_time = df.groupby("日").agg({'接触编号':'count','是否投诉':'sum'},as_index=False).reset_index()
        as_city = df.groupby('地市').agg({'接触编号':'count','是否投诉':'sum'},as_index=False).reset_index()
        as_time.to_excel(writer,sheet_name='按时间',index=False,encoding='gbk')
        as_city.to_excel(writer,sheet_name='按地市',index=False,encoding='gbk')
        writer.save()

    def HuaChengResult(self, df):
        '''read huacheng result and check the amount'''
        hc = pd.read_table(self.savepath + 'result_fl_id.txt',engine='python',encoding='utf-8',
                            names = ["接触编号","内容","结果"])
        print("处理后数据数目: ",hc.shape[0])
        hc["维度处理"] = hc["结果"].apply(lambda x:self.FetchDimension(x)).apply(lambda x:list(set(x)))
        hc["维度"] = hc["维度处理"].apply(lambda x:'/'.join(x))
        new_df = hc.merge(df,on="接触编号",how='left').drop(["内容","结果"],axis=1)
        return new_df


    def FetchDimension(self,x):
        lst = []
        for i in eval(x):
            lst.append(i[1])
        return lst

    def ClassifyDimens(self, df, days):
        classify = pd.read_excel('D:/CMCC/table/TencentWang.xlsx')
        threes = classify['classThree'].tolist()
        twos = set(classify['classTwo'].tolist())
        dct = {}
        frame = pd.DataFrame()
        concat_lst = []

        for dimen in threes:
            dimen_df = df.loc[df["维度"].str.contains(dimen)]
            dimen_df["classThree"] = dimen
            dct[dimen] = [len(dimen_df),dimen_df["是否投诉"].sum()]
            concat_lst.append(dimen_df)
        frame = pd.concat(concat_lst)
        n = frame.merge(classify,on='classThree',how='left')
        n.drop('classThree',axis=1,inplace=True)

        writer1 = pd.ExcelWriter(self.savepath + "维度按时间.xlsx")
        writer2 = pd.ExcelWriter(self.savepath + "维度按地市.xlsx")
        for two in twos:  
            f = n.loc[n['classTwo']==two]
            dimen_time = f.groupby("日").agg({'接触编号':'count','是否投诉':'sum'},as_index=False).reset_index()
            dimen_city = f.groupby('地市').agg({'接触编号':'count','是否投诉':'sum'},as_index=False).reset_index()
            dimen_city.sort_values(by='接触编号',ascending=False,inplace=True)

            dimen_time["总来话量"] = dimen_time["接触编号"].sum()
            dimen_time["日均来话量"] = round(dimen_time["总来话量"]/days,1)
            dimen_time["最高来话量"] = dimen_time["接触编号"].max()
            dimen_time["最高来话量日期"] = dimen_time["日"].loc[dimen_time["接触编号"] == dimen_time["接触编号"].max()]
            dimen_time["升级投诉总量"] = dimen_time["是否投诉"].sum()

            dimen_time.to_excel(writer1,sheet_name='%s'%two,index=False,encoding='gbk')
            dimen_city.to_excel(writer2,sheet_name='%s'%two,index=False,encoding='gbk')
        writer1.save()
        writer2.save()
        return dct

    def RelatedCate(self, dct):
        classify = pd.read_excel('D:/CMCC/table/TencentWang.xlsx')
        dimen_frame = pd.DataFrame.from_dict(dct,orient='index').reset_index()
        dimen_frame.columns=['咨询内容','咨询次数','升级投诉量']
        result = classify.merge(dimen_frame,left_on='classThree',right_on='咨询内容',how='right')
        g = result.groupby('classTwo').sum()["咨询次数"]
        a = pd.DataFrame(g)
        a = a.reset_index()
        a.columns = ['classTwo','总咨询']
        result = result.merge(a,on='classTwo',how='left')
        result['占比'] = round(result['咨询次数']/result['总咨询'],2)
        result.to_excel(self.savepath+'维度基本情况.xlsx',index=False,encoding='gbk')






     






