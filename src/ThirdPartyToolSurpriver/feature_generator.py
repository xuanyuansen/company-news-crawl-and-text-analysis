# Basic libraries
import ta
import numpy as np
from scipy.stats import linregress
import warnings

warnings.filterwarnings("ignore")


# 通过股价数据计算特征
class TAEngine:
    def __init__(self, history_to_use):
        print("Technical Indicator Engine has been initialized")
        self.HISTORY_TO_USE = history_to_use

    @staticmethod
    def __calculate_slope(data):
        """
        Calculate slope, p value, and r^2 value given some data
        """
        x_axis = np.arange(len(data))
        # slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        regression_model = linregress(x_axis, data)
        slope, r_value, p_value = (
            round(regression_model[0], 3),
            round(abs(regression_model[2]), 3),
            round(regression_model[3], 4),
        )
        return slope, r_value, p_value

    def get_technical_indicators(self, price_data, upper_case: bool = True):
        """
        Given a pandas data frame with columns -> 'Open', 'High', 'Low', 'Close', 'Volume',
        extract different technical indicators and returns
        """
        technical_indicators_dictionary = {}

        # RSI
        rsi_history = [5, 10, 15]
        for history in rsi_history:
            rsi = (
                ta.momentum.RSIIndicator(
                    price_data["Close" if upper_case else "close"],
                    window=history,
                    fillna=True,
                )
                .rsi()
                .values.tolist()
            )
            slope_rsi, r_value_rsi, p_value_rsi = self.__calculate_slope(
                rsi[-self.HISTORY_TO_USE :]
            )
            technical_indicators_dictionary["rsi-" + str(history)] = rsi[
                -self.HISTORY_TO_USE :
            ] + [slope_rsi, r_value_rsi, p_value_rsi]

        # Stochastic
        stochastic_history = [5, 10, 15]
        for history in stochastic_history:
            stochastics = (
                ta.momentum.StochasticOscillator(
                    price_data["High" if upper_case else "high"],
                    price_data["Low" if upper_case else "low"],
                    price_data["Close" if upper_case else "close"],
                    window=history,
                    smooth_window=int(history / 3),
                    fillna=True,
                )
                .stoch()
                .values.tolist()
            )
            slope_stoch, r_value_stoch, p_value_stoch = self.__calculate_slope(
                stochastics[-self.HISTORY_TO_USE :]
            )
            technical_indicators_dictionary["stochs-" + str(history)] = stochastics[
                -self.HISTORY_TO_USE :
            ] + [slope_stoch, r_value_stoch, p_value_stoch]

        # Accumulation Distribution
        acc_dist = ta.volume.acc_dist_index(
            price_data["High" if upper_case else "high"],
            price_data["Low" if upper_case else "low"],
            price_data["Close" if upper_case else "close"],
            price_data["Volume" if upper_case else "volume"],
            fillna=True,
        ).values.tolist()
        acc_dist = acc_dist[-self.HISTORY_TO_USE :]
        slope_acc_dist, r_value_acc_dist, p_value_acc_dist = self.__calculate_slope(
            acc_dist
        )
        technical_indicators_dictionary["acc_dist"] = [
            slope_acc_dist,
            r_value_acc_dist,
            p_value_acc_dist,
        ]

        # Ease of movement
        eom_history = [5, 10, 20]
        # class ta.volume.EaseOfMovementIndicator(high: pandas.core.series.Series,
        # low: pandas.core.series.Series, volume: pandas.core.series.Series, window: int = 14, fillna: bool = False)
        for history in eom_history:
            eom = ta.volume.ease_of_movement(
                price_data["High" if upper_case else "high"],
                price_data["Low" if upper_case else "low"],
                price_data["Volume" if upper_case else "volume"],
                window=history,
                fillna=True,
            ).values.tolist()
            slope_eom, r_value_eom, p_value_eom = self.__calculate_slope(
                eom[-self.HISTORY_TO_USE :]
            )
            technical_indicators_dictionary["eom-" + str(history)] = [
                slope_eom,
                r_value_eom,
                p_value_eom,
            ]

        # CCI
        cci_history = [5, 10, 20]
        # https://technical-analysis-library-in-python.readthedocs.io/en/latest/ta.html#trend-indicators
        for history in cci_history:
            cci = ta.trend.cci(
                price_data["High" if upper_case else "high"],
                price_data["Low" if upper_case else "low"],
                price_data["Close" if upper_case else "close"],
                window=history,
                constant=0.015,
                fillna=True,
            ).values.tolist()
            slope_cci, r_value_cci, p_value_cci = self.__calculate_slope(
                cci[-self.HISTORY_TO_USE :]
            )
            technical_indicators_dictionary["cci-" + str(history)] = cci[
                -self.HISTORY_TO_USE :
            ] + [slope_cci, r_value_cci, p_value_cci]

        # Daily log return
        # daily_return = ta.others.daily_return(
        #     price_data["Close"], fillna=True
        # ).values.tolist()
        daily_log_return = ta.others.daily_log_return(
            price_data["Close" if upper_case else "close"], fillna=True
        ).values.tolist()
        technical_indicators_dictionary["daily_log_return"] = daily_log_return[
            -self.HISTORY_TO_USE :
        ]

        # Volume difference
        volume_list = price_data["Volume" if upper_case else "volume"].values.tolist()
        volume_list = [vol for vol in volume_list if vol != 0]
        volume_returns = [
            volume_list[x] / volume_list[x - 1] for x in range(1, len(volume_list))
        ]
        slope_vol, r_value_vol, p_value_vol = self.__calculate_slope(
            volume_returns[-self.HISTORY_TO_USE :]
        )
        technical_indicators_dictionary["volume_returns"] = volume_returns[
            -self.HISTORY_TO_USE :
        ] + [slope_vol, r_value_vol, p_value_vol]

        return technical_indicators_dictionary

    @staticmethod
    def get_features(features_dictionary):
        """
        Extract features from the data dictionary.
        The data dictionary contains values for multiple TAs such as cci, rsi, stocks etc.
        But here, we will only use the price returns, volume returns, and eom values.
        """

        keys_to_use = ["volume_returns", "daily_log_return", "eom", "cci", "rsi"]
        all_keys = list(sorted(features_dictionary.keys()))
        feature_list = []
        for key in all_keys:
            # Check if key is present
            key_in_keys_to_use = [k in key for k in keys_to_use]
            if key_in_keys_to_use.count(True) > 0:
                # Add values for the key
                feature_list.extend(features_dictionary[key])
            else:
                # why???
                # TAs such as CCI, RSI, STOCHS are being ignored. You can add another condition above to use them
                _ = None

        return feature_list
