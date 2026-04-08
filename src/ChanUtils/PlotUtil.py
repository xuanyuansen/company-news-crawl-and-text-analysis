# -*- coding:utf-8 -*-
"""
author wangshuai
date 2021/06/02
plot util
"""
# from pandas import DataFrame
import mplfinance as mpf
import pandas as pd
import ta
import sys
from Utils.database import Database


class PlotUtil(object):
    def __init__(self, data_to_plot: pd.DataFrame):
        self.data_to_plot_frame = data_to_plot
        self.exp12 = self.data_to_plot_frame["close"].ewm(span=12, adjust=False).mean()
        self.exp26 = self.data_to_plot_frame["close"].ewm(span=26, adjust=False).mean()
        self.macd = self.exp12 - self.exp26
        self.signal = self.macd.ewm(span=9, adjust=False).mean()
        y_max = max(self.macd.max(), self.signal.max())
        y_min = min(self.macd.min(), self.signal.min())
        # 添加MACD子图，拆分成红绿柱子
        self.histogram = self.macd - self.signal
        temp_hist_p = self.macd - self.signal
        temp_hist_p[temp_hist_p < 0] = None
        self.histogram_positive = temp_hist_p
        temp_hist_n = self.macd - self.signal
        temp_hist_n[temp_hist_n >= 0] = None
        self.histogram_negative = temp_hist_n

        # BOLL线
        # 一般在软件上都用BOLL表示。该指标一般都三条线，上、中、下三个轨道。
        # 一般性地，在上轨以上和下轨以下运行是超强状态，一般中枢移动时肯定会出现，唯一区别是前者是上涨超强，后者是下跌超强。
        #
        # 注意，用这个指标有一个很好的辅助判断第二类买卖点，有时候也可以用来判断第一类买卖点。
        # 一般来说，从上轨上跌回其下或从下轨下涨回其上，都是从超强区域转向一般性区域，
        # 这时候，如果再次的上涨或回跌创出新高或新低但不能重新有效回到超强区域，那么就意味着进入中阴状态了，也就是第一类买卖点出现了。
        #
        # 但更有效的是对第二买卖点的辅助判断，
        # 一般来说，在进入中阴状态，上轨和下轨都会滞后反应，也就是等第一次回跌或回升后再次向上或下跌时，上轨和下轨才会转向，
        # 而这时候转向的上轨和下轨，往往成为最大的阻力和支持，使得第二类买卖点在其下或其上被构造出来。
        # classta.volatility.BollingerBands(close: pandas.core.series.Series, window: int = 20,
        # window_dev: int = 2, fillna: bool = False)
        self.boll = ta.volatility.BollingerBands(
            self.data_to_plot_frame["close"],
            window=20,
            # number of non-biased standard deviations from the mean
            window_dev=2,
            # Moving average type: simple moving average here
            fillna=False,
        )
        print(self.boll)
        self.data_to_plot_frame["upper"] = self.boll.bollinger_hband()
        self.data_to_plot_frame["lower"] = self.boll.bollinger_lband()
        self.data_to_plot_frame["middle"] = self.boll.bollinger_mavg()
        self.add_plot = [
            # 原图上面的MACD线
            # mpf.make_addplot(exp12, type='line', color='y'),
            # mpf.make_addplot(exp26, type='line', color='r'),
            # MACD图上面的面积柱子，红柱子，绿柱子
            mpf.make_addplot(
                self.histogram_positive,
                type="bar",
                width=0.7,
                panel=2,
                color="red",
                ylim=(y_min - 0.1, y_max + 0.1),
            ),
            mpf.make_addplot(
                self.histogram_negative,
                type="bar",
                width=0.7,
                panel=2,
                color="green",
                ylim=(y_min - 0.1, y_max + 0.1),
            ),
            mpf.make_addplot(
                self.macd, panel=2, color="fuchsia", ylim=(y_min - 0.1, y_max + 0.1)
            ),
            mpf.make_addplot(
                self.signal, panel=2, color="b", ylim=(y_min - 0.1, y_max + 0.1)
            ),
            # BOLL线
            mpf.make_addplot(
                self.data_to_plot_frame["upper"], type="line", color="r", panel=1
            ),
            mpf.make_addplot(
                self.data_to_plot_frame["lower"], type="line", color="g", panel=1
            ),
            mpf.make_addplot(
                self.data_to_plot_frame["middle"], type="line", color="b", panel=1
            ),
        ]
        self.my_color = mpf.make_marketcolors(
            up="red",
            down="cyan",
            edge="inherit",
            wick="black",
            volume={"up": "red", "down": "green"},
        )
        self.my_style = mpf.make_mpf_style(
            marketcolors=self.my_color,
            gridaxis="both",
            gridstyle="-.",
            y_on_right=False,
        )

    def plot(self, stock_name, pic_date):
        mpf.plot(
            self.data_to_plot_frame,
            type="candle",
            addplot=self.add_plot,
            mav=(5, 10, 30),
            volume=True,
            figscale=1.4,
            style=self.my_style,
            title="{0}: {1}".format(stock_name, pic_date),
            ylabel="Price",
            ylabel_lower="Volume",
            xrotation=15,
            datetime_format="%Y-%m-%d",
        )


if __name__ == "__main__":
    db = Database()
    df = db.get_data(
        database_name="stock",
        collection_name="sz000995",
        max_data_request=None,
        query=None,
        keys=None,
        sort=True,
        sort_key=["date"],
    )
    print(df.shape)
    print(df[:10])
    print(df[-10:])
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.to_datetime.html
    # https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df.set_index("date", inplace=True)
    # print(df[:100])

    _plot = PlotUtil(df)
    _plot.plot("sz002019", "亿帆医药")
    pass
