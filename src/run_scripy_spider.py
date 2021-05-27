import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from SpiderWithScrapy.stcn_spider import StcnSpider
from SpiderWithScrapy.jrj_spider import JrjSpider
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


if __name__ == '__main__':
    os.environ['SCRAPY_SETTINGS_MODULE'] = f'settings'
    settings = get_project_settings()
    _process = CrawlerProcess(settings)

    add_stcn_spider(_process)
    add_jrj_spider(_process)

    _process.start()

    pass
