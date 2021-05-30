import logging
import os

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
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
    os.environ["SCRAPY_SETTINGS_MODULE"] = f"settings"
    settings = get_project_settings()
    _process = CrawlerProcess(settings)

    EAST_MONEY = [
        element.update({"end_page": 5}) for element in config.EAST_MONEY_SPIDER_LIST
    ]

    JRJ_NEWS = [element.update({"end_page": 5}) for element in config.JRJ_SPIDER_LIST]

    NET_EASE = [
        element.update({"end_page": 5}) for element in config.NET_EASE_SPIDER_LIST
    ]

    STCN_EASE = [element.update({"end_page": 5}) for element in config.STCN_SPIDER_LIST]

    SHANG_HAI = [
        element.update({"end_page": 5}) for element in config.SHANG_HAI_SPIDER_LIST
    ]

    NBD_NEWS = [element.update({"end_page": 5}) for element in config.NBD_SPIDER_LIST]

    ZHONG_JIN = [
        element.update({"end_page": 15}) for element in config.ZHONG_JIN_SPIDER_LIST
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

    #
    start_date_time = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    logging.info("start time is {}".format(start_date_time))
    gdb = GenStockNewsDB(force_update_score_using_model=True, generate_report=True)
    report_list_of_dict = []
    for db_name, collection_list in config.ALL_SPIDER_LIST_OF_DICT.items():
        for col in collection_list:
            gdb.get_all_news_about_specific_stock(
                db_name,
                col.get("name").replace("spider", "data"),
                start_date=start_date_time,
            )
            one_col_report_dict = dict()
            # {
            #   'XXXX_name': { 'news': list(news_list), '利好': 111, '利空':222}
            # }
            report_dict_list = gdb.get_report(
                db_name, col.get("name").replace("spider", "data")
            )
            if report_dict_list is None:
                logging.warning("no data found, continue")
                continue

            for element in report_dict_list:
                # logging.info('element is {} {}'.format(type(element), element))
                if one_col_report_dict.get(element.get("Name")) is None:
                    _value = [element]
                    one_col_report_dict[element.get("Name")] = dict(
                        {"news": _value, element.get("Label"): 1}
                    )
                else:
                    logging.warning(one_col_report_dict)
                    raw_news = one_col_report_dict.get(element.get("Name")).get("news")
                    raw_news.append(element)
                    one_col_report_dict[element.get("Name")] = (
                        dict(
                            {
                                "news": raw_news,
                                "利好": get_or_else(
                                    one_col_report_dict.get(element.get("Name")),
                                    "利好",
                                )
                                + 1,
                                "利空": get_or_else(
                                    one_col_report_dict.get(element.get("Name")),
                                    "利空",
                                ),
                            }
                        )
                        if element.get("Label") == "利好"
                        else dict(
                            {
                                "news": raw_news,
                                "利好": get_or_else(
                                    one_col_report_dict[element.get("Name")], "利好"
                                ),
                                "利空": get_or_else(
                                    one_col_report_dict[element.get("Name")], "利空"
                                )
                                + 1,
                            }
                        )
                    )

            report_list_of_dict.append(one_col_report_dict)
            logging.info(
                "{0} : {1}\n insert data done, data cnt is {2}".format(
                    db_name, col, len(one_col_report_dict)
                )
            )
        # break
    logging.info("report list cnt is {}".format(len(report_list_of_dict)))
    whole_report_dict = dict()
    # logging.info(report_list_of_dict)
    for element in report_list_of_dict:
        logging.info(element)
        for k, v in element.items():
            # logging.info(k, v)
            if whole_report_dict.get(k) is None:
                whole_report_dict[k] = v
            else:
                whole_report_dict[k] = dict(
                    {
                        "news": whole_report_dict.get(k).get("news") + v.get("news"),
                        "利好": get_or_else(whole_report_dict.get(k), "利好")
                        + get_or_else(v, "利好"),
                        "利空": get_or_else(whole_report_dict.get(k), "利空")
                        + get_or_else(v, "利空"),
                    }
                )

    whole_report_dict_sorted = dict(
        sorted(
            whole_report_dict.items(),
            key=lambda item: item[1].get("利好")
            if item[1].get("利好") is not None
            else -1 * item[1].get("利空"),
            reverse=True,
        )
    )

    title_list = []

    temp_list = {}
    for k, v in whole_report_dict_sorted.items():
        title_list.append("{},利好:{},利空:{}".format(k, v.get("利好"), v.get("利空")))

        content_list = [
            "Title:{}\nArticle:{}".format(ele.get("Title"), ele.get("Article"))
            for ele in v.get("news")
        ]
        for content in content_list:
            if temp_list.get(content) is None:
                temp_list[content] = [k]
            else:
                temp_list[content] = temp_list[content] + [k]
    logging.info(len(whole_report_dict_sorted))
    utils.send_mail(
        ", ".join([ele for ele in title_list]),
        "\n\n\n".join(
            [
                "{}:\n {}".format(",".join(code), content)
                for content, code in temp_list.items()
            ]
        ),
    )
    pass
