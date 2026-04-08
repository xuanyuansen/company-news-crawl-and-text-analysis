# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
from Utils.database import Database
from Utils import utils, config
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)


class Deduplication(object):
    def __init__(self, database_name, collection_name):
        self.database = Database()
        self.database_name = database_name
        self.collection_name = collection_name
        self.delete_num = 0

    def run(self):
        date_list = self.database.get_data(
            self.database_name, self.collection_name, keys=["Date"]
        )["Date"].tolist()
        collection = self.database.get_collection(
            self.database_name, self.collection_name
        )
        date_list.sort()  # 升序
        # start_date, end_date = date_list[1].split(" ")[0], date_list[-1].split(" ")[0]
        start_date, end_date = (
            min(date_list).split(" ")[0],
            max(date_list).split(" ")[0],
        )
        logging.info("remove duplication, {0} {1}".format(start_date, end_date))
        for _date in utils.get_date_list_from_range(start_date, end_date):
            # 获取特定时间对应的数据并根据URL去重
            # logging.info(_date)
            try:
                data_df = self.database.get_data(
                    self.database_name,
                    self.collection_name,
                    query={"Date": {"$regex": _date}},
                )
            except Exception as e:
                logging.error(e)
                continue
            if data_df is None:
                continue
            data_df_drop_duplicate = data_df.drop_duplicates(["Url"])
            for _id in list(set(data_df["_id"]) - set(data_df_drop_duplicate["_id"])):
                collection.delete_one({"_id": _id})
                self.delete_num += 1
            # logging.info("{} finished ... ".format(_date))
        logging.info(
            "DB:{} - COL:{} had {} data length originally, now has deleted {} depulications ... ".format(
                self.database_name,
                self.collection_name,
                str(len(date_list)),
                self.delete_num,
            )
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


class DeleteTimeWrong(object):
    def __init__(self, database_name, collection_name):
        self.database = Database()
        self.database_name = database_name
        self.collection_name = collection_name
        self.delete_num = 0
        self.today_date = datetime.now().strftime("%Y-%m-%d")

    def run(self):
        collection = self.database.get_collection(
            self.database_name, self.collection_name
        )
        for row in self.database.get_collection(
            self.database_name, self.collection_name
        ).find():
            if row["Date"] > self.today_date:
                collection.delete_one({"_id": row["_id"]})
                self.delete_num += 1
        logging.info(
            "there are {} news contained wrong value in {} collection, {}, and delete done ... ".format(
                self.delete_num, self.collection_name, self.database_name
            )
        )


if __name__ == "__main__":
    for db_name, collection_list in config.ALL_SPIDER_LIST_OF_DICT.items():
        for col in collection_list:
            dt = DeleteTimeWrong(db_name, col.get("name").replace("spider", "data"))
            dt.run()
    pass
