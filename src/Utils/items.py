# -*- coding: utf-8 -*-
from scrapy import Item, Field


class TweetItem(Item):
    """Tweet information"""

    _id = Field()
    Url = Field()  # URL
    Date = Field()  #
    Title = Field()  #
    RelatedStockCodes = Field()
    Article = Field()  #
    WordsFrequent = Field()  #
    Category = Field()  #
    Label = Field()
    Score = Field()
