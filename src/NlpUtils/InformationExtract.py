# -*- coding: UTF-8 -*-
import json
import Utils.config as config
from Utils.database import Database
from Utils import utils
import logging
import random
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.naive_bayes import MultinomialNB

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

    def get_collection_word_seg(self, collection_name):
        self.df = self.db_obj.get_data(
            self.db_name,
            collection_name,
            keys=["Url", "WordsFrequent", ''],
        )
        print(self.df[0:10])
        wf = self.df["WordsFrequent"].tolist()
        urls = self.df["Url"].tolist()
        df_data_dict_list = [(element[1], json.loads(element[0], encoding='utf-8')) for element in zip(wf, urls)]
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

    def get_vocabulary(self): return self.vocabulary

    pass


# 生成选择训练数据和测试数据的随机序列
def randomSequence(n, size):
    result = [0 for i in range(size)]
    for i in range(n):
        x = random.randrange(0, size - 1, 1)
        result[x] = 1
    return result


if __name__ == '__main__':
    # test
    info_extract = InformationExtract()
    result = info_extract.get_collection_word_seg(info_extract.collections[0])
    print(result)
    # 读数据
    filename = 'data/sms_spam.csv'
    sms = pd.read_csv(filename, sep=',', header=0, names=['label', 'text'])

    # 拆分训练数据集和测试数据集
    size = len(sms)
    sequence = randomSequence(500, size)
    sms_train_mask = [sequence[i] == 0 for i in range(size)]
    sms_train = sms[sms_train_mask]
    sms_test_mask = [sequence[i] == 1 for i in range(size)]
    sms_test = sms[sms_test_mask]

    # 文本转换成TF-IDF向量
    train_labels = sms_train['label'].values
    train_features = sms_train['text'].values
    count_v1 = CountVectorizer(stop_words='english', max_df=0.5, decode_error='ignore')
    counts_train = count_v1.fit_transform(train_features)
    # print(count_v1.get_feature_names())
    # repr(counts_train.shape)
    tfidftransformer = TfidfTransformer()
    tfidf_train = tfidftransformer.fit(counts_train).transform(counts_train)

    test_labels = sms_test['label'].values
    test_features = sms_test['text'].values
    count_v2 = CountVectorizer(vocabulary=count_v1.vocabulary_, stop_words='english', max_df=0.5, decode_error='ignore')
    counts_test = count_v2.fit_transform(test_features)
    tfidf_test = tfidftransformer.fit(counts_test).transform(counts_test)

    # 训练
    clf = MultinomialNB(alpha=0.01)
    clf.fit(tfidf_train, train_labels)

    # 预测
    predict_result = clf.predict(tfidf_test)
    # print(predict_result)

    # 正确率
    correct = [test_labels[i] == predict_result[i] for i in range(len(predict_result))]
    r = len(predict_result)
    t = correct.count(True)
    f = correct.count(False)
    print(r, t, f, t / float(r))

    pass
