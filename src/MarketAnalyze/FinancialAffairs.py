# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
# 基本面财务分析与打分
from jqdatasdk import *
import akshare as ak
from Utils.utils import set_display, today_date
from tqdm import tqdm, trange
import pandas as pd
import copy

tqdm.pandas(desc='progress status')


class GlobalStockInfo(object):
    def __init__(self):
        self.today_date = today_date
        self.all_codes = []
        self.current_stock_price_info = ak.stock_zh_a_spot_em()
        print('base data shape is {}'.format(self.current_stock_price_info.shape))
        if self.current_stock_price_info.shape[0] > 10:
            print(self.current_stock_price_info[:10])

    def get_all_stock_code_list(self):
        all_codes = copy.deepcopy(self.current_stock_price_info)
        all_codes['name'] = all_codes['名称']
        print("{} length is {}, sample {}".format(type(all_codes), len(all_codes), all_codes[:10]))

        return all_codes

    def get_stock_pe_pb(self, stock_code):
        target_stock_data = self.current_stock_price_info.loc[
            self.current_stock_price_info["代码"] == stock_code
            ]
        # _index = target_stock_data.index
        try:
            return (
                target_stock_data.loc[:, "市盈率-动态"].values[0],
                target_stock_data.loc[:, "市净率"].values[0],
            )
        except Exception as e:
            print(e)
            return 0.0, 0.0

    @staticmethod
    def get_financial_info_by_stock(stock_code: str):
        # 财务指标
        # 接口: stock_financial_analysis_indicator
        # 目标地址:
        # https://money.finance.sina.com.cn/corp/go.php/
        # vFD_FinancialGuideLine/stockid/600004/ctrl/2019/displaytype/4.phtml
        stock_financial_analysis_indicator_df = ak.stock_financial_analysis_indicator(
            symbol=stock_code
        )
        print(stock_financial_analysis_indicator_df[0:4])
        # latest_df = stock_financial_analysis_indicator_df.loc[0, :]
        return stock_financial_analysis_indicator_df

    @staticmethod
    def get_financial_info_by_date(t_date: str):
        stock_em_yjbb_df = ak.stock_em_yjbb(date=t_date)
        print(stock_em_yjbb_df)
        return stock_em_yjbb_df

    # 销售毛利率
    # 销售净利率
    # 净利润-同比增长
    # 营业收入-同比增长
    # 净资产收益率 ROE
    def get_financial_info_by_date_with_condition(self,
                                                  t_date: str,
                                                  gross_profit_margin=30,
                                                  net_profit_margin=15,
                                                  inc_net_profit_year_on_year=5,
                                                  inc_operation_profit_year_on_year=20,
                                                  roe=5,
                                                  ):
        # stock_em_yjbb_df = ak.stock_em_yjbb(date=t_date)
        # update akshare function
        print(t_date)
        stock_em_yjbb_df = ak.stock_yjbb_em(date=t_date)
        stock_em_yjbb_df = stock_em_yjbb_df[
            [
                "股票代码",
                "股票简称",
                "营业收入-营业收入",
                "营业收入-同比增长",
                "净利润-净利润",
                "净利润-同比增长",
                "净资产收益率",
                "每股经营现金流量",
                "销售毛利率",
                "所处行业",
                "最新公告日期",
            ]
        ]
        stock_em_yjbb_df['代码'] = stock_em_yjbb_df.progress_apply(lambda row: row["股票代码"],
                                                                 axis=1)

        stock_em_yjbb_df['净利润率'] = stock_em_yjbb_df.progress_apply(lambda row: (100*row["净利润-净利润"])/row["营业收入-营业收入"] if row["营业收入-营业收入"]>0 else 0.0,
                                                                 axis=1)

        print(stock_em_yjbb_df[:10])
        print(stock_em_yjbb_df.dtypes)

        stock_em_yjbb_df_all = pd.merge(stock_em_yjbb_df, self.current_stock_price_info, how='left', on='代码')
        print('stock_em_yjbb_df_all shape {}'.format(stock_em_yjbb_df_all.shape))

        stock_em_yjbb_df_sub = stock_em_yjbb_df_all[
            (stock_em_yjbb_df_all["销售毛利率"] >= gross_profit_margin)
            & (stock_em_yjbb_df_all["净利润率"] >= net_profit_margin)
            & (stock_em_yjbb_df_all["净利润-同比增长"] >= inc_net_profit_year_on_year)
            & (stock_em_yjbb_df_all["营业收入-同比增长"] >= inc_operation_profit_year_on_year)
            & (stock_em_yjbb_df_all["净资产收益率"] >= roe)
            & (stock_em_yjbb_df_all["市盈率-动态"] <= 100)
            & (stock_em_yjbb_df_all["市盈率-动态"] > 0)
            & (stock_em_yjbb_df_all["市净率"] <= 10)
            ]
        print('stock_em_yjbb_df_sub type {} , shape {}'.format(type(stock_em_yjbb_df_sub), stock_em_yjbb_df_sub.shape))
        print(stock_em_yjbb_df_sub[:10])

        stock_em_yjbb_df_sub['basic_info'] = stock_em_yjbb_df_sub.progress_apply(lambda row: get_stock_basic_info_ak(str(row["代码"])),
                                                                 axis=1)

        stock_em_yjbb_df_sub.dropna(axis=0, inplace=True)
        print('stock_em_yjbb_df_sub type {} , shape {}'.format(type(stock_em_yjbb_df_sub), stock_em_yjbb_df_sub.shape))

        stock_em_yjbb_df_sub['总股本'] = stock_em_yjbb_df_sub.progress_apply(lambda row: row["basic_info"][4],
                                                                 axis=1)
        stock_em_yjbb_df_sub['经营现金流量'] = stock_em_yjbb_df_sub.progress_apply(lambda row: row["总股本"]*row["每股经营现金流量"],
                                                                          axis=1)

        stock_em_yjbb_df_sub_sub = stock_em_yjbb_df_sub[
            (stock_em_yjbb_df_sub["总股本"] <= 4.0)
            & (stock_em_yjbb_df_sub["经营现金流量"] >= 1.0)
            ]

        print('stock_em_yjbb_df_sub_sub final shape {}'.format(stock_em_yjbb_df_sub_sub.shape))
        print(stock_em_yjbb_df_sub_sub)

        return stock_em_yjbb_df_sub_sub


