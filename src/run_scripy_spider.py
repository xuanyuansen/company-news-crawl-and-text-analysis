import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from SpiderWithScrapy.east_money_spider import EastMoneySpider
from SpiderWithScrapy.net_ease_spider import NetEaseSpider
from SpiderWithScrapy.shanghai_stock_spider import ShanghaiStockSpider
from SpiderWithScrapy.stcn_spider import StcnSpider
from SpiderWithScrapy.jrj_spider import JrjSpider
from SpiderWithScrapy.nbd_spider import NBDSpider
from SpiderWithScrapy.zhong_jin_spider import ZhongJinStockSpider
from Utils import config


def add_stcn_spider(process: CrawlerProcess):
    # 麻烦一些，格式不一样
    # https://news.stcn.com/sd/index_1.html 深度
    process.crawl(StcnSpider, **config.STCN_DEEP_NEWS)

    # https://company.stcn.com/index_2.html 公司
    process.crawl(StcnSpider, **config.STCN_COMPANY_TRENDS)
    process.crawl(StcnSpider, **config.STCN_COMPANY_NEWS)

    # https://kuaixun.stcn.com/egs/index.html 股市
    process.crawl(StcnSpider, **config.STCN_KX_EGS)

    # https://kuaixun.stcn.com/yb/index_1.html 研报
    process.crawl(StcnSpider, **config.STCN_KX_REPORT)

    # https://data.stcn.com/djsj/index_17.html 独家数据
    process.crawl(StcnSpider, **config.STCN_DJSJ)

    # https://stock.stcn.com/djjd/index_1.html 独家解读
    process.crawl(StcnSpider, **config.STCN_DJJD)

    # https://finance.stcn.com/index_2.html 机构
    process.crawl(StcnSpider, **config.STCN_JIGOU)
    pass


def add_jrj_spider(process: CrawlerProcess):
    # http://stock.jrj.com.cn/invest/scgc.shtml 市场分析
    # process.crawl(JrjSpider, **config.JRJ_INVEST_SCGC)
    # http://stock.jrj.com.cn/list/stockssgs.shtml 上市公司
    # process.crawl(JrjSpider, **config.JRJ_STOCK_SSGS)
    # http://stock.jrj.com.cn/hotstock/gnjj.shtml 行业掘金
    # process.crawl(JrjSpider, **config.JRJ_HOT_STOCK_GNJJ)
    # http://stock.jrj.com.cn/list/stockgszx.shtml 股市资讯
    # process.crawl(JrjSpider, **config.JRJ_STOCK_GU_SHI_NEWS)
    # http://stock.jrj.com.cn/list/ztbyc.shtml 涨停板预测
    process.crawl(JrjSpider, **config.JRJ_STOCK_ZHANG_TING_PREDICT)

    pass


def add_nbd_spider(process: CrawlerProcess):
    # http://stocks.nbd.com.cn/columns/318  重磅推荐
    # process.crawl(NBDSpider, **config.NBD_STOCK_IMPORTANT_NEWS)
    # http://stocks.nbd.com.cn/columns/275 A股动态
    # process.crawl(NBDSpider, **config.NBD_STOCK_TREND_A)
    # http://stocks.nbd.com.cn/columns/476
    # process.crawl(NBDSpider, **config.NBD_DAO_DA_INVEST_LOG)
    # http://stocks.nbd.com.cn/columns/800  每经网首页>券商>火山财富
    process.crawl(NBDSpider, **config.NBD_VOLCANO_FORTUNE_NEWS)
    pass


def add_net_ease_spider(process: CrawlerProcess):
    # http://money.163.com/special/00251LR5/gptj.html 个股资讯
    # process.crawl(NetEaseSpider, **config.NET_EASE_STOCK_NEWS)
    process.crawl(NetEaseSpider, **config.NET_EASE_MARKET_NEWS)
    pass


def add_east_money_spider(process: CrawlerProcess):
    # http://finance.eastmoney.com/a/cssgs.html
    process.crawl(EastMoneySpider, **config.EAST_MONEY_A_STOCK_NEWS)
    process.crawl(EastMoneySpider, **config.EAST_MONEY_A_MARKET_NEWS)
    process.crawl(EastMoneySpider, **config.EAST_MONEY_DEEP_INVESTIGATE_NEWS)
    process.crawl(EastMoneySpider, **config.EAST_MONEY_INDUSTRY_DEEP_REVIEW_NEWS)
    process.crawl(EastMoneySpider, **config.EAST_MONEY_STOCK_OPINION_NEWS)
    process.crawl(EastMoneySpider, **config.EAST_MONEY_BUSINESS_NEWS)

    pass


def add_shang_hai_stock_spider(process: CrawlerProcess):
    # process.crawl(ShanghaiStockSpider, **config.SHANG_HAI_STOCK_COMPANY_NEWS)
    # process.crawl(ShanghaiStockSpider, **config.SHANG_HAI_STOCK_COMPANY_KUAI_XUN_NEWS)
    # process.crawl(ShanghaiStockSpider, **config.SHANG_HAI_STOCK_ANNOUNCEMENT_NEWS)
    # process.crawl(ShanghaiStockSpider, **config.SHANG_HAI_STOCK_COMPANY_GOOD_NEWS)
    process.crawl(ShanghaiStockSpider, **config.SHANG_HAI_STOCK_INDUSTRY_NEWS)
    pass


def add_zhong_jin_stock_spider(process: CrawlerProcess):
    # process.crawl(ShanghaiStockSpider, **config.SHANG_HAI_STOCK_COMPANY_NEWS)
    # process.crawl(ShanghaiStockSpider, **config.SHANG_HAI_STOCK_COMPANY_KUAI_XUN_NEWS)
    # process.crawl(ShanghaiStockSpider, **config.SHANG_HAI_STOCK_ANNOUNCEMENT_NEWS)
    # process.crawl(ShanghaiStockSpider, **config.SHANG_HAI_STOCK_COMPANY_GOOD_NEWS)
    process.crawl(ZhongJinStockSpider, **config.ZHONG_JIN_STOCK_NEWS)
    pass


if __name__ == "__main__":
    os.environ["SCRAPY_SETTINGS_MODULE"] = f"settings"
    settings = get_project_settings()
    _process = CrawlerProcess(settings)

    # add_stcn_spider(_process)
    # add_jrj_spider(_process)
    # add_nbd_spider(_process)
    # add_net_ease_spider(_process)
    # add_east_money_spider(_process)
    # add_shang_hai_stock_spider(_process)
    add_zhong_jin_stock_spider(_process)
    _process.start()

    pass
