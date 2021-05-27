import json

from Utils.database import Database
from Utils import config
from Utils import utils
import re
import jieba
import pkuseg
import logging
import spacy_pkuseg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)


class Tokenization(object):
    def __init__(self, import_module="jieba", user_dict=None, chn_stop_words_dir=None):
        # self.database = Database().conn[config.DATABASE_NAME]  #.get_collection(config.COLLECTION_NAME_CNSTOCK)
        self.database = Database()
        self.import_module = import_module
        if self.import_module == "jieba" and user_dict is not None:
            jieba.load_userdict(user_dict)
            logging.info("load user dict done")
        self.user_dict = user_dict
        if chn_stop_words_dir:
            self.stop_words_list = utils.get_chn_stop_words(chn_stop_words_dir)
        else:
            self.stop_words_list = list()

    # 返回文章中的代码以及切词的结果
    # 切词的结果是词，以及词出现的次数，用json格式存储
    def find_relevant_stock_codes_in_article(self, article, stock_name_code_dict):
        stock_codes_set = list()
        cut_words_lists = self.cut_words(article)
        info_dict = dict()
        if cut_words_lists:
            for word in cut_words_lists:
                value = info_dict.get(word)
                if value is None:
                    info_dict[word] = 1
                else:
                    info_dict[word] = value + 1

                if stock_name_code_dict.get(word) is not None:
                    stock_codes_set.append(stock_name_code_dict.get(word))

        info_dict_sorted = dict(sorted(info_dict.items(), key=lambda item: item[1], reverse=True))
        info_dict_sorted_json = json.dumps(info_dict_sorted, ensure_ascii=False)
        f_codes = list(set(stock_codes_set))
        f_codes.sort()
        return f_codes, info_dict_sorted_json

    def find_stock_code_and_name_in_article(self, article, stock_name_code_dict: dict):
        # 直接从原始文档里面寻找，而非切词后再寻找
        stock_codes_dict = dict()
        for name, code in stock_name_code_dict.items():
            if name in article:
                stock_codes_dict[name] = code
        stock_codes_dict_sorted = dict(sorted(stock_codes_dict.items(), key=lambda item: item[1], reverse=False))
        f_codes_json = json.dumps(stock_codes_dict_sorted, ensure_ascii=False)

        cut_words_lists = self.cut_words(article)
        info_dict = dict()
        if len(cut_words_lists) > 0:
            for word in cut_words_lists:
                value = info_dict.get(word)
                if value is None:
                    info_dict[word] = 1
                else:
                    info_dict[word] = value + 1

        info_dict_sorted = dict(sorted(info_dict.items(), key=lambda item: item[1], reverse=True))
        info_dict_sorted_json = json.dumps(info_dict_sorted, ensure_ascii=False)

        return f_codes_json, info_dict_sorted_json

    def cut_words(self, ori_text):
        ori_text = re.sub('[’!"#$%&\'()*+,-./:;<=>?@，。★、…【】《》？“”‘！\\[\\]^_`{|}~\\s]+', "", ori_text)
        # print(ori_text)
        # out_str = list()
        sentence_seg = None
        if self.import_module == "jieba":
            sentence_seg = list(jieba.cut(ori_text, HMM=True))
        elif self.import_module == "pkuseg":
            seg = spacy_pkuseg.pkuseg(user_dict=self.user_dict, postag=False)  # 添加自定义词典
            sentence_seg = seg.cut(ori_text)  # 进行分词
        else:
            logging.warning("module not defined")
        out_str = [word if (word not in self.stop_words_list
                            and word != "\t"
                            and utils.is_contain_chn(word)
                            and len(word) >= 1) else '' for word in sentence_seg]
        out_str = list(filter(lambda a: a != '', out_str))
        return out_str

    def update_news_database_rows(
            self,
            database_name,
            collection_name,
            incremental_column_name="RelatedStockCodes",
    ):
        name_code_df = self.database.get_data(
            config.STOCK_DATABASE_NAME,
            config.COLLECTION_NAME_STOCK_BASIC_INFO,
            keys=["name", "code"],
        )
        name_code_dict = dict(name_code_df.values)
        data = self.database.get_collection(database_name, collection_name).find()
        for row in data:
            # if row["Date"] > "2019-05-20 00:00:00":
            # 在新增数据中，并不存在更新列，但是旧数据中已存在更新列，因此需要
            # 判断数据结构中是否包含该incremental_column_name字段
            if incremental_column_name not in row.keys():
                related_stock_codes_list = self.find_relevant_stock_codes_in_article(
                    row["Article"], name_code_dict
                )
                self.database.update_row(
                    database_name,
                    collection_name,
                    {"_id": row["_id"]},
                    {incremental_column_name: " ".join(related_stock_codes_list)},
                )
                logging.info(
                    "[{} -> {} -> {}] updated {} key value ... ".format(
                        database_name,
                        collection_name,
                        row["Date"],
                        incremental_column_name,
                    )
                )
            else:
                logging.info(
                    "[{} -> {} -> {}] has already existed {} key value ... ".format(
                        database_name,
                        collection_name,
                        row["Date"],
                        incremental_column_name,
                    )
                )


if __name__ == "__main__":
    tokenization = Tokenization(
        import_module="jieba",
        user_dict="../info/finance_dict_weight.txt",
        chn_stop_words_dir="../info/stopwords/",
    )
    documents_list = \
        [
            "中央、地方支持政策频出,煤炭 []行 业站上了风口 券商研报浩如烟海，投资线索眼花缭乱，\
            第一财经推出《一财研选》产品，挖掘研报精华，每期梳理5条投资线索，便于您短时间内获\
            取有价值的信息。专业团队每周日至每周四晚8点准时“上新”，助您投资顺利！",
            "郭文仓到重点工程项目督导检查 2月2日,公司党委书记、董事长、总经理郭文仓,公司董事,\
            股份公司副总经理、总工程师、郭毅民,股份公司副总经理张国富、柴高贵及相关单位负责人到\
            焦化厂煤场全封闭和干熄焦等重点工程项目建设工地督导检查施工进度和安全工作情况。顺丰快递，上机数控"
        ]
    for text in documents_list:
        cut_words_list = tokenization.cut_words(text)
        print(cut_words_list)
    # tokenization.update_news_database_rows(config.DATABASE_NAME, "jrj")
