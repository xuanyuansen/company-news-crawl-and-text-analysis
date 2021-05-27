from bs4 import BeautifulSoup

from SpiderWithScrapy.BaseSpider import BaseSpider
import logging
from scrapy.http import Request


class NBDSpider(BaseSpider):
    def __init__(self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 20):
        self.name = name
        self.start_url: str = start_url
        self.end_page: int = end_page
        self.key_word = key_word
        self.key_word_chn = key_word_chn
        self.base_url = base_url
        logging.info("name is {}".format(self.name))
        super().__init__()

    def start_requests(self):
        start_url = getattr(self, 'start_url')
        end_page = getattr(self, 'end_page')
        logging.info(start_url)
        url_start = [start_url]
        urls_plus = [(start_url+"/page/1").replace("page/1", "page/{0}.html".format(xid)) for xid in range(2, end_page)]
        urls = url_start + urls_plus
        for url in urls:
            yield Request(url, callback=self.parse)

    def parse(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        div_list = bs.find_all("div", class_="m-list")

        for div in div_list:
            _date = str(div.find_all("p", class_="u-channeltime")[0].text).strip()
            li_list = div.find_all("li", class_="u-news-title")
            logging.info("all sub url li  count is {0}".format(len(li_list)))
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
                    _date_time = str(span[0].text).strip()
                    logging.info("sub url is {0} title is {1}".format(sub_url, title))
                    yield Request(sub_url,
                                  callback=self.parse_further_information,
                                  dont_filter=True,
                                  meta={'date_time': ' '.join([_date, _date_time]),
                                        'title': title})
        pass

    def parse_further_information(self, response):
        bs = BeautifulSoup(response.text, "lxml")
        paragraphs = bs.find_all("div", class_="g-articl-text")
        yield self.from_paragraphs_to_item(paragraphs, response)

    pass
