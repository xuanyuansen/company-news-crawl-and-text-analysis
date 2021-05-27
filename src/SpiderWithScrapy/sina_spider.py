# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
"""
新浪财经网：https://finance.sina.com.cn
公司要闻：https://finance.sina.com.cn/roll/index.d.html?cid=56592&page=1
个股点评：https://finance.sina.com.cn/roll/index.d.html?cid=56588&page=1
大盘评述：https://finance.sina.com.cn/roll/index.d.html?cid=56589&page=1
公司研究：http://stock.finance.sina.com.cn/stock/go.php/vReport_List/kind/company/index.phtml?p=1
市场研究：https://finance.sina.com.cn/roll/index.d.html?cid=56605&page=1
主力动向：https://finance.sina.com.cn/roll/index.d.html?cid=56615&page=1
行业研究：http://stock.finance.sina.com.cn/stock/go.php/vReport_List/kind/industry/index.phtml?p=1
投资策略：http://stock.finance.sina.com.cn/stock/go.php/vReport_List/kind/strategy/index.phtml?p=1
"""
# http://finance.sina.com.cn/roll/index.d.html?cid=56588
# https://finance.sina.com.cn/roll/index.d.html?cid=56588&page=2
import hashlib

from bs4 import BeautifulSoup
from scrapy.http import Request
from SpiderWithScrapy.BaseSpider import BaseSpider
import logging

from SpiderWithScrapy.items import TweetItem


class SinaSpider(BaseSpider):
    def __init__(self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 20):
        super().__init__(name, key_word, key_word_chn, start_url, base_url, end_page)
        logging.info("name is {}".format(self.name))

    def start_requests(self):
        start_url = getattr(self, 'start_url')
        end_page = getattr(self, 'end_page')
        logging.info(start_url)
        url_start = [start_url]
        urls_plus = [start_url + "&page={0}".format(xid) for xid in range(2, end_page)]
        urls = url_start + urls_plus
        for url in urls:
            # logging.info("base url is {}".format(url))
            yield Request(url, callback=self.parse)

    def parse(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        ul_list = bs.find_all("ul", class_="list_009")

        for ul in ul_list:
            li_list = ul.find_all("li")
            logging.info("all sub li div count is {0}".format(len(li_list)))
            for li in li_list:
                a_list = li.find_all("a")
                if len(a_list) > 0:
                    a = a_list[0]
                else:
                    a = dict()
                if a.get("href") is not None:
                    sub_url = a["href"]
                    title = a.text
                    span = li.find_all("span")
                    # logging.info('span is {} {} {}'.format(span, len(span), span[0]))
                    _date_time = str(span[0].text).strip().replace('(', '').replace(')', '')
                    logging.info("sub url is {0} title is {1}".format(sub_url, title))
                    yield Request(sub_url,
                                  callback=self.parse_further_information,
                                  dont_filter=True,
                                  meta={'date_time': _date_time,
                                        'title': title})
        pass

    def has_cms_style(self, tag):
        return tag.has_attr('cms-style')

    def parse_further_information(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        paragraphs = bs.find_all(self.has_cms_style)

        article = []
        for paragraph in paragraphs:
            article.append(str(paragraph.text).strip())

        article += "\n".join(article)
        # article = " ".join(re.split(" +|\n+", article)).strip()

        related_stock_codes_json, cut_words_json = \
            self.GenStockNewsDB.information_extractor.token.find_stock_code_and_name_in_article(
                article, self.name_code_dict)

        _judge = self.GenStockNewsDB.information_extractor.predict_score(response.meta['title'] + article)

        i_item = TweetItem()

        str_md5 = hashlib.md5(response.url.encode(encoding='utf-8')).hexdigest()

        i_item['_id'] = str_md5
        i_item['Url'] = response.url
        i_item['Date'] = response.meta['date_time']
        i_item['Title'] = response.meta['title']
        i_item['RelatedStockCodes'] = related_stock_codes_json
        i_item['Article'] = article
        i_item['WordsFrequent'] = cut_words_json
        i_item['Category'] = getattr(self, 'key_word_chn')
        i_item['Label'] = _judge[0]
        i_item['Score'] = _judge[1]

        yield self.from_paragraphs_to_item(paragraphs, response)

    pass
