# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
# https://blog.csdn.net/coreylam/article/details/40213109
import platform

os_type = platform.system()
print(os_type)

MONGODB_IP = "localhost"
MONGODB_PORT = 27017
REDIS_IP = "localhost"
REDIS_PORT = 6379
THREAD_NUMS_FOR_SPYDER = 4

SEG_METHOD = "jieba"
DATABASE_NAME = "finnewshunter"

COLLECTION_NAME_CNSTOCK = "cnstock"

CHROME_DRIVER = "./info/chromedriver_mac" if os_type == 'Darwin' else "./info/chromedriver"
# WEBSITES_LIST_TO_BE_CRAWLED_CNSTOCK = {"https://company.cnstock.com/company/scp_gsxw": "公司聚焦",
#                                        "https://ggjd.cnstock.com/gglist/search/qmtbbdj": "公告解读",
#                                        "https://ggjd.cnstock.com/gglist/search/ggkx": "公告快讯",
#                                        "https://ggjd.cnstock.com/company/scp_ggjd/tjd_sdlh": "利好公告"}
WEBSITES_LIST_TO_BE_CRAWLED_CNSTOCK = {
    "https://company.cnstock.com/company/scp_gsxw": "公司聚焦",
    "http://ggjd.cnstock.com/company/scp_ggjd/tjd_bbdj": "公告解读",
    "http://ggjd.cnstock.com/company/scp_ggjd/tjd_ggkx": "公告快讯",
    "https://ggjd.cnstock.com/company/scp_ggjd/tjd_sdlh": "利好公告",
}
RECORD_CNSTOCK_FAILED_URL_TXT_FILE_PATH = "./info/cnstock_failed_urls.txt"
CNSTOCK_MAX_REJECTED_AMOUNTS = 10

COLLECTION_NAME_JRJ = 'jrj'
COLLECTION_NAME_NBD = "nbd"
WEBSITES_LIST_TO_BE_CRAWLED_NBD = "http://stocks.nbd.com.cn/columns/275/page"
RECORD_NBD_FAILED_URL_TXT_FILE_PATH = "./info/nbd_failed_urls.txt"
NBD_TOTAL_PAGES_NUM = 684
NBD_MAX_REJECTED_AMOUNTS = 10
CACHE_SAVED_NEWS_NBD_TODAY_VAR_NAME = "cache_news_queue_nbd"

TUSHARE_TOKEN = "97fbc4c73727b5d171ca6670cbc4af8b0a3de5fbab74b52f30b598cc"
STOCK_DATABASE_NAME = "stock"
COLLECTION_NAME_STOCK_BASIC_INFO = "basic_info"
STOCK_PRICE_REQUEST_DEFAULT_DATE = "20150101"
REDIS_CLIENT_FOR_CACHING_STOCK_INFO_DB_ID = 1

ALL_NEWS_OF_SPECIFIC_STOCK_DATABASE = "stocknews"

TOPIC_NUMBER = 200
SVM_TUNED_PARAMTERS = {
    "kernel": ["rbf"],
    "gamma": [10, 20, 50, 100, 150, 200],
    "C": [10, 15, 20, 30, 50, 100],
}
RDFOREST_TUNED_PARAMTERS = {
    "n_estimators": [1, 2, 3, 4, 5, 10],
    "criterion": ["gini", "entropy"],
    "max_features": ["auto", "sqrt"],
}
CLASSIFIER_SCORE_LIST = ["f1_weighted"]
USER_DEFINED_DICT_PATH = "./info/finance_dict.txt"
USER_DEFINED_WEIGHT_DICT_PATH = "./info/finance_dict_weight.txt"
CHN_STOP_WORDS_PATH = "./info/stopwords/"

CACHE_NEWS_REDIS_DB_ID = 0
CACHE_NEWS_LIST_NAME = "cache_news_waiting_for_classification"

CACHE_RECORED_OPENED_PYTHON_PROGRAM_DB_ID = 0
CACHE_RECORED_OPENED_PYTHON_PROGRAM_VAR = "opened_python_scripts"

MINIMUM_STOCK_NEWS_NUM_FOR_ML = 1000

# 机器学习
BAYES_MODEL_FILE = './info/bayes_model.pkl'

STCN_DJSJ = dict({'name': 'stcn_du_jia_data_spider',
                  'start_url': 'https://data.stcn.com/djsj/index.html',
                  'key_word': 'djsj',
                  'key_word_chn': '独家数据',
                  'base_url': 'https://data.stcn.com/'})
STCN_DJJD = dict({'name': 'stcn_du_jia_jie_du_spider',
                  'start_url': 'https://stock.stcn.com/djjd/index.html',
                  'key_word': 'djjd',
                  'key_word_chn': '独家解读',
                  'base_url': 'https://stock.stcn.com/'})

STCN_JIGOU = dict({'name': 'stcn_ji_gou_buyer_spider',
                   'start_url': 'https://finance.stcn.com/index.html',
                   'key_word': 'jigou',
                   'key_word_chn': '机构',
                   'base_url': 'https://finance.stcn.com/'})

# https://kuaixun.stcn.com/egs/index.html 股市
STCN_KX_EGS = dict({'name': 'stcn_egs_fast_info_spider',
                    'start_url': 'https://kuaixun.stcn.com/egs/index.html',
                    'key_word': 'egs',
                    'key_word_chn': '快讯',
                    'base_url': 'https://kuaixun.stcn.com/'})

