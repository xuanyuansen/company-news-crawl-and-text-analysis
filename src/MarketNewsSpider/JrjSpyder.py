# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
"""
金融界：http://www.jrj.com.cn
股票频道全部新闻：http://stock.jrj.com.cn/xwk/202012/20201203_1.shtml
"""
from MarketNewsSpider.BasicSpyder import Spyder

from Utils import utils
from Utils import config
import time
import json
import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)


class JrjSpyder(Spyder):
    def __init__(self, database_name, collection_name):
        super().__init__(database_name, collection_name)
        self.max_rej_amounts = config.JRJ_MAX_REJECTED_AMOUNTS
        self.record_fail_path = config.RECORD_JRJ_FAILED_URL_TXT_FILE_PATH

    def get_url_info(self, url, specific_date):
        try:
            bs = utils.html_parser(url)
        except Exception as e:
            logging.warning("html parse fail {0}".format(e))
            return False
        date = ""
        for span in bs.find_all("span"):
            if span.contents[0] == "jrj_final_date_start":
                date = span.text.replace("\r", "").replace("\n", "")
                break
        if date == "":
            date = specific_date
        article = ""
        for p in bs.find_all("p"):
            if (
                not p.find_all("jrj_final_daohang_start")
                and p.attrs == {}
                and not p.find_all("input")
                and not p.find_all("a", attrs={"class": "red"})
                and not p.find_all("i")
                and not p.find_all("span")
            ):
                article += (
                    p.text.replace("\r", "").replace("\n", "").replace("\u3000", "")
                )

        return [date, article]

    def from_url_2_a_list(self, url, date, num):
        _url = "{}/{}/{}_{}.shtml".format(
            url, date.replace("-", "")[0:6], date.replace("-", ""), str(num)
        )
        bs = utils.html_parser(_url)
        a_list = bs.find_all("a")
        return a_list

    def get_historical_news(self, url, start_date=None, end_date=None):
        crawled_urls_list = []
        if end_date is None:
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")

        if start_date is None:
            # 如果start_date是None，则从历史数据库最新的日期补充爬取到最新日期
            # e.g. history_latest_date_str -> "2020-12-08"
            #      history_latest_date_dt -> datetime.date(2020, 12, 08)
            #      start_date -> "2020-12-09"
            history_latest_date_list = self.db_obj.get_data(
                self.db_name, self.col_name, keys=["Date"]
            )["Date"].to_list()
            if len(history_latest_date_list) != 0:
                history_latest_date_str = max(history_latest_date_list).split(" ")[0]
                history_latest_date_dt = datetime.datetime.strptime(
                    history_latest_date_str, "%Y-%m-%d"
                ).date()
                offset = datetime.timedelta(days=1)
                start_date = (history_latest_date_dt + offset).strftime("%Y-%m-%d")
            else:
                start_date = config.JRJ_REQUEST_DEFAULT_DATE

        dates_list = utils.get_date_list_from_range(start_date, end_date)
        dates_separated_into_ranges_list = utils.gen_dates_list(
            dates_list, config.JRJ_DATE_RANGE
        )

        for dates_range in dates_separated_into_ranges_list:
            for date in dates_range:
                first_url = "{}/{}/{}_1.shtml".format(
                    url, date.replace("-", "")[0:6], date.replace("-", "")
                )
                max_pages_num = utils.search_max_pages_num(first_url, date)
                for num in range(1, max_pages_num + 1):
                    a_list = self.from_url_2_a_list(url, date, num)
                    for a in a_list:
                        if (
                            "href" in a.attrs
                            and a.string
                            and a["href"].find(
                                "/{}/{}/".format(
                                    date.replace("-", "")[:4],
                                    date.replace("-", "")[4:6],
                                )
                            )
                            != -1
                        ):
                            if a["href"] not in crawled_urls_list:
                                # 如果标题不包含"收盘","报于"等字样，即可写入数据库，因为包含这些字样标题的新闻多为机器自动生成
                                if (
                                    a.string.find("收盘") == -1
                                    and a.string.find("报于") == -1
                                    and a.string.find("新三板挂牌上市") == -1
                                ):
                                    result = self.get_url_info(a["href"], date)
                                    while not result:
                                        terminated = self.fail_scrap(a["href"])
                                        if terminated:
                                            break
                                        self.fail_sleep(a["href"])
                                        result = self.get_url_info(a["href"], date)
                                    if not result:
                                        # 爬取失败的情况
                                        logging.info(
                                            "[FAILED] {} {}".format(a.string, a["href"])
                                        )
                                    else:
                                        self.process_article(result, a["href"], a.string, date)

                                    self.terminated_amount = 0  # 爬取结束后重置该参数
                                else:
                                    logging.info("[QUIT] {}".format(a.string))

    def get_realtime_news(self, interval=60):
        # crawled_urls_list = []
        is_change_date = False
        last_date = datetime.datetime.now().strftime("%Y-%m-%d")

        while True:
            today_date = datetime.datetime.now().strftime("%Y-%m-%d")
            if today_date != last_date:
                is_change_date = True
                last_date = today_date
            if is_change_date:
                # crawled_urls_list = []
                utils.batch_lpop(
                    self.redis_client,
                    config.CACHE_SAVED_NEWS_JRJ_TODAY_VAR_NAME,
                    self.redis_client.llen(config.CACHE_SAVED_NEWS_JRJ_TODAY_VAR_NAME),
                )
                is_change_date = False
            _url = "{}/{}/{}_1.shtml".format(
                config.WEBSITES_LIST_TO_BE_CRAWLED_JRJ,
                today_date.replace("-", "")[0:6],
                today_date.replace("-", ""),
            )
            max_pages_num = utils.search_max_pages_num(_url, today_date)
            for num in range(1, max_pages_num + 1):
                _url = "{}/{}/{}_{}.shtml".format(
                    config.WEBSITES_LIST_TO_BE_CRAWLED_JRJ,
                    today_date.replace("-", "")[0:6],
                    today_date.replace("-", ""),
                    str(num),
                )
                bs = utils.html_parser(_url)
                a_list = bs.find_all("a")
                for a in a_list:
                    if (
                        "href" in a.attrs
                        and a.string
                        and a["href"].find(
                            "/{}/{}/".format(
                                today_date.replace("-", "")[:4],
                                today_date.replace("-", "")[4:6],
                            )
                        )
                        != -1
                    ):
                        # if a["href"] not in crawled_urls_list:
                        if a["href"] not in self.redis_client.lrange(
                            config.CACHE_SAVED_NEWS_JRJ_TODAY_VAR_NAME, 0, -1
                        ):
                            # 如果标题不包含"收盘","报于"等字样，即可写入数据库，因为包含这些字样标题的新闻多为机器自动生成
                            if (
                                a.string.find("收盘") == -1
                                and a.string.find("报于") == -1
                                and a.string.find("新三板挂牌上市") == -1
                            ):
                                result = self.get_url_info(a["href"], today_date)
                                while not result:
                                    terminated = self.fail_scrap(a["href"])
                                    if terminated:
                                        break
                                    self.fail_sleep(a["href"])
                                    # result = self.get_url_info(a["href"], date)
                                    result = self.get_url_info(a["href"], today_date)
                                if not result:
                                    # 爬取失败的情况
                                    logging.info(
                                        "[FAILED] {} {}".format(a.string, a["href"])
                                    )
                                else:
                                    # 有返回但是article为null的情况
                                    # article_specific_date, article = result
                                    self.process_article(result, a["href"], a.string, today_date, True)
                                self.terminated_amount = 0  # 爬取结束后重置该参数
                            else:
                                logging.info("[QUIT] {}".format(a.string))
                            # crawled_urls_list.append(a["href"])
                            self.redis_client.lpush(
                                config.CACHE_SAVED_NEWS_JRJ_TODAY_VAR_NAME, a["href"]
                            )
            # logging.info("sleep {} secs then request again ... ".format(interval))
            time.sleep(interval)
