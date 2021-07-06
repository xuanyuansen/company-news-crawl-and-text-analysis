# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
# https://blog.csdn.net/coreylam/article/details/40213109
import platform

os_type = platform.system()
print(os_type)

GPU_MODE = False if os_type == "Darwin" else True
# MONGO_HOST = "127.0.0.1"
# 在mac上面开发时用远程的mongodb
MONGODB_IP = (
    "[2409:8a28:e6d:9940:a925:2282:fd4f:f00f]" if os_type == "Darwin" else "localhost"
)
MONGODB_PORT = 27017

REDIS_IP = "localhost"
REDIS_PORT = 6379

CHROME_DRIVER = (
    "./info/chromedriver_mac" if os_type == "Darwin" else "./info/chromedriver"
)
# joint quant
cipher_key = b"C8_ACDILYdQubRfNB7oUPWvFR1G1U7uhQRBVH_NGne8="

STOCK_PRICE_REQUEST_DEFAULT_DATE = "20180101"

# 机器学习
USER_DEFINED_DICT_PATH = "./info/finance_dict.txt"
USER_DEFINED_WEIGHT_DICT_PATH = "./info/finance_dict_weight.txt"
CHN_STOP_WORDS_PATH = "./info/stopwords/"

SEG_METHOD = "jieba"
BAYES_MODEL_FILE = "./info/bayes_model.pkl"
SVM_MODEL_FILE = "./info/svm_model.pkl"
COUNT_VECTOR_FILE = "./info/count_vector_rizer.pkl"

STOCK_DATABASE_NAME = "stock"
COLLECTION_NAME_STOCK_BASIC_INFO = "basic_info"
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

STCN_NEWS_DB = "stcn"
STCN_DJSJ = dict(
    {
        "name": "stcn_du_jia_data_spider",
        "start_url": "https://data.stcn.com/djsj/index.html",
        "key_word": "djsj",
        "key_word_chn": "独家数据",
        "base_url": "https://data.stcn.com/",
        "end_page": 100,
    }
)
STCN_DJJD = dict(
    {
        "name": "stcn_du_jia_jie_du_spider",
        "start_url": "https://stock.stcn.com/djjd/index.html",
        "key_word": "djjd",
        "key_word_chn": "独家解读",
        "base_url": "https://stock.stcn.com/",
        "end_page": 20,
    }
)

STCN_JIGOU = dict(
    {
        "name": "stcn_ji_gou_buyer_spider",
        "start_url": "https://finance.stcn.com/index.html",
        "key_word": "jigou",
        "key_word_chn": "机构",
        "base_url": "https://finance.stcn.com/",
        "end_page": 20,
    }
)
# https://kuaixun.stcn.com/egs/index.html 股市
STCN_KX_EGS = dict(
    {
        "name": "stcn_egs_fast_info_spider",
        "start_url": "https://kuaixun.stcn.com/egs/index.html",
        "key_word": "egs",
        "key_word_chn": "快讯",
        "base_url": "https://kuaixun.stcn.com/",
        "end_page": 20,
    }
)

STCN_KX_REPORT = dict(
    {
        "name": "stcn_company_report_spider",
        "start_url": "https://kuaixun.stcn.com/yb/index.html",
        "key_word": "yb",
        "key_word_chn": "研报",
        "base_url": "https://kuaixun.stcn.com/",
        "end_page": 20,
    }
)

STCN_COMPANY_TRENDS = dict(
    {
        "name": "stcn_company_latest_trends_spider",
        "start_url": "https://company.stcn.com/gsdt/index.html",
        "key_word": "gsdt",
        "key_word_chn": "公司动态",
        "base_url": "https://company.stcn.com/",
        "end_page": 20,
    }
)

STCN_COMPANY_NEWS = dict(
    {
        "name": "stcn_company_news_spider",
        "start_url": "https://company.stcn.com/gsxw/index.html",
        "key_word": "gsxw",
        "key_word_chn": "公司新闻",
        "base_url": "https://company.stcn.com/",
        "end_page": 20,
    }
)

STCN_DEEP_NEWS = dict(
    {
        "name": "stcn_company_deep_news_spider",
        "start_url": "https://news.stcn.com/sd/index.html",
        "key_word": "sd",
        "key_word_chn": "深度",
        "base_url": "https://news.stcn.com/",
        "end_page": 20,
    }
)
STCN_SPIDER_LIST = [
    STCN_DJSJ,
    STCN_DJJD,
    STCN_JIGOU,
    STCN_KX_EGS,
    STCN_KX_REPORT,
    STCN_COMPANY_TRENDS,
    STCN_COMPANY_NEWS,
    STCN_DEEP_NEWS,
]