# 基于永续年金的估值
def get_cash_in_x_year(init_cash, cash_increase_ratio, zhe_xian_r_ratio, year_n):
    all_cash = []
    zhe_xian_cash = []
    for i in range(0, year_n):
        c = init_cash * pow(1 + cash_increase_ratio, i)
        all_cash.append(c)
        zhe_xian_cash.append(c / pow(1 + zhe_xian_r_ratio, i))
    return all_cash, zhe_xian_cash


# 自由现金流估值，重要的价值投资估值方法
def get_stock_basic_price(cash: float, capitalization: float, debug_flag: bool = False):
    current_cash = cash
    current_cap = capitalization

    cash_increase_ratio = 0.1
    zhe_xian_r_ratio = 0.1
    yong_xu_g_ratio = 0.03

    cash_year, zhe_xian_year = get_cash_in_x_year(
        current_cash, cash_increase_ratio, zhe_xian_r_ratio, 10
    )
    yong_xu = (
            cash_year[-1] * (1 + yong_xu_g_ratio) / (zhe_xian_r_ratio - yong_xu_g_ratio)
    )
    yong_xu_zhe_xian = yong_xu / pow(1 + zhe_xian_r_ratio, 10)
    gu_zhi = yong_xu_zhe_xian + sum(zhe_xian_year)
    if debug_flag:
        print("自由现金流", current_cash)
        print("总股本", current_cap / 10000)
        print(cash_year)
        print(zhe_xian_year, sum(zhe_xian_year))
        print(yong_xu, yong_xu_zhe_xian)
        print("估值", gu_zhi, gu_zhi / 100000000, "亿元")
        print("股价", gu_zhi / (current_cap * 10000))
        print("40%安全边际价格", 0.6 * gu_zhi / (current_cap * 10000))
        print("=====================")
    return gu_zhi / (current_cap * 10000)


