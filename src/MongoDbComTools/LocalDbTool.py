from pandas import DataFrame
import akshare as ak
from Utils.database import Database
from Utils import config, utils
import datetime

from Utils.utils import set_display


class LocalDbTool(object):
    def __init__(self):
        self.db_obj = Database()
        # cn stock market
        self.database_name_cn = config.STOCK_DATABASE_NAME
        self.collection_name_cn = config.COLLECTION_NAME_STOCK_BASIC_INFO
        self.col_basic_info_cn = self.db_obj.get_collection(
            self.database_name_cn, self.collection_name_cn
        )

        self.base_stock_info_df = self.db_obj.get_data(
            self.database_name_cn, self.collection_name_cn
        )
        # hk stock market
        self.database_name_hk = config.HK_STOCK_DATABASE_NAME
        self.collection_name_hk = config.COLLECTION_NAME_STOCK_BASIC_INFO_HK
        self.col_basic_info_hk = self.db_obj.get_collection(
            self.database_name_hk, self.collection_name_hk
        )
        self.col_basic_info_hk_df = self.db_obj.get_data(
            self.database_name_hk, self.collection_name_hk
        )
        # us stock market
        self.database_name_us = config.US_STOCK_DATABASE_NAME
        self.collection_name_us = config.COLLECTION_NAME_STOCK_BASIC_INFO_US
        self.col_basic_info_us = self.db_obj.get_collection(
            self.database_name_us, self.collection_name_us
        )
        # "stock_us_zh_spot"  # 中国概念股行情
        # "stock_us_zh_daily"  # 中国概念股历史数据
        self.collection_name_us_zh = config.COLLECTION_NAME_STOCK_BASIC_INFO_US_ZH
        self.col_basic_info_us_zh = self.db_obj.get_collection(
            self.database_name_us, self.collection_name_us_zh
        )

        self.cn_industry_file = config.CN_STOCK_INDUSTRY_DICT_FILE
        self.cn_concept_file = config.CN_STOCK_CONCEPT_DICT_FILE

    def get_target_stock_info_by_code(self, stock_code):
        # print(
        #     "shape is {}, sample is {}".format(
        #         self.base_stock_info_df.shape, self.base_stock_info_df[:10]
        #     )
        # )
        # print("data type is {}".format(self.base_stock_info_df.dtypes))

        query_res = self.base_stock_info_df[
            self.base_stock_info_df["code"] == stock_code
        ]
        return query_res

    # 获取总的股本数
    def get_stock_all_capital_num(self, stock_code):
        stock_individual_info_em_df = ak.stock_individual_info_em(symbol=stock_code)
        # print(stock_individual_info_em_df)
        res = stock_individual_info_em_df[stock_individual_info_em_df["item"] == "总股本"]
        return res.values[0][1]

    # symbol is code plus market type
    def get_symbol_from_code(self, target_code):
        info = self.get_target_stock_info_by_code(stock_code=target_code)
        res = list(info["symbol"])
        if len(res) > 0:
            return res[0]
        else:
            return 0

    def get_price_list_by_range(self, symbol, m_type, start, end):
        success_or_not, a_stock_price = self.get_daily_price_data_of_specific_stock(
            symbol=symbol,
            market_type=m_type,
            start_date=start,
            end_date=end,
        )
        if success_or_not:
            return list(a_stock_price["close"])
        else:
            return 0

    def get_target_stock_info_by_code_of_hk(self, stock_code):
        query_res = self.col_basic_info_hk_df[
            self.col_basic_info_hk_df["symbol"] == stock_code
        ]
        print(query_res)
        return query_res

    def get_week_data_stock(
        self,
        symbol,
        market_type: str,
        start_date: str = None,
        end_date=None,
        _keys: list = None,
    ):
        res, stock_data = self.get_daily_price_data_of_specific_stock(
            symbol, market_type, start_date, end_date, _keys
        )
        if not res:
            return False, DataFrame()
        df2 = stock_data.resample("W").agg(
            {
                "open": "first",
                "close": "last",
                "high": "max",
                "low": "min",
                "money": "sum",
                "volume": "sum",
                "date": "first",
            }
        )

        df2 = df2[df2["open"].notnull()]
        df2.index = df2["date"]
        # print(df2)
        return True, df2

    @staticmethod
    def _normalize_query_date_candidates(date_value):
        if date_value is None:
            return []

        candidates = []
        raw_value = str(date_value).strip()
        if raw_value:
            candidates.append(raw_value)

        parsed_dt = None
        if isinstance(date_value, datetime.datetime):
            parsed_dt = date_value
        elif isinstance(date_value, datetime.date):
            parsed_dt = datetime.datetime.combine(date_value, datetime.time.min)
        else:
            for fmt in (
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%Y%m%d",
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
            ):
                try:
                    parsed_dt = datetime.datetime.strptime(raw_value, fmt)
                    break
                except Exception:
                    continue

        if parsed_dt is not None:
            candidates.extend(
                [
                    parsed_dt,
                    parsed_dt.strftime("%Y-%m-%d"),
                    parsed_dt.strftime("%Y/%m/%d"),
                    parsed_dt.strftime("%Y%m%d"),
                ]
            )

        deduped = []
        seen = set()
        for item in candidates:
            marker = (type(item).__name__, str(item))
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(item)
        return deduped

    def _build_date_query_candidates(self, start_date, end_date, market_type: str):
        start_candidates = self._normalize_query_date_candidates(start_date)
        end_candidates = (
            self._normalize_query_date_candidates(end_date) if end_date is not None else [None]
        )

        market_l = str(market_type).lower()
        if market_l == "us":
            ordered_starts = [
                *[c for c in start_candidates if isinstance(c, datetime.datetime)],
                *[c for c in start_candidates if not isinstance(c, datetime.datetime)],
            ]
            ordered_ends = [
                *[c for c in end_candidates if isinstance(c, datetime.datetime)],
                *[c for c in end_candidates if not isinstance(c, datetime.datetime)],
            ]
        else:
            ordered_starts = [
                *[c for c in start_candidates if isinstance(c, str)],
                *[c for c in start_candidates if not isinstance(c, str)],
            ]
            ordered_ends = [
                *[c for c in end_candidates if isinstance(c, str)],
                *[c for c in end_candidates if not isinstance(c, str)],
            ]

        query_candidates = []
        if end_date is None:
            for start_candidate in ordered_starts:
                query_candidates.append({"date": {"$gte": start_candidate}})
            return query_candidates

        for start_candidate in ordered_starts:
            for end_candidate in ordered_ends:
                if end_candidate is None:
                    query_candidates.append({"date": {"$gte": start_candidate}})
                else:
                    query_candidates.append(
                        {"date": {"$gte": start_candidate, "$lte": end_candidate}}
                    )
        return query_candidates

    def _try_load_stock_data(self, db_name, symbol, query_candidates, _keys=None):
        for query in query_candidates:
            stock_data = self.db_obj.get_data(
                db_name, symbol, query=query, keys=_keys, sort=True, sort_key=["date"]
            )
            if stock_data is not None and not stock_data.empty:
                return stock_data
        return DataFrame()

    def get_daily_price_data_of_specific_stock(
        self,
        symbol,
        market_type: str,
        start_date: str = None,
        end_date: str = None,
        _keys: list = None,
    ):
        if market_type == "cn":
            db_name = self.database_name_cn
        elif market_type == "hk":
            db_name = self.database_name_hk
        elif market_type == "us":
            db_name = self.database_name_us
        else:
            raise Exception("unknown market type")

        if start_date is None:
            stock_data = self.db_obj.get_data(
                db_name, symbol, sort=True, sort_key=["date"]
            )
        else:
            query_candidates = self._build_date_query_candidates(
                start_date=start_date,
                end_date=end_date,
                market_type=market_type,
            )
            stock_data = self._try_load_stock_data(
                db_name=db_name,
                symbol=symbol,
                query_candidates=query_candidates,
                _keys=_keys,
            )

        if stock_data is None or stock_data.empty:
            return False, DataFrame()
        # to do 用joint quant的数据来更新money数据。
        stock_data["money"] = stock_data.apply(
            lambda row: 0.25
            * (row["open"] + row["close"] + row["high"] + row["low"])
            * row["volume"],
            axis=1,
        )
        if market_type == "hk":
            stock_data["date_time_index"] = stock_data.apply(
                lambda row: datetime.datetime.strptime(row["date"], "%Y-%m-%d"), axis=1
            )
            stock_data.index = stock_data["date_time_index"]
        else:
            stock_data.index = stock_data["date"]
        return True, stock_data


if __name__ == "__main__":
    set_display()
    local_db_tool = LocalDbTool()
    res = local_db_tool.get_target_stock_info_by_code(stock_code="000001")
    print(res)

    capital_res = local_db_tool.get_stock_all_capital_num(stock_code="000001")
    print(capital_res)
    pass
