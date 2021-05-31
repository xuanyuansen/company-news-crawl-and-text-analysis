from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from selenium import webdriver
from scrapy import Request
from SpiderWithScrapy.BaseSpider import BaseSpider
from Utils import config
import time
import random
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)


class ZhongJinStockSpider(BaseSpider):
    def __init__(
        self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 20
    ):
        super().__init__(name, key_word, key_word_chn, start_url, base_url, end_page)

    # http://stock.cnfol.com/
    def start_requests(self):
        start_url = getattr(self, "start_url")
        driver = webdriver.Chrome(executable_path=config.CHROME_DRIVER)
        btn_more_text = ""
        driver.get(start_url)
        page_cnt = 0
        while btn_more_text != "无更多文章" and page_cnt < self.end_page:
            page_cnt += 1

            time.sleep(random.random() + 1)
            more_btn = driver.find_element_by_xpath("//a[contains(@class, 'loadMore')]")
            btn_more_text = more_btn.text
            logging.info(
                "1-{} \n{} \n{} \n page cnt {}".format(
                    more_btn, more_btn.text, type(more_btn), page_cnt
                )
            )
            if more_btn.text == "正在加载":
                driver.execute_script("arguments[0].focus();", more_btn)
                target_elem = driver.find_element_by_xpath(
                    "//a[contains(@class, 'backBtn')]"
                )
                driver.execute_script("arguments[0].focus();", target_elem)
                # more_btn.click()
                time.sleep(random.random() + 1)  # sleep random time less 1s

        bs = BeautifulSoup(driver.page_source, "html.parser")

        div_list = bs.find_all("ul", class_="TList")
        logging.info(
            "start parse, bs list len is {0} {1} {2}".format(
                type(div_list[0]), len(div_list), type(div_list)
            )
        )
        for li in div_list[0].find_all("li"):
            a = li.find_all("a")[0]
            # desc = li.find_all("p", class_="des")[0]
            # logging.info('a {0}, desc {1}'.format(a, desc))
            if a.get("href") is not None:
                sub_url = a["href"]
                _title = str(a.text).strip()
                _time = li.find_all("span")[0]
                _time = str(_time.text).replace("(", "").replace(")", "").strip()
                if _time.split(' ')[0] > self.day_now:
                    _year = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d').split('-')[0]
                else:
                    _year = datetime.now().strftime('%Y-%m-%d').split('-')[0]
                logging.info(
                    "sub url {0} sub title {1} \n time {2}".format(
                        sub_url, _title, _time
                    )
                )
                yield Request(
                    sub_url,
                    callback=self.parse,
                    meta={
                        "title": "{0}".format(_title),
                        "date_time": "{0}-{1}".format(_year, _time),
                    },
                )
        pass

    def parse(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        content = bs.find_all("div", attrs={"class": ["Article"]})

        yield self.from_paragraphs_to_item(content, response)
        pass