def get_city_info(stock_code):
    q = (
        query(finance.STK_COMPANY_INFO)
            .filter(finance.STK_COMPANY_INFO.code == stock_code)
            .limit(10)
    )
    data = finance.run_query(q)
    return data["city"], data["industry_1"], data["industry_2"], data["full_name"]


def get_basic_stock(s_date: str, price_date: str):
    df = get_fundamentals(
        query(
            valuation.code,
            valuation.pe_ratio,
            valuation.capitalization,
            # valuation.pcf_ratio,  # 市现率(PCF, 现金净流量TTM), 每股市价为每股现金净流量的倍数
            valuation.market_cap,  # 总市值
            valuation.pb_ratio,
            cash_flow.net_operate_cash_flow,  # 经营活动产生的现金流量净额(元)
            cash_flow.net_invest_cash_flow,  # 投资活动产生的现金流量净额(元)
            cash_flow.subtotal_invest_cash_inflow,  # 投资活动现金流入小计(元)
            cash_flow.subtotal_invest_cash_outflow,  # 投资活动现金流出小计(元)
            cash_flow.cash_and_equivalents_at_end,
            # 量化指标1，营业收入同比增长率(%)
            indicator.inc_revenue_year_on_year,
            # 营业收入,是指公司在从事销售商品、提供劳务和让渡资产使用权等日常经营业务过程中所形成的经济利益的总流入，
            # 而营业收入同比增长率，则是检验上市公司去年一年挣钱能力是否提高的标准，营业收入同比增长,
            # 说明公司在上一年度挣钱的能力加强了，营业收入同比下降，则说明公司的挣钱能力稍逊于往年。
            # 量化指标2，营业收入同比增长率(%)
            # 同比增长率就是指公司当年期的营业利润和上月同期、上年同期的营业利润比较。
            # （当期的营业利润 - 上月（上年）当期的营业利润） / 上月（上年）当期的营业利润绝对值 = 利润同比增长率。
            indicator.inc_operation_profit_year_on_year,
            # 量化指标3，毛利率
            # 销售毛利率(%)	毛利/营业收入
            indicator.gross_profit_margin,
            # 量化指标4，ROE, 归属于母公司股东的净利润*2/（期初归属于母公司股东的净资产+期末归属于母公司股东的净资产）
            indicator.roe,
            # 量化指标5，净资产收益率(扣除非经常损益)(%)
            # 扣除非经常损益后的净利润（不含少数股东损益）*2/（期初归属于母公司股东的净资产+期末归属于母公司股东的净资产）
            indicator.inc_return,
            # 量化指标6，ROA, 净利润*2/（期初总资产+期末总资产）
            indicator.roa,
            # 量化指标7，营业利润同比增长率(%)
            # 同比增长率就是指公司当年期的营业利润和上月同期、上年同期的营业利润比较。
            # （当期的营业利润-上月（上年）当期的营业利润）/上月（上年）当期的营业利润绝对值=利润同比增长率。
            indicator.inc_operation_profit_year_on_year,
            cash_flow.statDate,
        ).filter(
            # 风生水起选股指标
            valuation.capitalization <= 20000,  # 总的股本数
            valuation.pe_ratio <= 200,
            valuation.pe_ratio > 0,
            cash_flow.net_operate_cash_flow > 10000000,  # 经营活动现金流量净额
            indicator.inc_operation_profit_year_on_year >= 20,  # 营业收入同比增长率(%)
            indicator.inc_net_profit_year_on_year >= 5,  # 净利润同比增长率(%)
            valuation.pb_ratio <= 20,
            indicator.net_profit_margin >= 15,  # 销售净利率(%) 净利润/营业收入
            indicator.gross_profit_margin >= 30,  # 销售毛利率(%) 毛利/营业收入
            # 这里不能使用 in 操作, 要使用in_()函数
            # valuation.code.in_(['000651.XSHE','002848.XSHE','603416.XSHG','603040.XSHG',
            # '002273.XSHE', '603079.XSHG', '300673.XSHE','603605.XSHG','603585.XSHG'])
        ),
        statDate=s_date,
    )

    print(df.shape)
    print(df[:10])

    df["peg"] = df["pe_ratio"] / df["inc_operation_profit_year_on_year"]
    df["info"] = df.apply(lambda row: get_security_info(row["code"]), axis=1)
    df["name"] = df.apply(lambda row: row["info"].name, axis=1)
    df["display_name"] = df.apply(lambda row: row["info"].display_name, axis=1)
    df["free_cash"] = df["net_operate_cash_flow"] - df["net_invest_cash_flow"]
    df["current_price_data"] = df.apply(
        lambda row: get_price(
            security=row["code"],
            end_date=price_date,
            frequency="daily",
            fields=["close"],
            count=1,
        ).iloc[0, :]["close"],
        axis=1,
    )

    df["f_info"] = df.apply(lambda row: get_city_info(row["code"]), axis=1)
    df["city"] = df.apply(lambda row: row["f_info"][0], axis=1)
    df["industry_1"] = df.apply(lambda row: row["f_info"][1], axis=1)
    df["industry_2"] = df.apply(lambda row: row["f_info"][2], axis=1)
    df["full_name"] = df.apply(lambda row: row["f_info"][3], axis=1)
    # 获得行业分类
    # df['industry'] = df.apply(lambda row: get_industry(row['code']), axis=1)
    # 获得证监会二级行业分类
    # df['zjw'] = df.apply(lambda row: row['industry'].get(row['code']).get('zjw').get('industry_name'), axis=1)
    df["cash_gu_zhi"] = df.apply(
        lambda row: get_stock_basic_price(row["free_cash"], row["capitalization"]),
        axis=1,
    )

    return df


