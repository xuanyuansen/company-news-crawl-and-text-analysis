#!/usr/bin/env python
# encoding: utf-8
"""
File Description:
Author: wangshuai
Mail: xxx@163.com
Created Time: 2021/05/25
"""
import re

from bs4 import BeautifulSoup
from scrapy.http import Request
from Utils import utils
from SpiderWithScrapy.BaseSpider import BaseSpider
from items import TweetItem
# https://data.stcn.com/djsj/index_17.html 独家数据
# https://stock.stcn.com/index_1.html 股市
# https://stock.stcn.com/djjd/index_1.html 独家解读
# https://kuaixun.stcn.com/yb/index_1.html 研报
# https://news.stcn.com/sd/index_1.html 深度
# https://company.stcn.com/index_2.html 公司
# https://finance.stcn.com/index_2.html 机构


class StcnSpider(BaseSpider):
    def __init__(self):
        self.name = 'djjd_spider'
        self.start_url: str = 'https://stock.stcn.com/djjd/index.html'
        self.end_page: int = 20
        self.key_word = 'djjd'
        self.base_url = 'https://stock.stcn.com/'
        self.is_article_prob = 0.5
        super().__init__()

    def parse(self, response):
        bs = BeautifulSoup(response.text, "lxml")

        a_list = bs.find_all("a")
        for a in a_list:
            if a["href"].contains(self.key_word):
                sub_url = a["href"].string
                yield Request(self.base_url + sub_url[1:len(sub_url)],
                              callback=self.parse_further_information,
                              dont_filter=True,
                              meta=response.meta)

    def parse_further_information(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        span_list = bs.find_all("span")
        part = bs.find_all("p")
        article = ""
        date = ""
        for span in span_list:
            if "class" in span.attrs and span["class"] == ["auth_item"]:
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

        related_stock_codes_list, cut_words_json = \
            self.information_extractor.token.find_relevant_stock_codes_in_article(
                article, self.name_code_dict
            )

        title = bs.find_all("h2")[0]

        _judge = self.information_extractor.predict_score(title + article)

        i_item = TweetItem()
        i_item['_id'] = str(hash(response.url))
        i_item['Url'] = response.url
        i_item['Date'] = date
        i_item['Title'] = title
        i_item['RelatedStockCodes'] = " ".join(related_stock_codes_list)
        i_item['Article'] = article
        i_item['WordsFrequent'] = cut_words_json
        i_item['Category'] = self.spider_name
        i_item['Label'] = _judge[0]
        i_item['Score'] = _judge[1]
        yield i_item
    pass
