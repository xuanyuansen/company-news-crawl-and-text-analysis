# -*- coding:utf-8 -*-
# 涨停板行情
# "stock_em_zt_pool"  # 涨停板行情-涨停股池
# "stock_em_zt_pool_previous"  # 涨停板行情-昨日涨停股池
# "stock_em_zt_pool_strong"  # 涨停板行情-强势股池
# "stock_em_zt_pool_sub_new"  # 涨停板行情-次新股池
# "stock_em_zt_pool_zbgc"  # 涨停板行情-炸板股池
# "stock_em_zt_pool_dtgc"  # 涨停板行情-跌停股池

# 同花顺-数据中心-资金流向
#  "stock_fund_flow_individual"  # 同花顺-数据中心-资金流向-个股资金流
# "stock_fund_flow_industry"  # 同花顺-数据中心-资金流向-行业资金流
# "stock_fund_flow_concept"  # 同花顺-数据中心-资金流向-概念资金流
# "stock_fund_flow_big_deal"  # 同花顺-数据中心-资金流向-大单追踪

# 行业板块
# "stock_board_industry_cons_ths"  # 同花顺-成份股
# "stock_board_industry_index_ths"  # 同花顺-指数日频数据

# 概念板块
# "stock_board_concept_cons_ths"  # 同花顺-成份股
# "stock_board_concept_index_ths"  # 同花顺-指数日频数据

# 分红配送
# "stock_em_fhps"  # 分红配送
# 业绩快报
# "stock_em_yjkb"  # 业绩快报
import akshare as ak
import pandas as pd
# 显示所有列
pd.set_option("display.max_columns", None)
# 显示所有行
pd.set_option("display.max_rows", None)
pd.set_option("max_colwidth", 500)


if __name__ == "__main__":
    # utils.set_display()
    # 涨停板行情-涨停股池
    zhangting = ak.stock_em_zt_pool(date="20210610")
    print(zhangting)
    # kuaibao = ak.stock_em_yjkb(date='20210331')
    # print(kuaibao)

    # “即时”, "3日排行", "5日排行", "10日排行", "20日排行"
    # 同花顺-数据中心-资金流向-行业资金流
    money_flow = ak.stock_fund_flow_industry(symbol="即时")
    print(money_flow)
    money_flow_3_day = ak.stock_fund_flow_industry(symbol="3日排行")
    print(money_flow_3_day)

    # 行业 同花顺-成份股
    cheng_fen_stock = ak.stock_board_industry_cons_ths(symbol="石油矿业开采")
    cheng_fen_stock.sort_values(by=["涨跌幅"], axis=0, ascending=False)
    print(cheng_fen_stock)

    # 同花顺-指数日频数据
    # http://q.10jqka.com.cn/gn/detail/code/301558//
    industry_index = ak.stock_board_industry_index_ths(symbol="石油矿业开采")
    print(industry_index.shape)

    # 概念 同花顺-成份股
    # http://q.10jqka.com.cn/gn/detail/code/301558//
    gai_nian_stock = ak.stock_board_concept_cons_ths(symbol="白酒概念")
    gai_nian_stock.sort_values(by=["涨跌幅"], axis=0, ascending=False)
    print(gai_nian_stock)

    # 涨停板行情-强势股池
    strong_stock = ak.stock_em_zt_pool_strong(date="20210611")
    print(strong_stock)
    # 涨停板行情-次新股池
    sub_new_stock = ak.stock_em_zt_pool_sub_new(date="20210611")
    print(sub_new_stock)

    # 同花顺-数据中心-资金流向-概念资金流
    flow_concept = ak.stock_fund_flow_concept(symbol="3日排行")
    print("同花顺-数据中心-资金流向-概念资金流 3日排行")
    print(flow_concept)
    # 同花顺-数据中心-资金流向-行业资金流
    industry_flow = ak.stock_fund_flow_industry(symbol="3日排行")
    print("同花顺-数据中心-资金流向-行业资金流 3日排行")
    print(industry_flow)

    # 概念 同花顺-指数日频数据
    gai_nian_stock_hong_meng = ak.stock_board_concept_cons_ths(symbol="鸿蒙概念")
    print("概念 同花顺-指数日频数据, 鸿蒙概念")
    print(gai_nian_stock_hong_meng)

    # 同花顺-数据中心-资金流向-大单追踪
    # big_deal = ak.stock_fund_flow_big_deal()
    print("同花顺-数据中心-资金流向-大单追踪")
    # print(big_deal.shape)
    # print(big_deal[:100])

    # 同花顺-数据中心-资金流向-个股资金流
    # flow_individual = ak.stock_fund_flow_individual(symbol = "即时")
    print("同花顺-数据中心-资金流向-个股资金流 即时")
    # print(flow_individual.shape)
    # print(flow_individual[:100])

    pass