# 个股信息查询
# 接口: stock_individual_info_em
# 目标地址: http://quote.eastmoney.com/concept/sh603777.html?from=classic
# 描述: 东方财富-个股-股票信息
# 限量: 单次返回指定 symbol 的个股信息


def get_stock_basic_info_ak(stock_code: str):
    try:
        stock_individual_info_em_df = ak.stock_individual_info_em(symbol=stock_code)
        # print(stock_individual_info_em_df)
        market_value = 0.0 if isinstance(stock_individual_info_em_df.loc[0, "value"], str) else stock_individual_info_em_df.loc[0, "value"] / 100000000
        flow_market_value = 0.0 if isinstance(stock_individual_info_em_df.loc[1, "value"], str) else stock_individual_info_em_df.loc[1, "value"] / 100000000
        capitalization = 0.0 if isinstance(stock_individual_info_em_df.loc[6, "value"], str) else stock_individual_info_em_df.loc[6, "value"] / 100000000
        flow_capitalization = 0.0 if isinstance(stock_individual_info_em_df.loc[7, "value"], str) else stock_individual_info_em_df.loc[7, "value"] / 100000000
        stock_name = stock_individual_info_em_df.loc[5, "value"]
        current_price = market_value / capitalization
        return (
            stock_name,
            current_price,
            market_value,
            flow_market_value,
            capitalization,
            flow_capitalization,
        )
    except Exception as e:
        return None


def get_stock_latest_pe_pb_ak(stock_code: str):
    df = ak.stock_zh_a_spot_em()
    return df


if __name__ == "__main__":
    set_display()
    price_db = GlobalStockInfo()
    price_db.get_all_stock_code_list()
    test_code = "000001"
    print(get_stock_basic_info_ak(test_code))
    print(price_db.get_stock_pe_pb(test_code))
    final_res = price_db.get_financial_info_by_date_with_condition("20220331")

    final_res.to_csv("价值选股_{0}_{1}.csv".format('2022q1', today_date))
    pass
