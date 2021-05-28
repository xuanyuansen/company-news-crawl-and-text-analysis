from ComTools.BuildStockNewsDb import GenStockNewsDB
from Utils import config

gdb = GenStockNewsDB()
gdb.get_all_news_about_specific_stock(
    config.SHANG_HAI_STOCK_NEWS_DB,
    config.SHANG_HAI_STOCK_COMPANY_NEWS["name"].replace("spider", "data"),
)
pass
