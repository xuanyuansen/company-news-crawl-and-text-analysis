# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
"""
中国证券网：https://www.cnstock.com
公司聚焦：https://company.cnstock.com/company/scp_gsxw
公告解读：https://ggjd.cnstock.com/gglist/search/qmtbbdj
公告快讯：https://ggjd.cnstock.com/gglist/search/ggkx
利好公告：https://ggjd.cnstock.com/company/scp_ggjd/tjd_sdlh
"""
from MarketNewsSpider.BasicSpyder import Spyder

from Utils import utils
from Utils import config

import re
import time
import random
import logging
from bs4 import BeautifulSoup
from selenium import webdriver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)


class CnStockSpyder(Spyder):
    def __init__(self, database_name, collection_name):
        super().__init__(database_name, collection_name)
        self.max_rej_amounts = config.CNSTOCK_MAX_REJECTED_AMOUNTS
        self.record_fail_path = config.RECORD_CNSTOCK_FAILED_URL_TXT_FILE_PATH

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
            if "class" in span.attrs and span["class"] == ["timer"]:
                date = span.text
                break
        for paragraph in part:
            chn_status = utils.count_chn(str(paragraph))
            possible = chn_status[1]
            if possible > self.is_article_prob:
                article += str(paragraph)
        while article.find("<") != -1 and article.find(">") != -1:
            string = article[article.find("<"): article.find(">") + 1]
            article = article.replace(string, "")
        while article.find("\u3000") != -1:
            article = article.replace("\u3000", "")
        article = " ".join(re.split(" +|\n+", article)).strip()

        return [date, article]

    def get_historical_news(self, url, category_chn=None,
                            start_date=None,
                            force_update: bool = False):
        """
        :param url: 爬虫网页
        :param category_chn: 所属类别, 中文字符串, 包括'公司聚焦', '公告解读', '公告快讯', '利好公告'
        :param start_date: 数据库中category_chn类别新闻最近一条数据的时间
        :param force_update: force update
        """
        assert category_chn is not None
        driver = webdriver.Chrome(executable_path=config.CHROME_DRIVER)
        btn_more_text = ""
        crawled_urls_list = self.extract_data(["Url"])[0]
        logging.info("historical data length -> {} ... ".format(len(crawled_urls_list)))
        driver.get(url)

        if start_date is None:
            while btn_more_text != "没有更多":
                more_btn = driver.find_element_by_id("j_more_btn")
                btn_more_text = more_btn.text
                logging.info("1-{}".format(more_btn.text))
                if btn_more_text == "加载更多":
                    more_btn.click()
                    time.sleep(random.random())  # sleep random time less 1s
                elif btn_more_text == "加载中...":
                    time.sleep(random.random() + 2)
                    more_btn = driver.find_element_by_id("j_more_btn")
                    btn_more_text = more_btn.text
                    logging.info("2-{}".format(more_btn.text))
                    if btn_more_text == "加载更多":
                        more_btn.click()
                else:
                    more_btn.click()
                    break
            bs = BeautifulSoup(driver.page_source, "html.parser")
            for li in bs.find_all("li", attrs={"class": ["newslist"]}):
                a = li.find_all("h2")[0].find("a")
                if a["href"] not in crawled_urls_list or force_update:
                    result = self.get_url_info(a["href"], start_date)
                    while not result:
                        terminated = self.fail_scrap(a["href"])
                        if terminated:
                            break
                        self.fail_sleep(a["href"])
                        result = self.get_url_info(a["href"], start_date)
                        # result = self.get_url_info(a["href"])
                    if not result:
                        # 爬取失败的情况
                        logging.info("[FAILED] {} {}".format(a["title"], a["href"]))
                    else:
                        self.process_article(result, a["href"], a.string, start_date, category_chn,
                                             is_real_time=False,
                                             force_update=force_update)
        else:
            # 当start_date不为None时，补充历史数据
            is_click_button = True
            start_get_url_info = False
            tmp_a = None
            while is_click_button:
                bs = BeautifulSoup(driver.page_source, "html.parser")
                for li in bs.find_all("li", attrs={"class": ["newslist"]}):
                    a = li.find_all("h2")[0].find("a")
                    if tmp_a is not None and a["href"] != tmp_a:
                        continue
                    elif tmp_a is not None and a["href"] == tmp_a:
                        start_get_url_info = True
                    if start_get_url_info:
                        date, _ = self.get_url_info(a["href"], "")
                        if date <= start_date:
                            is_click_button = False
                            break
                tmp_a = a["href"]
                if is_click_button:
                    more_btn = driver.find_element_by_id("j_more_btn")
                    more_btn.click()

            # 从一开始那条新闻到tmp_a都是新增新闻，不包括tmp_a
            bs = BeautifulSoup(driver.page_source, "html.parser")
            for li in bs.find_all("li", attrs={"class": ["newslist"]}):
                a = li.find_all("h2")[0].find("a")
                if a["href"] != tmp_a:
                    result = self.get_url_info(a["href"], "")
                    while not result:
                        terminated = self.fail_scrap(a["href"])
                        if terminated:
                            break
                        self.fail_sleep(a["href"])
                        result = self.get_url_info(a["href"], start_date)

                    if not result:
                        # 爬取失败的情况
                        logging.info("[FAILED] {} {}".format(a["title"], a["href"]))
                    else:
                        self.process_article(result, a["href"], a.string,
                                             start_date,
                                             category_chn,
                                             is_real_time=False,
                                             force_update=force_update)
                else:
                    break
        driver.quit()

    def get_realtime_news(self, url, category_chn=None, interval=60):
        logging.info(
            "start real-time crawling of URL -> {}, request every {} secs ... ".format(
                url, interval
            )
        )
        assert category_chn is not None

        # TODO: 由于cnstock爬取的数据量并不大，这里暂时是抽取历史所有数据进行去重，之后会修改去重策略
        crawled_urls = self.db_obj.get_data(self.db_name, self.col_name, keys=["Url"])[
            "Url"
        ].to_list()

        logging.info("crawled_urls size {0}".format(len(crawled_urls)))

        while True:
            # 每隔一定时间轮询该网址
            bs = utils.html_parser(url)
            for li in bs.find_all("li", attrs={"class": ["newslist"]}):
                a = li.find_all("h2")[0].find("a")
                if a["href"] not in crawled_urls:  # latest_3_days_crawled_href
                    result = self.get_url_info(a["href"], "")
                    while not result:
                        terminated = self.fail_scrap(a["href"])
                        if terminated:
                            break
                        self.fail_sleep(a["href"])
                        result = self.get_url_info(a["href"], "")

                    if not result:
                        # 爬取失败的情况
                        logging.info("[FAILED] {} {}".format(a["title"], a["href"]))
                    else:
                        # 有返回但是article为null的情况
                        date, article = result
                        self.process_article(result, a["href"], a.string, date, category_chn, True)
                        if article != "":
                            crawled_urls.append(a["href"])
            logging.info("sleep {} secs then request {} again ... ".format(interval, url))
            time.sleep(interval)
