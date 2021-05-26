#!/usr/bin/env python
# encoding: utf-8
"""
File Description:
Author: wangshuai
Mail: xxx@163.com
Created Time: 2021/05/25
"""
import logging
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
        self.key_word_chn = '独家解读'
        self.base_url = 'https://stock.stcn.com/'
        self.is_article_prob = 0.5
        super().__init__()

    def parse(self, response):
        bs = BeautifulSoup(response.text, "lxml")

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
                            title = a['title']
                            logging.info("sub url is {0} title is {1}".format(sub_url, title))
                            yield Request(self.base_url + self.key_word + sub_url[1:len(sub_url)],
                                          callback=self.parse_further_information,
                                          dont_filter=True,
                                          meta={'date_time':
                                                date.text.strip().replace('\n', '').replace('\t\t\t\t', ' '),
                                                'title': title})

    def parse_further_information(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        part = bs.find_all("div", class_="txt_con")
        article = ""

        for paragraph in part:
            # if paragraph.get("style") == "text-align: left;":
            # logging.info({"type {} content{}".format(type(paragraph), paragraph)})
            p_list = paragraph.find_all("p")
            row_str = ""
            for p in p_list:
                row_str += p.text
            chn_status = utils.count_chn(str(row_str))
            possible = chn_status[1]
            if possible > self.is_article_prob:
                article += row_str

        while article.find("\u3000") != -1:
            article = article.replace("\u3000", "")
        article = " ".join(re.split(" +|\n+", article)).strip()

        related_stock_codes_list, cut_words_json = \
            self.GenStockNewsDB.information_extractor.token.find_relevant_stock_codes_in_article(
                article, dict(self.name_code_df.values)
            )

        _judge = self.GenStockNewsDB.information_extractor.predict_score(response.meta['title'] + article)

        i_item = TweetItem()
        i_item['_id'] = str(hash(response.url))
        i_item['Url'] = response.url
        i_item['Date'] = response.meta['date_time']
        i_item['Title'] = response.meta['title']
        i_item['RelatedStockCodes'] = " ".join(related_stock_codes_list)
        i_item['Article'] = article
        i_item['WordsFrequent'] = cut_words_json
        i_item['Category'] = self.key_word_chn
        i_item['Label'] = _judge[0]
        i_item['Score'] = _judge[1]
        yield i_item
    pass
