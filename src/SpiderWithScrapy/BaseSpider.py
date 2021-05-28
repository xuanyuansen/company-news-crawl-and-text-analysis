# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install

from ComTools.BuildStockNewsDb import GenStockNewsDB
from scrapy import Spider
from Utils.items import TweetItem
import hashlib
import re


class BaseSpider(Spider):
    def __init__(self, name, key_word, key_word_chn, start_url, base_url, end_page):
        self.name = name
        self.start_url: str = start_url
        self.end_page: int = end_page
        self.key_word = key_word
        self.key_word_chn = key_word_chn
        self.base_url = base_url
        self.GenStockNewsDB = GenStockNewsDB(force_train_model=False)
        self.name_code_dict = dict(
            (self.GenStockNewsDB.name_code_df[["name", "code"]]).values
        )
        self.logger.info("spider name is {}".format(self.name))
        super().__init__()

    def start_requests(self):
        pass

    def parse(self, response):
        pass

    def from_paragraphs_to_item(self, paragraphs: list, response):
        article = ""
        for paragraph in paragraphs:
            p_list = paragraph.find_all("p")
            row_str = []
            if len(p_list) < 1:
                row_str.append(paragraph.text)
            else:
                for p in p_list:
                    row_str.append(str(p.text).strip())
            if len(row_str) > 0:
                article += "\n".join(row_str)
        while article.find("\u3000") != -1:
            article = article.replace("\u3000", "")
        while article.find("\r\n") != -1:
            article = article.replace("\r\n", "")
        article = " ".join(re.split(" +|\n+", article)).strip()

        (
            related_stock_codes_json,
            cut_words_json,
        ) = self.GenStockNewsDB.information_extractor.token.find_stock_code_and_name_in_article(
            article, self.name_code_dict
        )

        _judge = self.GenStockNewsDB.information_extractor.predict_score(
            response.meta["title"] + article
        )

        i_item = TweetItem()

        str_md5 = hashlib.md5(response.url.encode(encoding="utf-8")).hexdigest()

        i_item["_id"] = str_md5
        i_item["Url"] = response.url
        i_item["Date"] = response.meta["date_time"]
        i_item["Title"] = response.meta["title"]
        i_item["RelatedStockCodes"] = related_stock_codes_json
        i_item["Article"] = article
        i_item["WordsFrequent"] = cut_words_json
        i_item["Category"] = getattr(self, "key_word_chn")
        i_item["Label"] = _judge[0]
        i_item["Score"] = _judge[1]
        return i_item


pass
