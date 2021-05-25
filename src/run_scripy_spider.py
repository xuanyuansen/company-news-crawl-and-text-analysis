import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from SpiderWithScrapy.stcn_spider import StcnSpider

if __name__ == '__main__':
    os.environ['SCRAPY_SETTINGS_MODULE'] = f'settings'
    settings = get_project_settings()
    process = CrawlerProcess(settings)

    process.crawl(StcnSpider)
    # the script will block here until the crawling is finished
    process.start()

    pass

