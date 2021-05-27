# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
# http://finance.eastmoney.com/a/cssgs.html
from bs4 import BeautifulSoup
from scrapy.http import Request
from SpiderWithScrapy.BaseSpider import BaseSpider
import logging


class EastMoneySpider(BaseSpider):
    def __init__(self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 20):
        super().__init__(name, key_word, key_word_chn, start_url, base_url, end_page)
        logging.info("name is {}".format(self.name))

    def start_requests(self):
        start_url = getattr(self, 'start_url')
        end_page = getattr(self, 'end_page')
        logging.info(start_url)
        url_start = [start_url]
        urls_plus = [start_url.replace(".html", "_{0}.html".format(xid)) for xid in range(2, end_page+1)]
        urls = url_start + urls_plus
        for url in urls:
            # logging.info("base url is {}".format(url))
            yield Request(url, callback=self.parse)

    def parse(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        li_list = bs.find_all("div", class_="repeatList")

        for li in li_list:
            div_list = li.find_all("div", class_="text text-no-img")
            logging.info("all sub li div count is {0}".format(len(div_list)))
            for div in div_list:
                p_list = div.find_all("p")
                logging.info("len p count is {0}".format(len(p_list)))
                if len(p_list) == 3:
                    a = p_list[0].find_all('a')[0]
                    logging.info("a is {0} type {1}".format(a, type(a)))
                    _time = p_list[2]
                    logging.info("_time is {0} type {1}".format(_time, type(_time)))
                    if a.get("href") is not None:
                        sub_url = a["href"]
                        title = str(a.text).strip()
                        # span = li.find_all("span")
                        # logging.info('span is {} {} {}'.format(span, len(span), span[0]))
                        _date_time = str(_time.text).strip()
                        logging.info("sub url is {0} title is {1}".format(sub_url, title))
                        yield Request(sub_url,
                                      callback=self.parse_further_information,
                                      dont_filter=True,
                                      meta={'date_time': _date_time,
                                            'title': title})
        pass

    def parse_further_information(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        paragraphs = bs.find_all("div", class_="Body")
        yield self.from_paragraphs_to_item(paragraphs, response)

    pass