# JRJ
JRJ_NEWS_DB = "jrj_news"
JRJ_INVEST_SCGC = dict(
    {
        "name": "jrj_invest_market_analyze_spider",
        "start_url": "http://stock.jrj.com.cn/invest/scgc.shtml",
        "key_word": "invest_scgc",
        "key_word_chn": "市场分析",
        "base_url": "http://stock.jrj.com.cn/invest/",
        "end_page": 11,
    }
)
JRJ_STOCK_SSGS = dict(
    {
        "name": "jrj_stock_shang_shi_gong_si_spider",
        "start_url": "http://stock.jrj.com.cn/list/stockssgs.shtml",
        "key_word": "stock_ss_gs",
        "key_word_chn": "上市公司",
        "base_url": "http://stock.jrj.com.cn/",
        "end_page": 11,
    }
)
# http://stock.jrj.com.cn/hotstock/gnjj.shtml
JRJ_HOT_STOCK_GNJJ = dict(
    {
        "name": "jrj_hot_stock_jue_jin_spider",
        "start_url": "http://stock.jrj.com.cn/hotstock/gnjj.shtml",
        "key_word": "hot_stock_jj",
        "key_word_chn": "行业掘金",
        "base_url": "http://stock.jrj.com.cn/",
        "end_page": 11,
    }
)
JRJ_STOCK_GU_SHI_NEWS = dict(
    {
        "name": "jrj_stock_gu_shi_news_spider",
        "start_url": "http://stock.jrj.com.cn/list/stockgszx.shtml",
        "key_word": "stock_news",
        "key_word_chn": "股市资讯",
        "base_url": "http://stock.jrj.com.cn/",
        "end_page": 11,
    }
)
JRJ_STOCK_ZHANG_TING_PREDICT = dict(
    {
        "name": "jrj_stock_zhang_ting_predict_spider",
        "start_url": "http://stock.jrj.com.cn/list/ztbyc.shtml",
        "key_word": "stock_zhang_ting",
        "key_word_chn": "涨停板预测",
        "base_url": "http://stock.jrj.com.cn/",
        "end_page": 11,
    }
)
JRJ_SPIDER_LIST = [
    JRJ_INVEST_SCGC,
    JRJ_STOCK_SSGS,
    JRJ_HOT_STOCK_GNJJ,
    JRJ_STOCK_GU_SHI_NEWS,
    JRJ_STOCK_ZHANG_TING_PREDICT,
]

