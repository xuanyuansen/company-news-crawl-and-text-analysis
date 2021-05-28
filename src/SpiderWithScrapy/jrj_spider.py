# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
from bs4 import BeautifulSoup
from SpiderWithScrapy.BaseSpider import BaseSpider
from scrapy.http import Request


class JrjSpider(BaseSpider):
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
            start_url.replace(".shtml", "-{0}.shtml".format(xid))
            for xid in range(2, end_page + 1)
        ]
        urls = url_start + urls_plus
        for url in urls:
            yield Request(url, callback=self.parse)

    def parse(self, response):
        bs = BeautifulSoup(response.text, "lxml")

        div_list = bs.find_all("div", class_="list-main")
        for div in div_list:
            li_list = div.find_all("li")
            self.logger.info("all sub url li  count is {0}".format(len(li_list)))
            for li in li_list:
                a_list = li.find_all("a")
                if len(a_list) > 0:
                    a = a_list[0]
                else:
                    a = dict()
                if a.get("title") is not None and a.get("href") is not None:
                    sub_url = a["href"]
                    title = a["title"]
                    date = li.find_all("span")[0]
                    self.logger.info("sub url is {0} title is {1}".format(sub_url, title))
                    yield Request(
                        sub_url,
                        callback=self.parse_further_information,
                        dont_filter=True,
                        meta={
                            "date_time": " ".join(date.text.strip().split(" ")),
                            "title": title,
                        },
                    )
        pass

    def parse_further_information(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        paragraphs = bs.find_all("div", class_="texttit_m1")

        yield self.from_paragraphs_to_item(paragraphs, response)
