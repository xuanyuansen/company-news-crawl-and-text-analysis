# -*- coding: UTF-8 -*-
import json
import os
from sklearn import metrics
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC
from xlsxwriter import Workbook
import Utils.config as config
from NlpModel.tokenization import Tokenization
from Utils.database import Database
from Utils import utils
import random
import pandas as pd
import joblib
import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)


class InformationExtract(object):
    def __init__(self, force_train_model: bool = False):
        self.logger = utils.get_logger()
        self.db_name = config.DATABASE_NAME
        self.db_obj = Database()
        self.collections = [
            config.COLLECTION_NAME_CNSTOCK,
            config.COLLECTION_NAME_JRJ,
            config.COLLECTION_NAME_NBD,
        ]
        # 获得所有collection的列表
        self.raw_spider_name_list_dict = dict(
            {
                config.EAST_MONEY_NEWS_DB: config.EAST_MONEY_SPIDER_LIST,
                config.JRJ_NEWS_DB: config.JRJ_SPIDER_LIST,
                config.NET_EASE_STOCK_NEWS_DB: config.NET_EASE_SPIDER_LIST,
                config.STCN_NEWS_DB: config.STCN_SPIDER_LIST,
                config.SHANG_HAI_STOCK_NEWS_DB: config.SHANG_HAI_SPIDER_LIST,
                config.ZHONG_JIN_STOCK_NEWS_DB: config.ZHONG_JIN_SPIDER_LIST,
                config.NBD_STOCK_NEWS_DB: config.NBD_SPIDER_LIST,
            }
        )

        self.all_collection_name_list_dict = dict()
        self.__from_raw_spider_name_list_dict_to_col_name()
        self.vocabulary = None
        self.df_of_train_data_set = None
        self.excel_name = "./info/word_seg_all.xlsx"
        self.label_excel = "./info/word_seg_all_with_label.xlsx"
        self.label = None
        self.label_pos = dict()
        self.label_neg = dict()
        self.label_middle = dict()
        self.all_raw_data_dict_of_list = dict()
        self.cn_stock_df = None
        self.jrj_df = None
        self.nbd_df = None
        self.__load_seg_word_label()
        self.token = Tokenization(
            import_module=config.SEG_METHOD,
            user_dict=config.USER_DEFINED_WEIGHT_DICT_PATH,
            chn_stop_words_dir=config.CHN_STOP_WORDS_PATH,
        )
        self.bayes_model = None
        self.svm_model = None
        self.vocabulary = None
        self.count_vector_rise = None
        self.tfidf_transformer = TfidfTransformer()
        self.force_train = force_train_model
        if not self.force_train:
            self.__inner_load_model()

    def __from_raw_spider_name_list_dict_to_col_name(self):
        for k_db, v_col_list in self.raw_spider_name_list_dict.items():
            self.all_collection_name_list_dict[k_db] = [
                sp_dic.get("name").replace("spider", "data") for sp_dic in v_col_list
            ]
        return True

    # 准备二分类数据的标签，标签来源两种。
    # 正面label，利好公告，加上人工规则提取出的好样本 pos_ratio>0.6 and pos_cnt>5
    # 负面label，人工规则提取出的负样本，neg_ratio>0.6 and neg_cnt>5
    # 这两部分数据分为训练集和测试集，然后拿模型来预测不好判断的数据。
    @staticmethod
    def __inner_set_data_label(row):
        keys = row.keys().tolist()
        if ("Category" in keys and row["Category"] == "利好公告") or (
            row["PosRatio"] > 0.6 and row["RuleLabel"][1][0] > 6
        ):
            return "good_news"
        elif row["PosRatio"] < 0.4 and row["RuleLabel"][1][1] > 6:
            return "bad_news"
        else:
            return "unknown"

    def __inner_load_model(self):
        if os.path.exists(config.BAYES_MODEL_FILE):
            self.bayes_model = joblib.load(config.BAYES_MODEL_FILE)
            self.logger.info("bayes model load")
        if os.path.exists(config.SVM_MODEL_FILE):
            self.svm_model = joblib.load(config.SVM_MODEL_FILE)
            self.logger.info("svm model load")
        if os.path.exists("./info/count_vector_rizer.pkl"):
            self.count_vector_rise = joblib.load("./info/count_vector_rizer.pkl")
            self.logger.info("count vector rizer load")
        return

    def __inner_title_cut(self, title):
        info_dict = dict()
        for word in self.token.cut_words(title):
            value = info_dict.get(word)
            if value is None:
                info_dict[word] = 1
            else:
                info_dict[word] = value + 1
        return info_dict

    def __calculate_result(self, actual, pred):
        # average Please choose another average setting, one of [None, 'micro', 'macro', 'weighted'].
        m_precision = metrics.precision_score(actual, pred, average=None)
        m_recall = metrics.recall_score(actual, pred, average=None)
        self.logger.info("predict info:")
        self.logger.info("precision:{0}".format(m_precision))
        self.logger.info("recall:{0}".format(m_recall))
        self.logger.info(
            "f1-score:{0}".format(metrics.f1_score(actual, pred, average=None))
        )

    # 从文件获得标签
    def __load_seg_word_label(self):
        self.label = pd.read_excel(self.label_excel, na_values=0)
        self.label["label"].fillna(0, inplace=True)
        # data = self.label[self.label['label'] != 0]
        for _, row in self.label.iterrows():
            # print(row[2])
            if row[2] == 1:
                self.label_pos[row[0]] = 1
            elif row[2] == -1:
                self.label_neg[row[0]] = -1
            else:
                self.label_middle[row[0]] = 0
        self.logger.info("pos word label size {0}".format(len(self.label_pos)))
        self.logger.info("neg word label size {0}".format(len(self.label_neg)))
        return True

    def __inner_merge_data_of_db_col(self, db_name, collection_name):
        data = self.db_obj.get_data(
            db_name,
            collection_name,
            keys=["WordsFrequent"],
        )
        data_list = data["WordsFrequent"].tolist()
        start_dict = dict()
        for element in data_list:
            utils.merge_dict(start_dict, json.loads(element))
        return start_dict

    # 获得所有现有数据的切词列表
    def __get_all_word_dictionary_col_list(self, db_name, col_list: list):
        all_word_dict = [
            self.__inner_merge_data_of_db_col(db_name, collection_name)
            for collection_name in col_list
        ]
        start_dict = all_word_dict[0]
        for idx in range(1, len(all_word_dict)):
            utils.merge_dict(start_dict, all_word_dict[idx])
        return start_dict

    def __from_seg_words_to_cnt(self, seg_words: dict):
        pos_cnt = 0
        neg_cnt = 0
        mid_cnt = 0
        for k, v in seg_words.items():
            if self.label_pos.get(k) is not None:
                pos_cnt += v
            elif self.label_neg.get(k) is not None:
                neg_cnt += v
            else:
                mid_cnt += v
        return pos_cnt / float(pos_cnt + neg_cnt) if pos_cnt + neg_cnt > 0 else 0.0, (
            pos_cnt,
            neg_cnt,
            mid_cnt,
        )

    def __inner_get_data(self, db_name, collection_name):
        df = self.db_obj.get_data(db_name, collection_name)
        df["WordsFrequent"] = df.apply(
            lambda row: json.loads(row["WordsFrequent"]), axis=1
        )
        df["TitleFrequent"] = df.apply(
            lambda row: self.__inner_title_cut(row["Title"]), axis=1
        )
        df["WordsFrequent"] = df.apply(
            lambda row: dict(row["TitleFrequent"], **row["WordsFrequent"]), axis=1
        )
        # 这一列是用规则打出来的标签,用来学习模型
        df["RuleLabel"] = df.apply(
            lambda row: self.__from_seg_words_to_cnt(row["WordsFrequent"]), axis=1
        )
        df["PosRatio"] = df.apply(lambda row: row["RuleLabel"][0], axis=1)
        # 这两列是用模型学习出来的label,可能和规则打出来的不一样
        df["ClassifyLabel"] = df.apply(
            lambda row: self.__inner_set_data_label(row), axis=1
        )
        return df.sort_values(by=["PosRatio"], ascending=True)

    # 生成选择训练数据和测试数据的随机序列
    # n代表测试集的大小
    @staticmethod
    def __random_sequence(n, data_size):
        test_result = [0 for _ in range(data_size)]
        for i in range(n):
            x = random.randrange(0, data_size - 1, 1)
            test_result[x] = 1
        return test_result

    def predict_score(self, text):
        text = " ".join(self.token.cut_words(text))
        counts_to_predict_data = self.count_vector_rise.fit_transform([text])
        to_predict_data = self.tfidf_transformer.fit(counts_to_predict_data).transform(
            counts_to_predict_data
        )
        prob_nb = self.bayes_model.predict_proba(to_predict_data)
        # logging.info("prob_nb is {0}".format(prob_nb))
        prob_svm = self.svm_model.predict_proba(to_predict_data)
        # logging.info("prob svm is {0}".format(prob_svm))
        bad_score = prob_nb[0][0] + prob_svm[0][0]
        good_score = prob_nb[0][1] + prob_svm[0][1]

        if bad_score > good_score:
            return "利空", 0.5 * bad_score
        else:
            return "利好", 0.5 * good_score

    def get_raw_data_from_db(self):
        # self.cn_stock_df = self.__inner_get_data(self.collections[0])
        # self.jrj_df = self.__inner_get_data(self.collections[1])
        # self.nbd_df = self.__inner_get_data(self.collections[2])
        for db_name, col_list in self.all_collection_name_list_dict.items():
            db_data_list = [self.__inner_get_data(db_name, col_name) for col_name in col_list]
            self.all_raw_data_dict_of_list[db_name] = db_data_list
        return

    def get_train_data(self, columns: list):
        data_frame_by_db_list = []
        for db_name, data_frame_list in self.all_raw_data_dict_of_list.items():
            data_frame_by_db_list.append(pd.concat(
                [data_frame[columns] for data_frame in data_frame_list],
                axis=0,
            ))
        self.df_of_train_data_set = pd.concat(data_frame_by_db_list, axis=0)
        return True

    def build_2_class_classify_model(self, force_train_model: bool = False):
        if not force_train_model and (
            self.svm_model is not None
            and self.bayes_model is not None
            and self.count_vector_rise is not None
        ):
            self.logger.info("model and vocabulary already load!!! no train need!")
            return True
        self.get_raw_data_from_db()
        res = self.get_train_data(["Title", "Article", "ClassifyLabel"])
        self.logger.info("get train data done!")
        if res:
            data = self.df_of_train_data_set
        else:
            raise Exception
        # 先做数据筛选
        data = data[data["ClassifyLabel"] != "unknown"]
        self.logger.info("train data size {}".format(data.shape))
        data["text_cut"] = data.apply(
            lambda row: " ".join(self.token.cut_words(row["Title"] + row["Article"])),
            axis=1,
        )
        self.logger.info("cut train data done!")
        # to_predict_data = data[data['ClassifyLabel'] == 'unknown']
        print(data.groupby("ClassifyLabel").size())
        print(data.shape)
        # 拆分训练数据集和测试数据集
        size = data.shape[0]
        sequence = self.__random_sequence(round(size * 0.3), size)
        sms_train_mask = [sequence[i] == 0 for i in range(size)]
        sms_train = data[sms_train_mask]
        sms_test_mask = [sequence[i] == 1 for i in range(size)]
        sms_test = data[sms_test_mask]

        # 文本转换成TF-IDF向量
        train_labels = sms_train["ClassifyLabel"].values
        train_features = sms_train["text_cut"].values
        count_v1 = CountVectorizer(max_df=0.8, decode_error="ignore")
        counts_train = count_v1.fit_transform(train_features)
        self.vocabulary = count_v1.vocabulary_
        # print(count_v1.get_feature_names())
        # repr(counts_train.shape)
        tfidf_train = self.tfidf_transformer.fit(counts_train).transform(counts_train)

        test_labels = sms_test["ClassifyLabel"].values
        test_features = sms_test["text_cut"].values
        self.count_vector_rise = CountVectorizer(
            vocabulary=self.vocabulary, max_df=0.8, decode_error="ignore"
        )
        joblib.dump(self.count_vector_rise, config.COUNT_VECTOR_FILE)
        counts_test = self.count_vector_rise.fit_transform(test_features)
        tfidf_test = self.tfidf_transformer.fit(counts_test).transform(counts_test)

        # 训练
        self.bayes_model = MultinomialNB(alpha=0.01)
        self.bayes_model.fit(tfidf_train, train_labels)
        joblib.dump(self.bayes_model, config.BAYES_MODEL_FILE)
        # 预测
        predict_result = self.bayes_model.predict(tfidf_test)
        print(self.bayes_model.predict_proba(tfidf_test))
        # 正确率
        correct = [
            test_labels[i] == predict_result[i] for i in range(len(predict_result))
        ]
        r = len(predict_result)
        t = correct.count(True)
        f = correct.count(False)
        self.logger.info(
            "测试集大小{0} 分类正确{1} 分类错误{2} 准确率{3}".format(r, t, f, t / float(r))
        )
        self.logger.info(self.bayes_model.score(tfidf_test, test_labels))

        # svm
        self.svm_model = SVC(kernel="linear", probability=True)  # default with 'rbf'
        self.svm_model.fit(tfidf_train, train_labels)
        joblib.dump(self.svm_model, config.SVM_MODEL_FILE)
        pred = self.svm_model.predict(tfidf_test)
        self.__calculate_result(test_labels, pred)
        return True

    def get_count(self, collection_name):
        return self.db_obj.get_collection(self.db_name, collection_name).find().count()

    def write_excel(self, word_dict_sort, threshold: int = 10):
        ordered_list = [
            "word",
            "count",
        ]  # list object calls by index but dict object calls items randomly

        wb = Workbook(self.excel_name)
        ws = wb.add_worksheet("Words")  # or leave it blank, default name is "Sheet 1"

        # 表头
        first_row = 0
        for header in ordered_list:
            col = ordered_list.index(header)  # we are keeping order.
            ws.write(
                first_row, col, header
            )  # we have written first row which is the header of worksheet also.

        row = 1
        for _key, _value in word_dict_sort.items():
            if _value >= threshold:
                ws.write(row, 0, _key)
                ws.write(row, 1, _value)
            row += 1  # enter the next row
        wb.close()
        return True

    # 获得所有现有数据的切词列表
    def get_all_word_dictionary_of_new_data(self):
        dict_sorted_list = []
        for db_name, col_list in self.all_collection_name_list_dict.items():
            assert type(col_list) == list
            start_dict_ = self.__get_all_word_dictionary_col_list(db_name, col_list)
            dict_sorted_list.append(start_dict_)
            logging.info("{} {} done".format(db_name, col_list))
        out_dict = dict()
        for element in dict_sorted_list:
            utils.merge_dict(out_dict, element)
        start_dict_sorted = dict(
            sorted(out_dict.items(), key=lambda item: item[1], reverse=True)
        )
        return start_dict_sorted

    # def get_collection_word_seg(self, collection_name):
    #     self.df_of_train_data_set = self.db_obj.get_data(
    #         self.db_name,
    #         collection_name,
    #         keys=["Url", "WordsFrequent", "Category", "Article"],
    #     )
    #     # print(self.df[0:10])
    #     wf = self.df_of_train_data_set["WordsFrequent"].tolist()
    #     urls = self.df_of_train_data_set["Url"].tolist()
    #     df_data_dict_list = [
    #         (element[1], json.loads(element[0])) for element in zip(wf, urls)
    #     ]
    #     # print(df_data_dict_list[0:10])
    #     start_dict = dict()
    #     for element in df_data_dict_list:
    #         if element[1] is not None:
    #             utils.merge_dict(start_dict, element[1])
    #         else:
    #             print(element)
    #             continue
    #
    #     return start_dict
    #
    # # no use
    # # self.vocabulary 设置的不对
    # def get_whole_dict(self):
    #     tem_dict = dict()
    #     for col in self.collections:
    #         result_dict = self.get_collection_word_seg(col)
    #         utils.merge_dict(tem_dict, result_dict)
    #     self.vocabulary = tem_dict
    def get_vocabulary(self):
        return self.vocabulary

    pass


if __name__ == "__main__":
    info_extract = InformationExtract()
    dict_of_words = info_extract.get_all_word_dictionary_of_new_data()
    info_extract.write_excel(threshold=100)
    pass
