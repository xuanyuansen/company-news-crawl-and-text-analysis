# -*- coding: UTF-8 -*-
import json

from sklearn import metrics
from xlsxwriter import Workbook
import Utils.config as config
from Utils.database import Database
from Utils import utils
import logging
import random
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)


class InformationExtract(object):
    def __init__(self):
        self.db_name = config.DATABASE_NAME
        self.db_obj = Database()
        self.collections = [config.COLLECTION_NAME_CNSTOCK, config.COLLECTION_NAME_JRJ, config.COLLECTION_NAME_NBD]
        self.vocabulary = None
        self.df = None
        self.excel_name = './info/word_seg_all.xlsx'
        self.label_excel = "./info/word_seg_all_with_label"
        self.label = None

    def get_count(self, collection_name):
        return self.db_obj.get_collection(self.db_name, collection_name).find().count()

    def inner_merge(self, collection_name):
        data = self.db_obj.get_data(
            self.db_name,
            collection_name,
            keys=["WordsFrequent"],
        )
        data_list = data["WordsFrequent"].tolist()
        start_dict = dict()
        for element in data_list:
            utils.merge_dict(start_dict, json.loads(element))
        return start_dict

    # 从文件获得标签
    def load_seg_word_label(self):
        self.label = pd.read_excel(self.label_excel)
        return

    def write_excel(self, word_dict_sort, threshold: int = 10):

        ordered_list = ["word", "count"]  # list object calls by index but dict object calls items randomly

        wb = Workbook(self.excel_name)
        ws = wb.add_worksheet("Words")  # or leave it blank, default name is "Sheet 1"

        # 表头
        first_row = 0
        for header in ordered_list:
            col = ordered_list.index(header)  # we are keeping order.
            ws.write(first_row, col, header)  # we have written first row which is the header of worksheet also.

        row = 1
        for _key, _value in word_dict_sort.items():
            if _value >= threshold:
                ws.write(row, 0, _key)
                ws.write(row, 1, _value)
            row += 1  # enter the next row
        wb.close()
        return True

    def get_all_word_dictionary(self):
        all_word_dict = [self.inner_merge(coll) for coll in self.collections]
        start_dict = all_word_dict[0]
        for idx in range(1, len(all_word_dict)):
            utils.merge_dict(start_dict, all_word_dict[idx])

        start_dict_sorted = dict(sorted(start_dict.items(), key=lambda item: item[1], reverse=True))
        return start_dict_sorted

    def get_collection_word_seg(self, collection_name):
        self.df = self.db_obj.get_data(
            self.db_name,
            collection_name,
            keys=["Url", "WordsFrequent", 'Category', 'Article'],
        )
        # print(self.df[0:10])
        wf = self.df["WordsFrequent"].tolist()
        urls = self.df["Url"].tolist()
        df_data_dict_list = [(element[1], json.loads(element[0])) for element in zip(wf, urls)]
        # print(df_data_dict_list[0:10])
        start_dict = dict()
        for element in df_data_dict_list:
            if element[1] is not None:
                utils.merge_dict(start_dict, element[1])
            else:
                print(element)
                continue

        return start_dict

    def get_whole_dict(self):
        tem_dict = dict()
        for col in self.collections:
            result_dict = self.get_collection_word_seg(col)
            utils.merge_dict(tem_dict, result_dict)
        self.vocabulary = tem_dict

    def get_vocabulary(self):
        return self.vocabulary

    pass


# 生成选择训练数据和测试数据的随机序列
# n代表测试集的大小
def random_sequence(n, data_size):
    test_result = [0 for _ in range(data_size)]
    for i in range(n):
        x = random.randrange(0, data_size - 1, 1)
        test_result[x] = 1
    return test_result


def calculate_result(actual, pred):
    # average Please choose another average setting, one of [None, 'micro', 'macro', 'weighted'].
    m_precision = metrics.precision_score(actual, pred, average=None)
    m_recall = metrics.recall_score(actual, pred, average=None)
    print('predict info:')
    print('precision:{0}'.format(m_precision))
    print('recall:{0}'.format(m_recall))
    print('f1-score:{0}'.format(metrics.f1_score(actual, pred, average=None)))
