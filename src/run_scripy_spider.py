import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from SpiderWithScrapy.stcn_spider import StcnSpider
from Utils import config

if __name__ == '__main__':
    os.environ['SCRAPY_SETTINGS_MODULE'] = f'settings'
    settings = get_project_settings()
    process = CrawlerProcess(settings)

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

    process.start()

    pass