# NBD NEWS
NBD_STOCK_NEWS_DB = "nbd_news"
NBD_STOCK_IMPORTANT_NEWS = dict(
    {
        "name": "nbd_stock_important_news_spider",
        "start_url": "http://stocks.nbd.com.cn/columns/318",
        "key_word": "stock_important_news",
        "key_word_chn": "重磅推荐",
        "base_url": "http://stocks.nbd.com.cn/",
        "end_page": 20,
    }
)
NBD_STOCK_TREND_A = dict(
    {
        "name": "nbd_stock_trend_a_spider",
        "start_url": "http://stocks.nbd.com.cn/columns/275",
        "key_word": "stock_trend_a",
        "key_word_chn": "A股动态",
        "base_url": "http://stocks.nbd.com.cn/",
        "end_page": 20,
    }
)
NBD_DAO_DA_INVEST_LOG = dict(
    {
        "name": "nbd_stock_dao_da_invest_log_spider",
        "start_url": "http://stocks.nbd.com.cn/columns/476",
        "key_word": "stock_dao_da_invest",
        "key_word_chn": "道达投资手记",
        "base_url": "http://stocks.nbd.com.cn/",
        "end_page": 20,
    }
)
NBD_VOLCANO_FORTUNE_NEWS = dict(
    {
        "name": "nbd_stock_volcano_fortune_news_spider",
        "start_url": "http://stocks.nbd.com.cn/columns/800",
        "key_word": "stock_volcano_fortune",
        "key_word_chn": "火山财富",
        "base_url": "http://stocks.nbd.com.cn/",
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


EAST_MONEY_NEWS_DB = "east_money_news"
EAST_MONEY_A_STOCK_NEWS = dict(
    {
        "name": "east_money_cn_stock_company_news_spider",
        "start_url": "http://finance.eastmoney.com/a/cssgs.html",
        "key_word": "stock_cn_company_news",
        "key_word_chn": "A股公司",
        "base_url": "http://finance.eastmoney.com/",
        "end_page": 26,
    }
)
EAST_MONEY_A_MARKET_NEWS = dict(
    {
        "name": "east_money_cn_market_data_news_spider",
        "start_url": "http://stock.eastmoney.com/a/cscsj.html",
        "key_word": "cn_market_data_news",
        "key_word_chn": "市场数据",
        "base_url": "http://finance.eastmoney.com/",
        "end_page": 26,
    }
)
EAST_MONEY_DEEP_INVESTIGATE_NEWS = dict(
    {
        "name": "east_money_cn_deep_investigate_news_spider",
        "start_url": "http://finance.eastmoney.com/a/czsdc.html",
        "key_word": "cn_stock_deep_investigate_news",
        "key_word_chn": "纵深调查",
        "base_url": "http://finance.eastmoney.com/",
        "end_page": 26,
    }
)
EAST_MONEY_INDUSTRY_DEEP_REVIEW_NEWS = dict(
    {
        "name": "east_money_cn_industry_deep_review_news_spider",
        "start_url": "http://finance.eastmoney.com/a/ccyts.html",
        "key_word": "cn_industry_deep_review_news",
        "key_word_chn": "产业透视",
        "base_url": "http://finance.eastmoney.com/",
        "end_page": 26,
    }
)
EAST_MONEY_STOCK_OPINION_NEWS = dict(
    {
        "name": "east_money_cn_stock_opinion_news_spider",
        "start_url": "http://finance.eastmoney.com/a/cgspl.html",
        "key_word": "cn_stock_opinion_news",
        "key_word_chn": "股市评论",
        "base_url": "http://finance.eastmoney.com/",
        "end_page": 26,
    }
)
EAST_MONEY_BUSINESS_NEWS = dict(
    {
        "name": "east_money_cn_business_news_spider",
        "start_url": "http://biz.eastmoney.com/a/csyzx.html",
        "key_word": "cn_business_news",
        "key_word_chn": "商业资讯",
        "base_url": "http://finance.eastmoney.com/",
        "end_page": 26,
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
        "start_url": "https://company.cnstock.com/company/scp_gsxw",
        "key_word": "stock_company_news",
        "key_word_chn": "公司聚集",
        "base_url": "https://company.cnstock.com/",
        "end_page": 100,
    }
)
SHANG_HAI_STOCK_ANNOUNCEMENT_NEWS = dict(
    {
        "name": "shanghai_stock_company_announcement_spider",
        "start_url": "http://ggjd.cnstock.com/company/scp_ggjd/tjd_bbdj",
        "key_word": "stock_announcement_news",
        "key_word_chn": "公告解读",
        "base_url": "http://ggjd.cnstock.com/",
        "end_page": 100,
    }
)
SHANG_HAI_STOCK_COMPANY_KUAI_XUN_NEWS = dict(
    {
        "name": "shanghai_stock_company_kuai_xun_spider",
        "start_url": "http://ggjd.cnstock.com/company/scp_ggjd/tjd_ggkx",
        "key_word": "stock_kuai_xun_news",
        "key_word_chn": "公告快讯",
        "base_url": "http://ggjd.cnstock.com/",
        "end_page": 100,
    }
)
SHANG_HAI_STOCK_COMPANY_GOOD_NEWS = dict(
    {
        "name": "shanghai_stock_company_very_good_news_spider",
        "start_url": "https://ggjd.cnstock.com/company/scp_ggjd/tjd_sdlh",
        "key_word": "stock_good_news",
        "key_word_chn": "利好公告",
        "base_url": "https://ggjd.cnstock.com/",
        "end_page": 100,
    }
)
SHANG_HAI_STOCK_INDUSTRY_NEWS = dict(
    {
        "name": "shanghai_stock_industry_news_spider",
        "start_url": "https://news.cnstock.com/industry",
        "key_word": "stock_industry_news",
        "key_word_chn": "产业聚焦",
        "base_url": "https://news.cnstock.com/",
        "end_page": 100,
    }
)
SHANG_HAI_SPIDER_LIST = [
    SHANG_HAI_STOCK_COMPANY_NEWS,
    SHANG_HAI_STOCK_ANNOUNCEMENT_NEWS,
    SHANG_HAI_STOCK_COMPANY_KUAI_XUN_NEWS,
    SHANG_HAI_STOCK_COMPANY_GOOD_NEWS,
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
        STCN_NEWS_DB: STCN_SPIDER_LIST,
        SHANG_HAI_STOCK_NEWS_DB: SHANG_HAI_SPIDER_LIST,
        ZHONG_JIN_STOCK_NEWS_DB: ZHONG_JIN_SPIDER_LIST,
        NBD_STOCK_NEWS_DB: NBD_SPIDER_LIST,
    }
)

LATEST_DAY_OR_PAGE_SETTING = 3
