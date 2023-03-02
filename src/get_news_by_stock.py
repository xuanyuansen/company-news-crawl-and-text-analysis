import logging

from MongoDbComTools.BuildStockNewsDb import GenStockNewsDB
from Utils import config

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)

gdb = GenStockNewsDB(force_update_score_using_model=True)

for db_name, collection_list in config.ALL_SPIDER_LIST_OF_DICT.items():
    for col in collection_list:
        gdb.get_all_news_about_specific_stock(
            db_name, col.get("name").replace("spider", "data")
        )
        logging.info("{0} : {1} insert data done".format(db_name, col))
pass
