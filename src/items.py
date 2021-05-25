# -*- coding: utf-8 -*-
from scrapy import Item, Field


class TweetItem(Item):
    """Tweet information """
    _id = Field()
    Url = Field()  # 微博URL
    Date = Field()  # 微博发表时
    Title = Field()  # 点赞数
    RelatedStockCodes = Field()
    Article = Field()  # 转发数
    WordsFrequent = Field()  # 评论数
    Category = Field()  # 评论数
    Label = Field()
    Score = Field()
