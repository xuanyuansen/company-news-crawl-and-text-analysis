import json
import logging
import os

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from xlsxwriter import Workbook
import argparse
from Utils.utils import get_or_else
from ComTools.BuildStockNewsDb import GenStockNewsDB
from SpiderWithScrapy.east_money_spider import EastMoneySpider
from SpiderWithScrapy.net_ease_spider import NetEaseSpider
from SpiderWithScrapy.shanghai_stock_spider import ShanghaiStockSpider
from SpiderWithScrapy.stcn_spider import StcnSpider
from SpiderWithScrapy.jrj_spider import JrjSpider
from SpiderWithScrapy.nbd_spider import NBDSpider
from SpiderWithScrapy.zhong_jin_spider import ZhongJinStockSpider
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
    parser.add_argument('-s', '--spider', help='run spider')
    parser.add_argument('-r', '--report', help='run report')
    args = parser.parse_args()
    if args.spider:
        logging.info('page number is {}'.format(int(args.spider)))
        os.environ["SCRAPY_SETTINGS_MODULE"] = f"settings"
        settings = get_project_settings()
        _process = CrawlerProcess(settings)

        EAST_MONEY = [
            element.update({"end_page": int(args.spider)}) for element in config.EAST_MONEY_SPIDER_LIST
        ]

        JRJ_NEWS = [element.update({"end_page": int(args.spider)}) for element in config.JRJ_SPIDER_LIST]

        NET_EASE = [
            element.update({"end_page": int(args.spider)}) for element in config.NET_EASE_SPIDER_LIST
        ]

        STCN_EASE = [element.update({"end_page": int(args.spider)}) for element in config.STCN_SPIDER_LIST]

        SHANG_HAI = [
            element.update({"end_page": int(args.spider)}) for element in config.SHANG_HAI_SPIDER_LIST
        ]

        NBD_NEWS = [element.update({"end_page": int(args.spider)}) for element in config.NBD_SPIDER_LIST]

        ZHONG_JIN = [
            element.update({"end_page": 2*int(args.spider)}) for element in config.ZHONG_JIN_SPIDER_LIST
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
        logging.info('report of {} days'.format(int(args.report)))
        start_date_time = (datetime.now() - timedelta(days=int(args.report))).strftime("%Y-%m-%d")
        logging.info("start time is {}".format(start_date_time))
        gdb = GenStockNewsDB(force_update_score_using_model=True, generate_report=True)
        report_list_of_dict = []
        collection_cnt = 0
        for db_name, collection_list in config.ALL_SPIDER_LIST_OF_DICT.items():
            for col in collection_list:
                collection_cnt += 1
                gdb.get_all_news_about_specific_stock(
                    db_name,
                    col.get("name").replace("spider", "data"),
                    start_date=start_date_time,
                )
                # one_col_report_dict = dict()
                # # {
                # #   'XXXX_name': { 'news': list(news_list), '利好': 111, '利空':222}
                # # }
                # report_dict_list = gdb.get_report(
                #     db_name, col.get("name").replace("spider", "data")
                # )
                # if report_dict_list is None:
                #     logging.warning("no data found, continue")
                #     continue
                #
                # for element in report_dict_list:
                #     # logging.info('element is {} {}'.format(type(element), element))
                #     if one_col_report_dict.get(element.get("Name")) is None:
                #         _value = [element]
                #         one_col_report_dict[element.get("Name")] = dict({"news": _value, element.get("Label"): 1})
                #     else:
                #         # logging.warning(one_col_report_dict)
                #         raw_news = one_col_report_dict.get(element.get("Name")).get("news")
                #         raw_news.append(element)
                #         one_col_report_dict[element.get("Name")] = (
                #             dict({
                #                     "news": raw_news,
                #                     "利好": get_or_else(one_col_report_dict.get(element.get("Name")), "利好") + 1,
                #                     "利空": get_or_else(one_col_report_dict.get(element.get("Name")), "利空"),
                #                 })
                #             if element.get("Label") == "利好"
                #             else dict({
                #                     "news": raw_news,
                #                     "利好": get_or_else(one_col_report_dict[element.get("Name")], "利好"),
                #                     "利空": get_or_else(one_col_report_dict[element.get("Name")], "利空") + 1,
                #                 })
                #         )
                #
                # report_list_of_dict.append(one_col_report_dict)
                # logging.info(
                #     "col_cnt: {3}, {0} : {1}\n insert data done, data cnt is {2}".format(
                #         db_name, col, len(one_col_report_dict), collection_cnt
                #     )
                # )
            # break
        # logging.info("report list cnt is {}".format(len(report_list_of_dict)))
        # whole_report_dict = dict()
        # # logging.info(report_list_of_dict)
        # for element in report_list_of_dict:
        #     # logging.info(element)
        #     for k, v in element.items():
        #         # logging.info(k, v)
        #         if whole_report_dict.get(k) is None:
        #             whole_report_dict[k] = v
        #         else:
        #             whole_report_dict[k] = dict({
        #                     "news": whole_report_dict.get(k).get("news") + v.get("news"),
        #                     "利好": get_or_else(whole_report_dict.get(k), "利好") + get_or_else(v, "利好"),
        #                     "利空": get_or_else(whole_report_dict.get(k), "利空") + get_or_else(v, "利空"),
        #                 })
        #
        # whole_report_dict_sorted = dict(
        #     sorted(
        #         whole_report_dict.items(),
        #         key=lambda item: item[1].get("利好")
        #         if item[1].get("利好") is not None
        #         else -1 * item[1].get("利空"),
        #         reverse=True,
        #     )
        # )
        #
        # title_list = []
        #
        # temp_list = {}
        # for k, v in whole_report_dict_sorted.items():
        #     title_list.append("{},利好:{},利空:{}".format(k, v.get("利好"), v.get("利空")))
        #
        #     content_list = [
        #         "{}\t\n{}\t\n{}\t\n{}\t\n{}".format(ele.get("Title"),
        #                                             ele.get("Article"),
        #                                             ele.get("Date"),
        #                                             ele.get("Label"),
        #                                             ele.get("Score"))
        #         for ele in v.get("news")
        #     ]
        #     for content in content_list:
        #         if temp_list.get(content) is None:
        #             temp_list[content] = [k]
        #         else:
        #             temp_list[content] = temp_list[content] + [k]
        # logging.info('all unique news count is '.format(len(whole_report_dict_sorted)))
        report_list_of_dict = gdb.get_report_raw_version()

        file_name = './info/news_{}.xlsx'.format(datetime.now().strftime("%Y-%m-%d"))

        ordered_list = ["Code", "Title", "Article", "Date", 'Category', "Label", "Score", "Url"]
        # list object calls by index but dict object calls items randomly
        wb = Workbook(file_name)
        ws = wb.add_worksheet("News")  # or leave it blank, default name is "Sheet 1"
        # 表头
        first_row = 0
        for header in ordered_list:
            col = ordered_list.index(header)  # we are keeping order.
            ws.write(first_row, col, header)  # we have written first row which is the header of worksheet also.

        row = 1
        for news in report_list_of_dict:
            ws.write(row, 0, news.get('RelatedStockCodes'))
            idx = 1
            for ele in ordered_list[1:]:
                ws.write(row, idx, news.get(ele))
                idx += 1
            row += 1  # enter the next row
        wb.close()
        title_dict = dict()
        for ele_dict in report_list_of_dict:
            related_codes = json.loads(ele_dict.get('RelatedStockCodes'))
            _label = ele_dict.get('Label')
            for k, _ in related_codes.items():
                if title_dict.get(k) is None:
                    title_dict[k] = {_label: 1}
                else:
                    title_dict[k].update({_label: get_or_else(title_dict[k], _label)+1})

        title_dict_sort = sorted(title_dict.items(), key=lambda item: get_or_else(item[1], '利好'), reverse=True)

        utils.send_mail(
            topic='news_{}'.format(datetime.now().strftime("%Y-%m-%d")),
            content=str(title_dict_sort),
            _file_name=file_name
        )

    pass
