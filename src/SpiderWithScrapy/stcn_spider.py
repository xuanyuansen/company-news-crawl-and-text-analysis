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


class StcnSpider(BaseSpider):
    def __init__(self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 20):
        self.name = name
        self.start_url: str = start_url
        self.end_page: int = end_page
        self.key_word = key_word
        self.key_word_chn = key_word_chn
        self.base_url = base_url
        self.is_article_prob = 0.5
        logging.info("name is {}".format(self.name))
        super().__init__()

    def __inner_get_sub_url(self, sub_url):
        if (self.key_word == 'djjd' and self.key_word_chn == '独家解读') or \
                (self.key_word == 'djsj' and self.key_word_chn == '独家数据') or \
                (self.key_word == 'egs' and self.key_word_chn == '快讯') or\
                (self.key_word == 'yb' and self.key_word_chn == '研报') or \
                (self.key_word == 'gsdt' and self.key_word_chn == '公司动态') or \
                (self.key_word == 'gsxw' and self.key_word_chn == '公司新闻') or \
                (self.key_word == 'sd' and self.key_word_chn == '深度'):
            iter_url = self.base_url + self.key_word + sub_url[1:len(sub_url)]
        elif self.key_word == 'jigou' or self.key_word_chn == '机构':
            iter_url = sub_url
        else:
            iter_url = ''
            logging.warning("not coded")
        return iter_url

    def parse(self, response):
        bs = BeautifulSoup(response.text, "lxml")

        # 深度新闻，特殊逻辑
        if self.key_word == 'sd':
            ul_meta = bs.find_all("ul", class_="news_list")

            for li in ul_meta[0].find_all("li"):
                _date_news = li.find_all("p", class_="sj")[0]
                _time_news = li.find_all("span")[0]
                _a = _time_news = li.find_all("a")[0]
                title = _a['title']
                sub_url = _a["href"]
                _sub_title = (li.find_all("p", class_="exp")[0]).text
                logging.info("sub url is {0} title is {1}, sub title {2}".format(sub_url, title, _sub_title))
                iter_url = self.__inner_get_sub_url(sub_url)
                yield Request(iter_url,
                              callback=self.parse_further_information,
                              dont_filter=True,
                              meta={'date_time': '{0} {1}'.format(_date_news.text, _time_news.text),
                                    'title': title + _sub_title})

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
                                title = a['title']
                                logging.info("sub url is {0} title is {1}".format(sub_url, title))
                                iter_url = self.__inner_get_sub_url(sub_url)
                                yield Request(iter_url,
                                              callback=self.parse_further_information,
                                              dont_filter=True,
                                              meta={'date_time':
                                                    date.text.strip().replace('\n', '').replace('\t\t\t\t', ' '),
                                                    'title': title})
        pass

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
            if len(row_str) > 0:
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
