# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
# https://blog.csdn.net/coreylam/article/details/40213109
import platform

os_type = platform.system()
print(os_type)

GPU_MODE = False if os_type == "Darwin" else True
# MONGO_HOST = "127.0.0.1"
# 在mac上面开发时用远程的mongodb
# 在mac上面开发时用local的mongodb 2024 4 18
MONGODB_IP = (
    "localhost" if os_type == "Darwin" else "localhost"
)
MONGODB_PORT = 27017

REDIS_IP = "localhost"
REDIS_PORT = 6379

CHROME_DRIVER = (
    "./info/chromedriver_mac" if os_type == "Darwin" else '/usr/bin/chromedriver'#"./info/chromedriver"
)
# joint quant
cipher_key = b"C8_ACDILYdQubRfNB7oUPWvFR1G1U7uhQRBVH_NGne8="

STOCK_PRICE_REQUEST_DEFAULT_DATE = "20251229"

# 机器学习
USER_DEFINED_DICT_PATH = "./info/finance_dict.txt"
USER_DEFINED_WEIGHT_DICT_PATH = "./info/finance_dict_weight.txt"
CHN_STOP_WORDS_PATH = "./info/stopwords/"

SEG_METHOD = "jieba"
BAYES_MODEL_FILE = "./info/bayes_model.pkl"
SVM_MODEL_FILE = "./info/svm_model.pkl"
COUNT_VECTOR_FILE = "./info/count_vector_rizer.pkl"

STOCK_DATABASE_NAME = "stock"
COLLECTION_NAME_STOCK_BASIC_INFO = "zh_stock_basic_info_test"
ALL_NEWS_OF_SPECIFIC_STOCK_DATABASE = "stock_specific_news"

HK_STOCK_DATABASE_NAME = "stock_hk"
COLLECTION_NAME_STOCK_BASIC_INFO_HK = "hk_stock_basic_info"

US_STOCK_DATABASE_NAME = "stock_us"
COLLECTION_NAME_STOCK_BASIC_INFO_US = "us_stock_basic_info"
# 中国概念股
COLLECTION_NAME_STOCK_BASIC_INFO_US_ZH = "us_zh_stock_basic_info"

# DEEP LEARNING PYTORCH
CN_STOCK_INDUSTRY_DICT_FILE = "./info/cn_stock_industry_dict_file.txt"
CN_STOCK_CONCEPT_DICT_FILE = "./info/cn_stock_concept_dict_file.txt"

JQKA_NEWS_DB = "jqka"
JQKA_TT_INFOS = dict(
    {
        "name": "jqka_tt_spider",
        "start_url": "https://www.10jqka.com.cn/",
        "key_word": "jqka",
        "key_word_chn": "头条",
        "base_url": "https://www.10jqka.com.cn/",
        "end_page": 3,
    }
)

JQKA_SPIDER_LIST = [
    JQKA_TT_INFOS,
]


# JRJ
JRJ_NEWS_DB = "jrj_news"
JRJ_STOCK_YBJX = dict(
    {
        "name": "jrj_stock_yan_bao_jing_xuan_spider",
        "start_url": "https://stock.jrj.com.cn/ybjx.shtml?jrjbq",
        "key_word": "stock_ss_gs",
        "key_word_chn": "研报精选",
        "base_url": "http://stock.jrj.com.cn/",
        "end_page": 1,
    }
)
# http://stock.jrj.com.cn/hotstock/gnjj.shtml
JRJ_HOT_STOCK_GGJX = dict(
    {
        "name": "jrj_hot_stock_bao_gao_spider",
        "start_url": "https://stock.jrj.com.cn/ggjj.shtml?jrjbq",
        "key_word": "hot_stock_jj",
        "key_word_chn": "公告精选",
        "base_url": "http://stock.jrj.com.cn/",
        "end_page": 1,
    }
)
JRJ_STOCK_JH_NEWS = dict(
    {
        "name": "jrj_stock_ji_hui_news_spider",
        "start_url": "https://stock.jrj.com.cn/jhqb.shtml?jrjbq",
        "key_word": "stock_news",
        "key_word_chn": "机会情报",
        "base_url": "http://stock.jrj.com.cn/",
        "end_page": 1,
    }
)
JRJ_STOCK_A_TT = dict(
    {
        "name": "jrj_stock_a_gu_tt_spider",
        "start_url": "https://stock.jrj.com.cn/agtt.shtml?jrjbq",
        "key_word": "stock_zhang_ting",
        "key_word_chn": "A股头条",
        "base_url": "http://stock.jrj.com.cn/",
        "end_page": 1,
    }
)
JRJ_SPIDER_LIST = [
    JRJ_STOCK_YBJX,
    JRJ_HOT_STOCK_GGJX,
    JRJ_STOCK_JH_NEWS,
    JRJ_STOCK_A_TT,
]

