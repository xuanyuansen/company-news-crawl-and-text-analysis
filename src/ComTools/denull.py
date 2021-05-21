# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
"""
删除数据库中含有null值的行
"""
import logging
from Utils.database import Database
from Utils import config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)


class DeNull(object):
    def __init__(self, database_name, collection_name):
        self.database = Database()
        self.database_name = database_name
        self.collection_name = collection_name
        self.delete_num = 0

    def run(self):
        collection = self.database.get_collection(
            self.database_name, self.collection_name
        )
        for row in self.database.get_collection(
            self.database_name, self.collection_name
        ).find():
            for _key in list(row.keys()):
                if _key != "RelatedStockCodes" and row[_key] == "":
                    collection.delete_one({"_id": row["_id"]})
                    self.delete_num += 1
                    break
        logging.info(
            "there are {} news contained NULL value in {} collection ... ".format(
                self.delete_num, self.collection_name
            )
        )


if __name__ == "__main__":
    DeNull(config.DATABASE_NAME, config.COLLECTION_NAME_CNSTOCK).run()
    DeNull(config.DATABASE_NAME, config.COLLECTION_NAME_NBD).run()
    DeNull(config.DATABASE_NAME, config.COLLECTION_NAME_JRJ).run()
