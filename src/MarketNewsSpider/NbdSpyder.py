# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
"""
每经网：http://www.nbd.com.cn
A股动态：http://stocks.nbd.com.cn/columns/275/page/1
"""
from MarketNewsSpider.BasicSpyder import Spyder
from Utils import utils, config
import re
import time
import logging
import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)


class NbdSpyder(Spyder):
    def __init__(self, database_name, collection_name):
        super().__init__(database_name, collection_name)
        self.max_rej_amounts = config.NBD_MAX_REJECTED_AMOUNTS
        self.record_fail_path = config.RECORD_NBD_FAILED_URL_TXT_FILE_PATH

    def get_url_info(self, url, specific_date):
        try:
            bs = utils.html_parser(url)
        except Exception as e:
            logging.warning("html parse fail {0}".format(e))
            return False
        span_list = bs.find_all("span")
        part = bs.find_all("p")
        article = ""
        date = ""
        for span in span_list:
            if "class" in span.attrs and span.text and span["class"] == ["time"]:
                string = span.text.split()
                for dt in string:
                    if dt.find("-") != -1:
                        date += dt + " "
                    elif dt.find(":") != -1:
                        date += dt
                break
        for paragraph in part:
            chn_status = utils.count_chn(str(paragraph))
            possible = chn_status[1]
            if possible > self.is_article_prob:
                article += str(paragraph)
        while article.find("<") != -1 and article.find(">") != -1:
            string = article[article.find("<") : article.find(">") + 1]
            article = article.replace(string, "")
        while article.find("\u3000") != -1:
            article = article.replace("\u3000", "")
        article = " ".join(re.split(" +|\n+", article)).strip()
        return [date, article]

    @staticmethod
    def condition(aa):
        return "click-statistic" in aa.attrs and aa.string \
                and aa["click-statistic"].find("Article_") != -1 \
                and aa["href"].find("http://www.nbd.com.cn/articles/") != -1

    def get_historical_news(self, start_page=684, force_update: bool = False):
        crawled_urls_list = self.extract_data(["Url"])[0]

        page_urls = [
            "{}/{}".format(config.WEBSITES_LIST_TO_BE_CRAWLED_NBD, page_id)
            for page_id in range(start_page, 0, -1)
        ]
        success = 0
        for page_url in page_urls:
            bs = utils.html_parser(page_url)
            a_list = bs.find_all("a")
            for a in a_list:
                if NbdSpyder.condition(a):
                    if a["href"] not in crawled_urls_list or force_update:
                        result = self.get_url_info(a["href"], "")
                        while not result:
                            # self.terminated_amount += 1
                            terminated = self.fail_scrap(a["href"])
                            if terminated:
                                break
                            self.fail_sleep(a["href"])
                            result = self.get_url_info(a["href"], "")
                            logging.info("in while loop result {0}".format(result))
                        if not result:
                            # 爬取失败的情况
                            logging.info(
                                "[FAILED] {} {}".format(a.string, a["href"])
                            )
                        else:
                            # 有返回但是article为null的情况
                            success += 1
                            self.process_article(result, a["href"], a.string, "")

            logging.info("page_start{0} page_end {1}, success {2}"
                         .format(page_urls[0], page_urls[len(page_urls)-1], success))

    def get_realtime_news(self, interval=60):
        page_url = "{}/1".format(config.WEBSITES_LIST_TO_BE_CRAWLED_NBD)
        logging.info(
            "start real-time crawling of URL -> {}, request every {} secs ... ".format(
                page_url, interval
            )
        )
        # name_code_dict = dict(name_code_df.values)
        # crawled_urls = []
        date_list = self.db_obj.get_data(self.db_name, self.col_name, keys=["Date"])[
            "Date"
        ].to_list()
        latest_date = max(date_list)
        is_change_date = False
        last_date = datetime.datetime.now().strftime("%Y-%m-%d")

        while True:
            today_date = datetime.datetime.now().strftime("%Y-%m-%d")
            if today_date != last_date:
                is_change_date = True
                last_date = today_date
            # 新的一天开始清除所有数据
            if is_change_date:
                # crawled_urls_list = []
                utils.batch_lpop(
                    self.redis_client,
                    config.CACHE_SAVED_NEWS_NBD_TODAY_VAR_NAME,
                    self.redis_client.llen(config.CACHE_SAVED_NEWS_NBD_TODAY_VAR_NAME),
                )
                is_change_date = False

            bs = utils.html_parser(page_url)
            a_list = bs.find_all("a")
            for a in a_list:
                if NbdSpyder.condition(a):
                    # if a["href"] not in crawled_urls:
                    if a["href"] not in self.redis_client.lrange(
                        config.CACHE_SAVED_NEWS_NBD_TODAY_VAR_NAME, 0, -1
                    ):
                        result = self.get_url_info(a["href"], "")
                        while not result:
                            terminated = self.fail_scrap(a["href"])
                            if terminated:
                                break
                            self.fail_sleep(a["href"])
                            result = self.get_url_info(a["href"], "")
                        if not result:
                            # 爬取失败的情况
                            logging.info("[FAILED] {} {}".format(a.string, a["href"]))
                        else:
                            # 有返回但是article为null的情况
                            date, article = result
                            if date > latest_date:
                                self.process_article(result, a["href"], a.string, date, None, True)
                                if article != "":
                                    # crawled_urls.append(a["href"])
                                    self.redis_client.lpush(
                                        config.CACHE_SAVED_NEWS_NBD_TODAY_VAR_NAME,
                                        a["href"],
                                    )
            logging.info("sleep {} secs then request again ... ".format(interval))
            time.sleep(interval)
