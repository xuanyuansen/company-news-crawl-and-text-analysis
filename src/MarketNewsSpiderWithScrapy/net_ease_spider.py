# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
# http://money.163.com/special/00251LR5/gptj.html
from bs4 import BeautifulSoup
from MarketNewsSpiderWithScrapy.BaseSpider import BaseSpider
from scrapy.http import Request


class NetEaseSpider(BaseSpider):
    def __init__(
        self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 20
    ):
        super().__init__(name, key_word, key_word_chn, start_url, base_url, end_page)

    def start_requests(self):
        start_url = getattr(self, "start_url")
        end_page = getattr(self, "end_page")
        self.logger.info(start_url)
        url_start = [start_url]
        urls_plus = [
            start_url.replace(".html", "_{0}.html".format(xid))
            if xid > 9
            else start_url.replace(".html", "_0{0}.html".format(xid))
            for xid in range(2, end_page)
        ]
        urls = url_start + urls_plus
        for url in urls:
            # logging.info("base url is {}".format(url))
            yield Request(url, callback=self.parse)

    def parse(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        div_list = bs.find_all("div", class_="col_l")

        for div in div_list:
            div_list = div.find_all("div", class_="item_top")
            self.logger.info("all sub url li div count is {0}".format(len(div_list)))
            for li in div_list:
                a_list = li.find_all("a")
                if len(a_list) > 0:
                    a = a_list[0]
                else:
                    a = dict()
                if a.get("href") is not None:
                    sub_url = a["href"]
                    title = a.text
                    span = li.find_all("span", class_="time")
                    # logging.info('span is {} {} {}'.format(span, len(span), span[0]))
                    _date_time = str(span[0].text).strip()
                    self.logger.info(
                        "sub url is {0} title is {1}".format(sub_url, title)
                    )
                    yield Request(
                        sub_url,
                        callback=self.parse_further_information,
                        dont_filter=True,
                        meta={"date_time": _date_time, "title": title},
                    )
        pass

    def parse_further_information(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        paragraphs = bs.find_all("div", class_="post_body")

        yield self.from_paragraphs_to_item(paragraphs, response)

    pass
