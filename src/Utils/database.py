import functools
import logging
import time

import pymongo
from cryptography.fernet import Fernet
from pymongo import MongoClient
import pandas as pd
import platform
from Utils import config

MAX_AUTO_RECONNECT_ATTEMPTS = 5


def graceful_auto_reconnect(mongo_op_func):
    """Gracefully handle a reconnection event."""

    # https://stackoverflow.com/questions/42502879/connection-reset-by-peer-pymongo
    @functools.wraps(mongo_op_func)
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_AUTO_RECONNECT_ATTEMPTS):
            try:
                return mongo_op_func(*args, **kwargs)
            except pymongo.errors.AutoReconnect as e:
                wait_t = 0.5 * pow(2, attempt)  # exponential back off
                logging.warning("PyMongo auto-reconnecting... %s. Waiting %.1f seconds.", str(e), wait_t)
                time.sleep(wait_t)

    return wrapper


class Database(object):
    def __init__(self):
        self.os_type = platform.system()
        self.ip = config.MONGODB_IP
        self.port = config.MONGODB_PORT
        self.conn = self.init_remote_client()
        self.collection = None

    def init_remote_client(self):
        uname = b'gAAAAABgvHJFrKFjhYB2_Ri49Ku7BVo0KwW-qKz1N7Bs20f70uNfDhGgd1rA1nRanHUnFKgPutTfMauATII2Kk5WxBuBbIDqnQ=='
        passwd = b'gAAAAABgvHJFTtvwhg3gbiaedLjlsEFMt_wdgkU1fgyIyYUizwRQXciBaSyG2DDoTvr3fD1qfRhnBzg-7rNt4rbDh7TUvyGEXQ=='
        _cipher = Fernet(config.cipher_key)
        _uname = str(_cipher.decrypt(uname), encoding="utf-8")
        _password = str(_cipher.decrypt(passwd), encoding="utf-8")
        mc = MongoClient(self.ip, self.port, username=_uname,
                         password=_password, authMechanism='SCRAM-SHA-1',
                         serverSelectionTimeoutMS='5000', maxPoolSize=200)
        logging.info('init db done!')
        return mc

    def connect_database(self, database_name):
        return self.conn[database_name]

    def get_collection(self, database_name, collection_name):
        self.collection = self.connect_database(database_name).get_collection(
            collection_name
        )
        return self.collection

    def find_max(self, database_name, collection_name, key: str):
        self.get_collection(database_name, collection_name)
        max_key_value = self.collection.find_one(sort=[(key, pymongo.DESCENDING)]).get(
            key
        )
        return max_key_value

    def insert_data(self, database_name, collection_name, data_dict):
        collection = self.get_collection(database_name, collection_name)
        collection.insert_one(data_dict)

    def update_row(self, database_name, collection_name, query, new_values):
        assert isinstance(query, dict)
        assert isinstance(new_values, dict)
        database = self.conn[database_name]
        collection = database.get_collection(collection_name)
        result = collection.update_one(query, {"$set": new_values})
        return result

    def query_fuzzy(self, _key, param):
        # 模糊查询
        return self.collection.find({_key: {"$regex": ".*{}.*".format(param)}})

    @graceful_auto_reconnect
    def get_data(
            self,
            database_name,
            collection_name,
            max_data_request=None,
            query=None,
            keys=None,
    ):
        database = self.conn[database_name]
        collection = database.get_collection(collection_name)
        if query:
            assert isinstance(query, dict)
        else:
            query = {}
        if keys:
            assert isinstance(keys, list)
        else:
            keys = []
        if max_data_request:
            assert isinstance(max_data_request, int)
        else:
            max_data_request = float("inf")

        if len(keys) != 0:
            _dict = {_key: [] for _key in keys}
            data = collection.find(query) if len(query) != 0 else collection.find()
            for _id, row in enumerate(data):
                if _id + 1 <= max_data_request:
                    for _key in keys:
                        # print("key is {0}, row is {1}".format(_key, row))
                        if row.get(_key) is not None:
                            _dict[_key].append(row[_key])
                        else:
                            _dict[_key].append("null")
                else:
                    break
            logging.info("fine done, data cnt is {}".format(len(_dict.get(keys[0]))))
        else:
            # data = collection.find()
            data = collection.find(query) if len(query) != 0 else collection.find()
            data_list = list(data)
            data_length = len(data_list)
            if data_length == 0:
                logging.warning(
                    "no data found with query {0} data {1} {2}".format(
                        query, data, data_length
                    )
                )
                return None
            else:
                logging.info(
                    "query {0} data {1} data length is {2}".format(
                        query, data, data_length
                    )
                )
            data_keys = list(
                data_list[0].keys()
            )  # ['_id', 'Date', 'PageId', 'Url', 'Title', 'Article', 'RelevantStockCodes']
            _dict = {_key: [] for _key in data_keys}
            # print(_dict)
            for _id, row in enumerate(
                    collection.find(query) if len(query) != 0 else collection.find()
            ):
                if _id + 1 <= max_data_request:
                    for _key in data_keys:
                        _dict[_key].append(row[_key])
                else:
                    break
            logging.info("find done {0}".format(len(_dict.get(data_keys[0]))))
        return pd.DataFrame(_dict)

    def drop_db(self, database):
        self.conn.drop_database(database)