# NBD NEWS
NBD_STOCK_NEWS_DB = "nbd_news"
NBD_STOCK_IMPORTANT_NEWS = dict(
    {
        "name": "nbd_stock_important_news_spider",
        "start_url": "https://stocks.nbd.com.cn/columns/318",
        "key_word": "stock_important_news",
        "key_word_chn": "重磅推荐",
        "base_url": "https://stocks.nbd.com.cn/",
        "end_page": 20,
    }
)
NBD_STOCK_TREND_A = dict(
    {
        "name": "nbd_stock_trend_a_spider",
        "start_url": "https://stocks.nbd.com.cn/columns/275",
        "key_word": "stock_trend_a",
        "key_word_chn": "A股动态",
        "base_url": "https://stocks.nbd.com.cn/",
        "end_page": 20,
    }
)
NBD_DAO_DA_INVEST_LOG = dict(
    {
        "name": "nbd_stock_dao_da_invest_log_spider",
        "start_url": "https://stocks.nbd.com.cn/columns/476",
        "key_word": "stock_dao_da_invest",
        "key_word_chn": "道达投资手记",
        "base_url": "https://stocks.nbd.com.cn/",
        "end_page": 20,
    }
)
NBD_VOLCANO_FORTUNE_NEWS = dict(
    {
        "name": "nbd_stock_volcano_fortune_news_spider",
        "start_url": "https://stocks.nbd.com.cn/columns/800",
        "key_word": "stock_volcano_fortune",
        "key_word_chn": "火山财富",
        "base_url": "https://stocks.nbd.com.cn/",
        "end_page": 20,
    }
)
NBD_SPIDER_LIST = [
    NBD_STOCK_IMPORTANT_NEWS,
    NBD_STOCK_TREND_A,
    NBD_DAO_DA_INVEST_LOG,
    NBD_VOLCANO_FORTUNE_NEWS,
]

# net ease
NET_EASE_STOCK_NEWS_DB = "net_ease_news"
NET_EASE_STOCK_NEWS = dict(
    {
        "name": "net_ease_stock_specific_news_spider",
        "start_url": "http://money.163.com/special/00251LR5/gptj.html",
        "key_word": "stock_specific_news",
        "key_word_chn": "个股资讯",
        "base_url": "http://money.163.com/",
        "end_page": 21,
    }
)
NET_EASE_MARKET_NEWS = dict(
    {
        "name": "net_ease_stock_market_news_spider",
        "start_url": "http://money.163.com/special/00251LR5/cpznList.html",
        "key_word": "stock_market_news",
        "key_word_chn": "市场资讯",
        "base_url": "http://money.163.com/",
        "end_page": 21,
    }
)
NET_EASE_SPIDER_LIST = [NET_EASE_STOCK_NEWS, NET_EASE_MARKET_NEWS]

