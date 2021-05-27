from SpiderWithScrapy.BaseSpider import BaseSpider
import logging


class ShanghaiStockSpider(BaseSpider):
    def __init__(self, name, key_word, key_word_chn, start_url, base_url, end_page: int = 20):
        super().__init__(name, key_word, key_word_chn, start_url, base_url, end_page)
        logging.info("name is {}".format(self.name))
    pass
