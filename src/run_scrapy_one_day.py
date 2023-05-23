import json
import logging
import os

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from xlsxwriter import Workbook
import argparse
from Utils.utils import get_or_else
from MongoDbComTools.BuildStockNewsDb import GenStockNewsDB
from MarketNewsSpiderWithScrapy.east_money_spider import EastMoneySpider
from MarketNewsSpiderWithScrapy.net_ease_spider import NetEaseSpider
from MarketNewsSpiderWithScrapy.shanghai_stock_spider import ShanghaiStockSpider
from MarketNewsSpiderWithScrapy.stcn_spider import StcnSpider
from MarketNewsSpiderWithScrapy.jrj_spider import JrjSpider
from MarketNewsSpiderWithScrapy.nbd_spider import NBDSpider
from MarketNewsSpiderWithScrapy.zhong_jin_spider import ZhongJinStockSpider
from Utils import config, utils
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)

# 每天运行一次,爬取最新的信息,然后形成最新消息的汇总.统计报告发出来到邮箱.按照消息数量由多到少排序.
# 再把这些消息插入到各自新闻的db.同时生成报告
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--spider", help="run spider")
    parser.add_argument("-r", "--report", help="run report")
    args = parser.parse_args()
    if args.spider:
        logging.info("page number is {}".format(int(args.spider)))
        os.environ["SCRAPY_SETTINGS_MODULE"] = f"settings"
        settings = get_project_settings()
        _process = CrawlerProcess(settings)

        EAST_MONEY = [
            element.update({"end_page": int(args.spider)})
            for element in config.EAST_MONEY_SPIDER_LIST
        ]

        JRJ_NEWS = [
            element.update({"end_page": int(args.spider)})
            for element in config.JRJ_SPIDER_LIST
        ]

        NET_EASE = [
            element.update({"end_page": int(args.spider)})
            for element in config.NET_EASE_SPIDER_LIST
        ]

        STCN_EASE = [
            element.update({"end_page": int(args.spider)})
            for element in config.STCN_SPIDER_LIST
        ]

        SHANG_HAI = [
            element.update({"end_page": int(args.spider)})
            for element in config.SHANG_HAI_SPIDER_LIST
        ]

        NBD_NEWS = [
            element.update({"end_page": int(args.spider)})
            for element in config.NBD_SPIDER_LIST
        ]

        ZHONG_JIN = [
            element.update({"end_page": 2 * int(args.spider)})
            for element in config.ZHONG_JIN_SPIDER_LIST
        ]

        for spider_config in config.EAST_MONEY_SPIDER_LIST:
            logging.info(spider_config)
            _process.crawl(EastMoneySpider, **spider_config)

        for spider_config in config.JRJ_SPIDER_LIST:
            _process.crawl(JrjSpider, **spider_config)

        for spider_config in config.NET_EASE_SPIDER_LIST:
            _process.crawl(NetEaseSpider, **spider_config)

        for spider_config in config.STCN_SPIDER_LIST:
            _process.crawl(StcnSpider, **spider_config)

        for spider_config in config.SHANG_HAI_SPIDER_LIST:
            _process.crawl(ShanghaiStockSpider, **spider_config)

        for spider_config in config.NBD_SPIDER_LIST:
            _process.crawl(NBDSpider, **spider_config)

        for spider_config in config.ZHONG_JIN_SPIDER_LIST:
            _process.crawl(ZhongJinStockSpider, **spider_config)

        _process.start()

    if args.report:
        logging.info("report of {} days".format(int(args.report)))
        start_date_time = (datetime.now() - timedelta(days=int(args.report))).strftime(
            "%Y-%m-%d"
        )
        logging.info("start time is {}".format(start_date_time))
        gdb = GenStockNewsDB(force_update_score_using_model=True, generate_report=True)
        report_list_of_dict = []
        collection_cnt = 0
        for db_name, collection_list in config.ALL_SPIDER_LIST_OF_DICT.items():
            print("db  name {}".format(db_name))
            for col in collection_list:
                print("col  name {}".format(col))
                collection_cnt += 1
                gdb.get_all_news_about_specific_stock(
                    db_name,
                    col.get("name").replace("spider", "data"),
                    start_date=start_date_time,
                )

        report_list_of_dict = gdb.get_report_raw_version()

        file_name = "./info/news_{}.xlsx".format(datetime.now().strftime("%Y-%m-%d"))
        mail_file_name = "news_{}.xlsx".format(datetime.now().strftime("%Y-%m-%d"))

        ordered_list = [
            "Code",
            "Title",
            "Article",
            "Date",
            "Category",
            "Label",
            "Score",
            "Url",
        ]
        # list object calls by index but dict object calls items randomly
        wb = Workbook(file_name)
        ws = wb.add_worksheet("News")  # or leave it blank, default name is "Sheet 1"
        # 表头
        first_row = 0
        for header in ordered_list:
            col = ordered_list.index(header)  # we are keeping order.
            ws.write(
                first_row, col, header
            )  # we have written first row which is the header of worksheet also.

        row = 1
        for news in report_list_of_dict:
            ws.write(row, 0, news.get("RelatedStockCodes"))
            idx = 1
            for ele in ordered_list[1:]:
                ws.write(row, idx, news.get(ele))
                idx += 1
            row += 1  # enter the next row
        # 先不关闭，把股票热度写入第二张表格
        # wb.close()

        title_dict = dict()
        for ele_dict in report_list_of_dict:
            related_codes = json.loads(ele_dict.get("RelatedStockCodes"))
            _label = ele_dict.get("Label")
            for k, _code in related_codes.items():
                if title_dict.get(k) is None:
                    title_dict[k] = {_label: 1}
                    title_dict[k] = {"code": _code}
                else:
                    title_dict[k].update(
                        {_label: get_or_else(title_dict[k], _label) + 1}
                    )

        title_dict_sort = sorted(
            title_dict.items(),
            key=lambda item: get_or_else(item[1], "利好"),
            reverse=True,
        )

        hot_cnt_sheet = wb.add_worksheet("GoodOrBad")
        # 写入表头
        hot_cnt_sheet.write(0, 0, "股票名字")
        hot_cnt_sheet.write(0, 1, "利好")
        hot_cnt_sheet.write(0, 2, "利空")
        hot_cnt_sheet.write(0, 3, "股票代码")

        row_idx = 1
        for element in title_dict_sort:
            hot_cnt_sheet.write(row_idx, 0, element[0])
            hot_cnt_sheet.write(row_idx, 1, get_or_else(element[1], "利好"))
            hot_cnt_sheet.write(row_idx, 2, get_or_else(element[1], "利空"))
            hot_cnt_sheet.write(row_idx, 3, get_or_else(element[1], "code"))
            row_idx += 1

        # 将top20的相关新闻列出来，写入表格里面
        top_related_cnt = 30 if len(title_dict_sort) >= 30 else len(title_dict_sort)
        for _idx in range(0, top_related_cnt):
            _stock_name = title_dict_sort[_idx][0]
            _stock_code = title_dict_sort[_idx][1].get("code")
            current_sheet = wb.add_worksheet("{}_{}".format(_stock_name, _stock_code))
            current_sheet.write(0, 0, "Articles")
            all_news_list = gdb.get_all_news_of_one_stock(_stock_code, start_date_time)
            _current_row = 1
            for _news in all_news_list:
                current_sheet.write(_current_row, 0, _news)
                _current_row += 1

        wb.close()

        # utils.send_mail(
        #     topic="news_{}".format(datetime.now().strftime("%Y-%m-%d")),
        #     content=str(title_dict_sort),
        #     attach_name=mail_file_name,
        #     _file_name=file_name,
        # )

    pass
