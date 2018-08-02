#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#created for: 服务规范、尾语质检月度结果

#time: 2018-06-25
#modify: 添加“百倍用心十分满意”

#time: 2018-07-23
#modify: 发现语音转文字的情况，句号比例突然减少，逗号分隔增加，尾语取得内容变多，使得程序运行变慢，由[-3:]改成取[-2:]


import pandas as pd
from pandas import DataFrame,ExcelWriter
import numpy as np
import os,re

def prepare_csv(file_path,file):    
    '''编码转换并处理制表符问题'''    
    df = pd.read_csv(file_path + file,engine='python',encoding='gbk')
    date = str(df['日'][0])
    df['接触编号'] = df['接触编号'].str.replace('\t','')
    quant = df.shape[0]
    print(quant)
    if quant <= 20000:
        print("{} 数据量少了，需要check一下！".format(date))
    return df,date


def role_split(file_path,df):    
    '''切分说话人角色'''    
    with open('result.txt','w',encoding='utf-8') as f:
        for i in range(len(df)):
            b_string = df['通话内容'][i]
            b_num = df['接触编号'][i]
            b_lst = re.split('【|】',b_string)
            b_lst.remove('')
            for tp,sent in zip(b_lst[0::2],b_lst[1::2]):
                s = '\t'.join([b_num,tp,sent]) + '\n'
                f.write(s)
    data = pd.read_table('result.txt',
                         names=['接触编号','type','内容'])
    r = pd.merge(df,data,on='接触编号',how='right')
    os.remove('result.txt')
    return r


def match(df2,df):    
    '''匹配外包公司和服务规范模式'''    
    #获取坐席内容的最后几句
    df3 = df2.loc[df2['type'] == '坐席' ] 
    df3.reset_index(drop=True,inplace=True)
    df4 = pd.DataFrame(df3.groupby('接触编号')['内容'].sum())
    df4.reset_index(inplace=True)
    df4['最后几句'] = df4['内容'].str.split('。|？').str[-2:]
    df4['最后几句'] = df4['最后几句'].apply(lambda x:''.join(x))
    df4.columns=['接触编号','坐席通话','最后几句']
    df5 = df.merge(df4,on='接触编号',how='left')
    df5['最后几句'].fillna('无',inplace=True)

    #外包公司匹配
    df5['坐席'] = df5['坐席'].astype(str)
    cond1 = df5['坐席'].str.contains(r"5[234]\d{2}")
    df5.loc[cond1,'外包'] = '嘉音讯一中心'
    cond2= df5['坐席'].str.contains(r"53[89]\d|5379|2\d{3}")
    df5.loc[cond2,'外包'] = '嘉音讯二中心'
    cond3 = df5['坐席'].str.contains(r"9\d{3}")
    df5.loc[cond3,'外包'] = '金华博升拓'
    cond4 = df5['坐席'].str.contains(r"5[678]\d{2}")
    df5.loc[cond4,'外包'] = '重庆博升拓'
    df5['外包'].fillna('杭州博升拓',inplace=True)

    #服务规范用语正则匹配
    pattern1 = r'按，?[1一以]|[钱前]，?[以一]|按个一|按基站|接起来一'
    pattern2 = r'[星线信性]号|信号[键减]'
    pattern3 = r'[把吧百白摆败办改边拜版的].*?[眉倍布不备味分为北度得费变拜成般的带本再这病].*?[用有中更游续炫铃].*?[铃心身先些声需欣新信幸七一戏西约].*[十士什][分丰么]满[意一音]'
    
    cond1 = df5['最后几句'].str.contains(pattern1)
    df5.loc[cond1,'按1'] = 1
    df5.loc[~cond1,'按1'] = 0
    
    cond2 = df5['最后几句'].str.contains(pattern2)
    df5.loc[cond2,'按*'] =1
    df5.loc[~cond2,'按*'] = 0
    
    cond3 = df5['最后几句'].str.contains(pattern3)
    df5.loc[cond3,'百倍用心十分满意'] = 1
    df5.loc[~cond3,'百倍用心十分满意'] = 0
    
    df5['匹配'] = df5['按1'] + df5['按*'] + df5['百倍用心十分满意']
    df5['都说到'] = np.where(df5['匹配']==3,1,0)
    df5['都没说到'] = np.where(df5['匹配']==0,1,0)
    return df5


