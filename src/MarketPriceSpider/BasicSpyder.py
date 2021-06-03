# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
import pymongo
from pandas import DataFrame
import hashlib
import Utils.utils


class Spyder(object):
    def __init__(self):
        self.logger = Utils.utils.get_logger()
        pass

    def get_historical_price(self, url):
        pass

    def get_realtime_price(self, url):
        pass

    def insert_data_to_col_from_dataframe(self, col: pymongo.collection.Collection, symbol: str, data: DataFrame):
        insert_cnt = 0
        for _idx in range(data.shape[0]):
            _tmp_dict = data.iloc[_idx].to_dict()
            id_md5 = hashlib.md5(
                ("{0} {1}".format(symbol, _tmp_dict["date"])).encode(
                    encoding="utf-8"
                )
            ).hexdigest()
            if col.find_one({"_id": id_md5}) is not None:
                self.logger.info(
                    "id already exist {0} {1}".format(id_md5, _tmp_dict)
                )
                continue
            _tmp_dict["_id"] = id_md5
            # _tmp_dict.pop("turnover")
            col.insert_one(_tmp_dict)
            insert_cnt += 1
        return True, insert_cnt
    pass
