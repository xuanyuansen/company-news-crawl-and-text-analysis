#!/usr/bin/env python
# encoding: utf-8
"""
File Description:
Author: wangshuai
Mail: xxx@163.com
Created Time: 2021/05/25
"""
from bs4 import BeautifulSoup
from scrapy.http import Request
from SpiderWithScrapy.BaseSpider import BaseSpider


class StcnSpider(BaseSpider):
    def __init__(
        self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 20
    ):
        super().__init__(name, key_word, key_word_chn, start_url, base_url, end_page)

    def __inner_get_sub_url(self, sub_url):
        if (
            (self.key_word == "djjd" and self.key_word_chn == "独家解读")
            or (self.key_word == "djsj" and self.key_word_chn == "独家数据")
            or (self.key_word == "egs" and self.key_word_chn == "快讯")
            or (self.key_word == "yb" and self.key_word_chn == "研报")
            or (self.key_word == "gsdt" and self.key_word_chn == "公司动态")
            or (self.key_word == "gsxw" and self.key_word_chn == "公司新闻")
            or (self.key_word == "sd" and self.key_word_chn == "深度")
        ):
            iter_url = self.base_url + self.key_word + sub_url[1: len(sub_url)]
        elif self.key_word == "jigou" or self.key_word_chn == "机构":
            iter_url = sub_url
        else:
            iter_url = ""
            self.logger.warning("not coded")
        return iter_url

    def start_requests(self):
        start_url = getattr(self, "start_url")
        end_page = getattr(self, "end_page")
        self.logger.info(start_url)
        url_start = [start_url]
        urls_plus = [
            start_url.replace(".html", "_{0}.html".format(xid))
            for xid in range(1, end_page)
        ]
        urls = url_start + urls_plus
        for url in urls:
            yield Request(url, callback=self.parse)

    def parse(self, response):
        bs = BeautifulSoup(response.text, "lxml")

        # 深度新闻，特殊逻辑
        if self.key_word == "sd":
            ul_meta = bs.find_all("ul", class_="news_list")

            for li in ul_meta[0].find_all("li"):
                _date_news = li.find_all("p", class_="sj")[0]
                _time_news = li.find_all("span")[0]
                _a = li.find_all("a")[0]
                title = _a["title"]
                sub_url = _a["href"]
                _sub_title = (li.find_all("p", class_="exp")[0]).text.strip()
                self.logger.info(
                    "sub url is {0} title is {1}, sub title {2}".format(
                        sub_url, title, _sub_title
                    )
                )
                iter_url = self.__inner_get_sub_url(sub_url)
                yield Request(
                    iter_url,
                    callback=self.parse_further_information,
                    dont_filter=True,
                    meta={
                        "date_time": "{0} {1}".format(_date_news.text.strip()[:10], _time_news.text.strip()),
                        "title": title + _sub_title,
                    },
                )

        else:
            ul_list = bs.find_all("ul")
            for ul in ul_list:
                if ul.get("id") == "news_list2":
                    for li in ul.find_all("li"):
                        date = li.find_all("span")[0]
                        # logging.info('data is {0} type {1} {2} type {3} {4} {5}'
                        #              .format(date, type(date), date.i, type(date.i), date.text, date.string))
                        for a in li.find_all("a"):
                            if a.get("title") is not None:
                                sub_url = a["href"]
                                title = a["title"]
                                self.logger.info(
                                    "sub url is {0} title is {1}".format(sub_url, title)
                                )
                                iter_url = self.__inner_get_sub_url(sub_url)
                                yield Request(
                                    iter_url,
                                    callback=self.parse_further_information,
                                    dont_filter=True,
                                    meta={
                                        "date_time": date.text.strip()
                                        .replace("\n", "")
                                        .replace("\t\t\t\t", " "),
                                        "title": title,
                                    },
                                )
        pass

    def parse_further_information(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        paragraphs = bs.find_all("div", class_="txt_con")

        yield self.from_paragraphs_to_item(paragraphs, response)

    pass
