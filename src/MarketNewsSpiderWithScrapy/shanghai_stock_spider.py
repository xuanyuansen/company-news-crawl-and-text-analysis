# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
from bs4 import BeautifulSoup
from scrapy import Request
from MarketNewsSpiderWithScrapy.BaseSpider import BaseSpider
from selenium import webdriver
import time
import random

from Utils import config


class ShanghaiStockSpider(BaseSpider):
    def __init__(
        self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 20
    ):
        super().__init__(name, key_word, key_word_chn, start_url, base_url, end_page)

    def start_requests(self):
        start_url = getattr(self, "start_url")
        driver = webdriver.Chrome(executable_path=config.CHROME_DRIVER)
        btn_more_text = ""
        driver.get(start_url)
        page_cnt = 0
        while btn_more_text != "没有更多" and page_cnt < self.end_page:
            page_cnt += 1
            more_btn = driver.find_element_by_id("j_more_btn")
            btn_more_text = more_btn.text
            self.logger.info("1-{}".format(more_btn.text))
            if btn_more_text == "加载更多":
                more_btn.click()
                time.sleep(random.random() + 1)  # sleep random time less 1s
            elif btn_more_text == "加载中...":
                time.sleep(random.random() + 2)
                more_btn = driver.find_element_by_id("j_more_btn")
                btn_more_text = more_btn.text
                self.logger.info("2-{}".format(more_btn.text))
                if btn_more_text == "加载更多":
                    more_btn.click()
            else:
                more_btn.click()
                break
        bs = BeautifulSoup(driver.page_source, "html.parser")

        bs_list = bs.find_all("li", class_="newslist")
        self.logger.info(
            "start parse, bs list len is {0} {1}".format(len(bs_list), type(bs_list))
        )
        for li in bs_list:
            a = (li.find_all("h2")[0]).find("a")
            desc = li.find_all("p", class_="des")[0]
            # logging.info('a {0}, desc {1}'.format(a, desc))
            if a.get("href") is not None:
                sub_url = a["href"]
                title = str(a.text).strip()
                sub_title = str(desc.text).strip()
                # logging.info('sub url {0} sub title {1} \n {2}'.format(sub_url, title, sub_title))
                yield Request(
                    sub_url,
                    callback=self.parse,
                    meta={"title": "{0}\n{1}".format(title, sub_title)},
                )
        pass

    def parse(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        content = bs.find_all("div", attrs={"id": ["qmt_content_div"]})
        span = bs.find_all("span", class_="timer")[0]
        date = str(span.text)
        response.meta.update({"date_time": date})
        yield self.from_paragraphs_to_item(content, response)
        pass

    pass