STCN_KX_REPORT = dict({'name': 'stcn_company_report_spider',
                       'start_url': 'https://kuaixun.stcn.com/yb/index.html',
                       'key_word': 'yb',
                       'key_word_chn': '研报',
                       'base_url': 'https://kuaixun.stcn.com/'})

STCN_COMPANY_TRENDS = dict({'name': 'stcn_company_latest_trends_spider',
                            'start_url': 'https://company.stcn.com/gsdt/index.html',
                            'key_word': 'gsdt',
                            'key_word_chn': '公司动态',
                            'base_url': 'https://company.stcn.com/'})

STCN_COMPANY_NEWS = dict({'name': 'stcn_company_news_spider',
                          'start_url': 'https://company.stcn.com/gsxw/index.html',
                          'key_word': 'gsxw',
                          'key_word_chn': '公司新闻',
                          'base_url': 'https://company.stcn.com/'})

STCN_DEEP_NEWS = dict({'name': 'stcn_company_deep_news_spider',
                       'start_url': 'https://news.stcn.com/sd/index.html',
                       'key_word': 'sd',
                       'key_word_chn': '深度',
                       'base_url': 'https://news.stcn.com/'})

# JRJ
JRJ_INVEST_SCGC = dict({'name': 'jrj_invest_market_analyze_spider',
                        'start_url': 'http://stock.jrj.com.cn/invest/scgc.shtml',
                        'key_word': 'invest_scgc',
                        'key_word_chn': '市场分析',
                        'base_url': 'http://stock.jrj.com.cn/invest/',
                        'end_page': 2})

JRJ_STOCK_SSGS = dict({'name': 'jrj_stock_shang_shi_gong_si_spider',
                       'start_url': 'http://stock.jrj.com.cn/list/stockssgs.shtml',
                       'key_word': 'stock_ss_gs',
                       'key_word_chn': '上市公司',
                       'base_url': 'http://stock.jrj.com.cn/',
                       'end_page': 2})

# http://stock.jrj.com.cn/hotstock/gnjj.shtml
JRJ_HOT_STOCK_GNJJ = dict({'name': 'jrj_hot_stock_jue_jin_spider',
                           'start_url': 'http://stock.jrj.com.cn/hotstock/gnjj.shtml',
                           'key_word': 'hot_stock_jj',
                           'key_word_chn': '行业掘金',
                           'base_url': 'http://stock.jrj.com.cn/',
                           'end_page': 2})

JRJ_STOCK_GU_SHI_NEWS = dict({'name': 'jrj_stock_gu_shi_news_spider',
                              'start_url': 'http://stock.jrj.com.cn/list/stockgszx.shtml',
                              'key_word': 'stock_news',
                              'key_word_chn': '股市资讯',
                              'base_url': 'http://stock.jrj.com.cn/',
                              'end_page': 2})

JRJ_STOCK_ZHANG_TING_PREDICT = dict({'name': 'jrj_stock_zhang_ting_predict_spider',
                                     'start_url': 'http://stock.jrj.com.cn/list/ztbyc.shtml',
                                     'key_word': 'stock_zhang_ting',
                                     'key_word_chn': '涨停板预测',
                                     'base_url': 'http://stock.jrj.com.cn/',
                                     'end_page': 2})

NBD_STOCK_IMPORTANT_NEWS = dict({'name': 'nbd_stock_important_news_spider',
                                 'start_url': 'http://stocks.nbd.com.cn/columns/318',
                                 'key_word': 'stock_important_news',
                                 'key_word_chn': '重磅推荐',
                                 'base_url': 'http://stocks.nbd.com.cn/',
                                 'end_page': 2})

NBD_STOCK_TREND_A = dict({'name': 'nbd_stock_trend_a_spider',
                          'start_url': 'http://stocks.nbd.com.cn/columns/275',
                          'key_word': 'stock_trend_a',
                          'key_word_chn': 'A股动态',
                          'base_url': 'http://stocks.nbd.com.cn/',
                          'end_page': 2})

NBD_DAO_DA_INVEST_LOG = dict({'name': 'nbd_stock_dao_da_invest_log_spider',
                              'start_url': 'http://stocks.nbd.com.cn/columns/476',
                              'key_word': 'stock_dao_da_invest',
                              'key_word_chn': '道达投资手记',
                              'base_url': 'http://stocks.nbd.com.cn/',
                              'end_page': 2})

NBD_VOLCANO_FORTUNE_NEWS = dict({'name': 'nbd_stock_volcano_fortune_news_spider',
                                 'start_url': 'http://stocks.nbd.com.cn/columns/800',
                                 'key_word': 'stock_volcano_fortune',
                                 'key_word_chn': '火山财富',
                                 'base_url': 'http://stocks.nbd.com.cn/',
                                 'end_page': 2})

NET_EASE_STOCK_NEWS = dict({'name': 'net_ease_stock_specific_news_spider',
                            'start_url': 'http://money.163.com/special/00251LR5/gptj.html',
                            'key_word': 'stock_specific_news',
                            'key_word_chn': '个股资讯',
                            'base_url': 'http://money.163.com/',
                            'end_page': 11})

EAST_MONEY_A_STOCK_NEWS = dict({'name': 'east_money_cn_stock_news_spider',
                                'start_url': 'http://finance.eastmoney.com/a/cssgs.html',
                                'key_word': 'stock_cn_news',
                                'key_word_chn': 'A股公司',
                                'base_url': 'ttp://finance.eastmoney.com/',
                                'end_page': 2})