# 2023 05 21 http 升级为 https 加密连接
EAST_MONEY_NEWS_DB = "east_money_news"
EAST_MONEY_A_STOCK_NEWS = dict(
    {
        "name": "east_money_cn_stock_company_news_spider",
        "start_url": "https://finance.eastmoney.com/a/cssgs.html",
        "key_word": "stock_cn_company_news",
        "key_word_chn": "A股公司",
        "base_url": "https://finance.eastmoney.com/",
        "end_page": 50,
    }
)
EAST_MONEY_A_MARKET_NEWS = dict(
    {
        "name": "east_money_cn_market_data_news_spider",
        "start_url": "https://stock.eastmoney.com/a/cscsj.html",
        "key_word": "cn_market_data_news",
        "key_word_chn": "市场数据",
        "base_url": "https://finance.eastmoney.com/",
        "end_page": 2,
    }
)
EAST_MONEY_DEEP_INVESTIGATE_NEWS = dict(
    {
        "name": "east_money_cn_deep_investigate_news_spider",
        "start_url": "https://finance.eastmoney.com/a/czsdc.html",
        "key_word": "cn_stock_deep_investigate_news",
        "key_word_chn": "纵深调查",
        "base_url": "https://finance.eastmoney.com/",
        "end_page": 2,
    }
)
EAST_MONEY_INDUSTRY_DEEP_REVIEW_NEWS = dict(
    {
        "name": "east_money_cn_industry_deep_review_news_spider",
        "start_url": "https://finance.eastmoney.com/a/ccyts.html",
        "key_word": "cn_industry_deep_review_news",
        "key_word_chn": "产业透视",
        "base_url": "https://finance.eastmoney.com/",
        "end_page": 2,
    }
)
EAST_MONEY_STOCK_OPINION_NEWS = dict(
    {
        "name": "east_money_cn_stock_opinion_news_spider",
        "start_url": "https://finance.eastmoney.com/a/cgspl.html",
        "key_word": "cn_stock_opinion_news",
        "key_word_chn": "股市评论",
        "base_url": "https://finance.eastmoney.com/",
        "end_page": 2,
    }
)
EAST_MONEY_BUSINESS_NEWS = dict(
    {
        "name": "east_money_cn_business_news_spider",
        "start_url": "https://biz.eastmoney.com/a/csyzx.html",
        "key_word": "cn_business_news",
        "key_word_chn": "商业资讯",
        "base_url": "https://finance.eastmoney.com/",
        "end_page": 25,
    }
)
EAST_MONEY_SPIDER_LIST = [
    EAST_MONEY_A_STOCK_NEWS,
    EAST_MONEY_A_MARKET_NEWS,
    EAST_MONEY_DEEP_INVESTIGATE_NEWS,
    EAST_MONEY_INDUSTRY_DEEP_REVIEW_NEWS,
    EAST_MONEY_STOCK_OPINION_NEWS,
    EAST_MONEY_BUSINESS_NEWS,
]

# shang hai
SHANG_HAI_STOCK_NEWS_DB = "shanghai_cn_stock_news"
SHANG_HAI_STOCK_COMPANY_NEWS = dict(
    {
        "name": "shanghai_stock_company_focus_news_spider",
        "start_url": "https://www.cnstock.com/channel/10006",
        "key_word": "stock_company_news",
        "key_word_chn": "公司聚集", # "公司"->"全部"
        "base_url": "https://www.cnstock.com/",
        "end_page": 5,
    }
)
SHANG_HAI_STOCK_ANNOUNCEMENT_NEWS = dict(
    {
        "name": "shanghai_stock_company_announcement_spider",
        "start_url": "https://www.cnstock.com/channel/10111",
        "key_word": "stock_announcement_news",
        "key_word_chn": "公告解读", # 公告速递
        "base_url": "http://ggjd.cnstock.com/",
        "end_page": 4,
    }
)
SHANG_HAI_STOCK_COMPANY_KUAI_XUN_NEWS = dict(
    {
        "name": "shanghai_stock_company_kuai_xun_spider",
        "start_url": "https://www.cnstock.com/channel/10030",
        "key_word": "stock_kuai_xun_news",
        "key_word_chn": "公告快讯", # 公司快讯
        "base_url": "http://ggjd.cnstock.com/",
        "end_page": 4,
    }
)

SHANG_HAI_STOCK_INDUSTRY_NEWS = dict(
    {
        "name": "shanghai_stock_industry_news_spider",
        "start_url": "https://www.cnstock.com/channel/10029",
        "key_word": "stock_industry_news",
        "key_word_chn": "产业聚焦", # "公司"->"聚焦"
        "base_url": "https://news.cnstock.com/",
        "end_page": 3,
    }
)
SHANG_HAI_SPIDER_LIST = [
    SHANG_HAI_STOCK_COMPANY_NEWS,
    SHANG_HAI_STOCK_ANNOUNCEMENT_NEWS,
    SHANG_HAI_STOCK_COMPANY_KUAI_XUN_NEWS,
    SHANG_HAI_STOCK_INDUSTRY_NEWS,
]

