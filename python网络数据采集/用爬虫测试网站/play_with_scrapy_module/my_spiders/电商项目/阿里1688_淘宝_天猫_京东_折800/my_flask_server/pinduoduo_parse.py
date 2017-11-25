# coding:utf-8

'''
@author = super_fazai
@File    : pinduoduo_parse.py
@Time    : 2017/11/24 14:58
@connect : superonesfazai@gmail.com
'''

"""
拼多多页面采集系统(官网地址: http://mobile.yangkeduo.com/)
由于拼多多的pc站，官方早已放弃维护，专注做移动端，所以下面的都是基于移动端地址进行的爬取
"""

import time
from random import randint
import json
import requests
import re
from pprint import pprint
from decimal import Decimal
from time import sleep
import datetime
import re
import gc
import pytz

from settings import HEADERS

class PinduoduoParse(object):
    def __init__(self):
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            # 'Accept-Encoding:': 'gzip',
            'Accept-Language': 'zh-CN,zh;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Host': 'mobile.yangkeduo.com',
            'User-Agent': HEADERS[randint(0, 34)]  # 随机一个请求头
        }
        self.result_data = {}

    def get_goods_data(self, goods_id):
        '''
        模拟构造得到data的url
        :param goods_id:
        :return: data   类型dict
        '''
        if goods_id == '':
            return {}
        else:
            tmp_url = 'http://mobile.yangkeduo.com/goods.html?goods_id=' + str(goods_id)
            print('------>>>| 得到的商品手机版地址为: ', tmp_url)

            # 设置代理ip
            self.proxies = self.get_proxy_ip_from_ip_pool()  # {'http': ['xx', 'yy', ...]}
            self.proxy = self.proxies['http'][randint(0, len(self.proxies) - 1)]

            tmp_proxies = {
                'http': self.proxy,
            }
            # print('------>>>| 正在使用代理ip: {} 进行爬取... |<<<------'.format(self.proxy))

            try:
                response = requests.get(tmp_url, headers=self.headers, proxies=tmp_proxies, timeout=10)  # 在requests里面传数据，在构造头时，注意在url外头的&xxx=也得先构造
                body = response.content.decode('utf-8')
                # print(data)

                # 过滤
                body = re.compile(r'\n').sub('', body)
                body = re.compile(r'\t').sub('', body)
                body = re.compile(r'  ').sub('', body)
                data = re.compile(r'window.rawData= (.*?);</script>').findall(body)  # 贪婪匹配匹配所有
                # print(data)
            except Exception:
                print('requests.get()请求超时....')
                print('data为空!')
                return {}

            if data != []:
                data = data[0]
                try:
                    data = json.loads(data)
                except Exception:
                    return {}
                # pprint(data)

                try:
                    data['goods'].pop('localGroups')
                    data['goods'].pop('mallService')
                    data.pop('reviews')             # 评价信息跟相关统计
                except:
                    pass
                # pprint(data)

                '''
                处理detailGallery转换成能被html显示页面信息
                '''
                detail_data = data.get('goods', {}).get('detailGallery', [])
                tmp_div_desc = ''
                if detail_data != []:
                    for index in range(0, len(detail_data)):
                        if index == 0:      # 跳过拼多多的提示
                            pass
                        else:
                            tmp = ''
                            tmp_img_url = detail_data[index].get('url')
                            tmp = r'<img src="{}" style="height:auto;width:100%;"/>'.format(tmp_img_url)
                            tmp_div_desc += tmp

                    detail_data = '<div>' + tmp_div_desc + '</div>'

                else:
                    detail_data = ''
                # print(detail_data)
                try:
                    data['goods'].pop('detailGallery')  # 删除图文介绍的无第二次用途的信息
                except:
                    pass
                data['div_desc'] = detail_data

                # pprint(data)
                self.result_data = data
                return data

            else:
                print('data为空!')
                return {}

    def deal_with_data(self):
        '''
        处理result_data, 返回需要的信息
        :return: 字典类型
        '''
        data = self.result_data
        if data != {}:
            # 店铺名称
            if data.get('mall') is not None:
                shop_name = data.get('mall', {}).get('mallName', '')
            else:
                shop_name = ''

            # 掌柜
            account = ''

            # 商品名称
            title = data.get('goods', {}).get('goodsName', '')

            # 子标题
            sub_title = ''

            # 商品库存
            # 商品标签属性对应的值

            # 商品标签属性名称
            if data.get('goods', {}).get('skus', []) == []:
                detail_name_list = ''
            else:
                detail_name_list = [{'spec_name': item.get('spec_key')} for item in data.get('goods', {}).get('skus', [])[0].get('specs')]
            print(detail_name_list)

            # 要存储的每个标签对应规格的价格及其库存
            skus = data.get('goods', {}).get('skus', [])
            price_info_list = []
            if skus != []:          # 注意: 拼多多商品只有一个规格时skus也不会为空的
                for item in skus:
                    tmp = {}
                    price = item.get('groupPrice', '')          # 拼团价
                    normal_price = item.get('normalPrice', '')  # 单独购买价格
                    spec_value = [item.get('spec_value') for item in data.get('goods', {}).get('skus', [])[0].get('specs')]
                    spec_value = '|'.join(spec_value)
                    img_url = item.get('thumbUrl', '')
                    rest_number = item.get('quantity', 0)  # 剩余库存
                    is_on_sale = item.get('isOnSale', 0)        # 用于判断是否在特价销售，1:特价 0:原价(normal_price)
                    tmp['spec_value'] = spec_value
                    tmp['detail_price'] = price
                    tmp['normal_price'] = normal_price
                    tmp['img_url'] = img_url
                    tmp['rest_number'] = rest_number
                    tmp['is_on_sale'] = is_on_sale
                    price_info_list.append(tmp)

            if price_info_list == []:
                print('price_info_list为空值')
                return {}

            # 商品价格和淘宝价
            tmp_price_list = sorted([round(float(item.get('detail_price', '')), 2) for item in price_info_list])
            price = tmp_price_list[-1]  # 商品价格
            taobao_price = tmp_price_list[0]  # 淘宝价

            # print('最高价为: ', price)
            # print('最低价为: ', taobao_price)
            # print(len(price_info_list))
            # pprint(price_info_list)

            # 所有示例图片地址
            all_img_url = [{'img_url': item} for item in data.get('goods', {}).get('topGallery', [])]
            # print(all_img_url)

            # 详细信息标签名对应属性
            p_info = [{'p_name': '商品描述', 'p_value': data.get('goods', {}).get('goodsDesc', '')}]
            # print(p_info)

            # 总销量
            all_sell_count = data.get('goods', {}).get('sales', 0)

            # div_desc
            div_desc = data.get('div_desc', '')

            # 商品销售时间区间
            schedule = [{
                'begin_time': self.timestamp_to_regulartime(data.get('goods', {}).get('groupTypes', [])[0].get('startTime')),
                'end_time': self.timestamp_to_regulartime(data.get('goods', {}).get('groupTypes', [])[0].get('endTime')),
            }]
            pprint(schedule)

            # 用于判断商品是否已经下架
            is_delete = 0

            result = {
                'shop_name': shop_name,  # 店铺名称
                'account': account,  # 掌柜
                'title': title,  # 商品名称
                'sub_title': sub_title,  # 子标题
                # 'shop_name_url': shop_name_url,            # 店铺主页地址
                'price': price,  # 商品价格
                'taobao_price': taobao_price,  # 淘宝价
                # 'goods_stock': goods_stock,                # 商品库存
                'detail_name_list': detail_name_list,  # 商品标签属性名称
                # 'detail_value_list': detail_value_list,    # 商品标签属性对应的值
                'price_info_list': price_info_list,  # 要存储的每个标签对应规格的价格及其库存
                'all_img_url': all_img_url,  # 所有示例图片地址
                'p_info': p_info,  # 详细信息标签名对应属性
                'div_desc': div_desc,  # div_desc
                'schedule': schedule,  # 商品开卖时间和结束开卖时间
                'is_delete': is_delete  # 用于判断商品是否已经下架
            }
            # pprint(result)
            # print(result)
            # wait_to_send_data = {
            #     'reason': 'success',
            #     'data': result,
            #     'code': 1
            # }
            # json_data = json.dumps(wait_to_send_data, ensure_ascii=False)
            # print(json_data)
            return result

        else:
            print('待处理的data为空的dict, 该商品可能已经转移或者下架')
            # return {
            #     'is_delete': 1,
            # }
            return {}

    def timestamp_to_regulartime(self, timestamp):
        '''
        将时间戳转换成时间
        '''
        # 利用localtime()函数将时间戳转化成localtime的格式
        # 利用strftime()函数重新格式化时间

        # 转换成localtime
        time_local = time.localtime(timestamp)
        # 转换成新的时间格式(2016-05-05 20:28:54)
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)

        return dt

    def get_proxy_ip_from_ip_pool(self):
        '''
        从代理ip池中获取到对应ip
        :return: dict类型 {'http': ['http://183.136.218.253:80', ...]}
        '''
        base_url = 'http://127.0.0.1:8000'
        result = requests.get(base_url).json()

        result_ip_list = {}
        result_ip_list['http'] = []
        for item in result:
            if item[2] > 7:
                tmp_url = 'http://' + str(item[0]) + ':' + str(item[1])
                result_ip_list['http'].append(tmp_url)
            else:
                delete_url = 'http://127.0.0.1:8000/delete?ip='
                delete_info = requests.get(delete_url + item[0])
        # pprint(result_ip_list)
        return result_ip_list

    def get_goods_id_from_url(self, pinduoduo_url):
        '''
        得到goods_id
        :param pinduoduo_url:
        :return: goods_id (类型str)
        '''
        is_pinduoduo_url = re.compile(r'http://mobile.yangkeduo.com/goods.html.*?').findall(pinduoduo_url)
        if is_pinduoduo_url != []:
            if re.compile(r'http://mobile.yangkeduo.com/goods.html\?.*?goods_id=(\d+).*?').findall(pinduoduo_url) != []:
                tmp_pinduoduo_url = re.compile(r'http://mobile.yangkeduo.com/goods.html\?.*?goods_id=(\d+).*?').findall(pinduoduo_url)[0]
                if tmp_pinduoduo_url != '':
                    goods_id = tmp_pinduoduo_url
                else:   # 只是为了在pycharm里面测试，可以不加
                    pinduoduo_url = re.compile(r';').sub('', pinduoduo_url)
                    goods_id = re.compile(r'http://mobile.yangkeduo.com/goods.html\?.*?goods_id=(\d+).*?').findall(pinduoduo_url)[0]
                print('------>>>| 得到的拼多多商品id为:', goods_id)
                return goods_id
            else:
                pass
        else:
            print('拼多多商品url错误, 非正规的url, 请参照格式(http://mobile.yangkeduo.com/goods.html)开头的...')
            return ''

    def __del__(self):
        gc.collect()

if __name__ == '__main__':
    pinduoduo = PinduoduoParse()
    while True:
        pinduoduo_url = input('请输入待爬取的拼多多商品地址: ')
        pinduoduo_url.strip('\n').strip(';')
        goods_id = pinduoduo.get_goods_id_from_url(pinduoduo_url)
        data = pinduoduo.get_goods_data(goods_id=goods_id)
        pinduoduo.deal_with_data()