def statis(data,date,to_path):
    '''按联通需求的总量统计内容'''
    new_df = pd.DataFrame(data.groupby('外包').agg({'接触编号':'size',
                                                  '都说到':['sum','mean'],
                                                  '按1':'sum',
                                                  '按*':'sum',
                                                  '百倍用心十分满意':'sum',
                                                  '都没说到':'sum'}))
    new_df['不规范率'] = 1- new_df['都说到','mean']
    new_df.columns=['总量','规范量','规范率','按1',\
                    '按*','百倍用心十分满意','都没说到','不规范率']

    bo = new_df.loc['杭州博升拓':'金华博升拓']
    dct = {'总量':bo['总量'].sum(),
    '规范量':bo['规范量'].sum(),
    '规范率':bo['规范率'].mean(),
    '按1':bo['按1'].sum(),
    '按*':bo['按*'].sum(),
    '百倍用心十分满意':bo['百倍用心十分满意'].sum(),       
    '都没说到':bo['都没说到'].sum(),
    '不规范率':bo['不规范率'].mean()
    }
    new_bo = pd.DataFrame.from_dict(dct,orient='index')
    new_bo.columns=['博升拓']
    new_bo = new_bo.T
    statis = new_df.append(new_bo)   

    all_dct = {'总量':new_df['总量'].sum(),
    '规范量':new_df['规范量'].sum(),
    '规范率':new_df['规范率'].mean(),
    '按1':new_df['按1'].sum(),
    '按*':new_df['按*'].sum(),
    '百倍用心十分满意':new_df['百倍用心十分满意'].sum(),
    '都没说到':new_df['都没说到'].sum(),
    '不规范率':new_df['不规范率'].mean()
    }
    new_all= pd.DataFrame.from_dict(all_dct,orient='index')
    new_all.columns=['总计']
    new_all = new_all.T
    statis = statis.append(new_all)

    statis['规范率'] = (statis['规范率'] * 100).apply(lambda x:round(x,1)).astype('str') + '%'
    statis['不规范率'] = (statis['不规范率'] * 100).apply(lambda x:round(x,1)).astype('str') + '%'
    statis.to_excel(to_path + './总统计量_{}.xlsx'.format(date),encoding='gbk')


def center_statis(data,center):    
    '''分中心统计函数'''    
    dat = data.loc[data['外包']==center]
    datt = dat.groupby('坐席').agg({'接触编号':'size',
                          '都说到':['sum','mean'],
                          '按*':'sum',
                          '按1':'sum',
                          '百倍用心十分满意':'sum',
                          '都没说到':'sum'})
    datt.columns=['总量','规范量','规范率','按*','按1','百倍用心十分满意','都没说到']
    datt['不规范率'] = 1 - datt['规范率']
    bad = datt.sort_values(['不规范率','总量'],ascending=False)
    bad['规范率'] = (bad['规范率'] * 100).apply(lambda x:round(x,1)).astype('str') + '%'
    bad['不规范率'] = (bad['不规范率'] * 100).apply(lambda x:round(x,1)).astype('str') + '%'
#     print(center,'总客服数： ',len(dat['坐席'].unique()))
#     print(center,'总通话数： ',len(dat))
#     print(center,'平均客服接待数：',round(len(dat)/len(dat['坐席'].unique()),1))
#     print(center,'规范率最高的客服坐席号： ',bad.index[0])
#     print('*************************************************************************')
    return bad


def save_center_results(data,date):    
    '''分中心结果存储函数'''    
    writer = pd.ExcelWriter(file_path + '分外包结果{}.xlsx'.format(date))
    lst = ['嘉音讯二中心','嘉音讯一中心','杭州博升拓','重庆博升拓','金华博升拓']
    for center in lst:
        bad = center_statis(data,center)
        bad.to_excel(writer,sheet_name='{}'.format(center),encoding='gbk')
    writer.save()
    
def fetch_batch_statis(file_path, to_path):
    '''批量获取总统计excel文件'''
    for file in os.listdir(file_path):
        print(file)
        df,date = prepare_csv(file_path,file)
        r = role_split(file_path,df)
        data = match(r,df)
        statis(data,date,to_path)
        
def result_monthly(to_path):
    '''获取总统计量的月度结果'''
    lst = []
    frame = pd.DataFrame()
    for file in os.listdir(to_path):
        name = file.split('.')[0]
        date = name.split('_')[1]
        df = pd.read_excel(to_path + file, encoding='gbk')
        df = df.reset_index()
        df.rename(columns={'index':'分中心'},inplace=True)
        df['date'] = date
        lst.append(df)
    frame = pd.concat(lst,ignore_index=True)

    writer = pd.ExcelWriter(to_path + r'尾语质检月份统计.xlsx')
    centers = set(frame['分中心'])
    for center in centers:
        cond = frame['分中心'] == center
        data = frame.loc[cond]
        data.to_excel(writer,sheet_name='{}'.format(center),index=False,encoding='gbk')
    writer.save()
    
    
file_path = 'D:/CMCC/ServiceTermCheck/'
to_path = r'C:/Users/xueji/Desktop/尾语质检/'
fetch_batch_statis(file_path, to_path)
result_monthly(to_path)