# zhong jin
ZHONG_JIN_STOCK_NEWS_DB = "zhong_jin_stock_news_db"
ZHONG_JIN_STOCK_NEWS = dict(
    {
        "name": "zhong_jin_stock_news_spider",
        "start_url": "http://sc.stock.cnfol.com/ggzixun/",
        "key_word": "stock_news",
        "key_word_chn": "个股资讯",
        "base_url": "http://sc.stock.cnfol.com/",
        "end_page": 100,
    }
)
ZHONG_JIN_STOCK_MARKET_ANALYZE_NEWS = dict(
    {
        "name": "zhong_jin_stock_market_analyze_news_spider",
        "start_url": "http://sc.stock.cnfol.com/shichangceping/",
        "key_word": "stock_market_analyze_news",
        "key_word_chn": "市场测评",
        "base_url": "http://sc.stock.cnfol.com/",
        "end_page": 100,
    }
)
ZHONG_JIN_STOCK_BAN_KUAI_SECTION_ANALYZE_NEWS = dict(
    {
        "name": "zhong_jin_stock_ban_kuai_section_news_spider",
        "start_url": "http://sc.stock.cnfol.com/bkjujiao/",
        "key_word": "stock_ban_kuai_section_news",
        "key_word_chn": "板块聚焦",
        "base_url": "http://sc.stock.cnfol.com/",
        "end_page": 100,
    }
)
ZHONG_JIN_STOCK_CHUANG_YE_BAN_NEWS = dict(
    {
        "name": "zhong_jin_stock_chuang_ye_ban_news_spider",
        "start_url": "http://sc.stock.cnfol.com/cybzixun/",
        "key_word": "stock_ban_kuai_section_news",
        "key_word_chn": "创业板资讯",
        "base_url": "http://sc.stock.cnfol.com/",
        "end_page": 100,
    }
)
ZHONG_JIN_STOCK_MARKET_SEEK_GOLD_NEWS = dict(
    {
        "name": "zhong_jin_stock_market_seek_gold_news_spider",
        "start_url": "http://sc.stock.cnfol.com/shichangjuejin/",
        "key_word": "stock_market_seek_gold_news",
        "key_word_chn": "市场掘金",
        "base_url": "http://sc.stock.cnfol.com/",
        "end_page": 100,
    }
)
ZHONG_JIN_STOCK_MARKET_VERY_IMPORTANT_NEWS = dict(
    {
        "name": "zhong_jin_stock_market_very_important_news_spider",
        "start_url": "http://sc.stock.cnfol.com/gushiyaowen/",
        "key_word": "stock_market_very_important_news",
        "key_word_chn": "股市要闻",
        "base_url": "http://sc.stock.cnfol.com/",
        "end_page": 100,
    }
)
ZHONG_JIN_STOCK_MARKET_MAIN_FORCE_TREND_NEWS = dict(
    {
        "name": "zhong_jin_stock_market_main_force_trend_news_spider",
        "start_url": "http://sc.stock.cnfol.com/zldongxiang/",
        "key_word": "stock_market_main_force_trend_news",
        "key_word_chn": "主力动向",
        "base_url": "http://sc.stock.cnfol.com/",
        "end_page": 100,
    }
)
ZHONG_JIN_SPIDER_LIST = [
    ZHONG_JIN_STOCK_NEWS,
    ZHONG_JIN_STOCK_MARKET_ANALYZE_NEWS,
    ZHONG_JIN_STOCK_BAN_KUAI_SECTION_ANALYZE_NEWS,
    ZHONG_JIN_STOCK_CHUANG_YE_BAN_NEWS,
    ZHONG_JIN_STOCK_MARKET_SEEK_GOLD_NEWS,
    ZHONG_JIN_STOCK_MARKET_VERY_IMPORTANT_NEWS,
    ZHONG_JIN_STOCK_MARKET_MAIN_FORCE_TREND_NEWS,
]

ALL_SPIDER_LIST_OF_DICT = dict(
    {
        EAST_MONEY_NEWS_DB: EAST_MONEY_SPIDER_LIST,
        JRJ_NEWS_DB: JRJ_SPIDER_LIST,
        NET_EASE_STOCK_NEWS_DB: NET_EASE_SPIDER_LIST,
        JQKA_NEWS_DB: JQKA_SPIDER_LIST,
        SHANG_HAI_STOCK_NEWS_DB: SHANG_HAI_SPIDER_LIST,
        ZHONG_JIN_STOCK_NEWS_DB: ZHONG_JIN_SPIDER_LIST,
        NBD_STOCK_NEWS_DB: NBD_SPIDER_LIST,
    }
)

LATEST_DAY_OR_PAGE_SETTING = 3
