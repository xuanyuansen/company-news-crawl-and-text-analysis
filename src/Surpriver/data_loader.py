# Basic libraries
import os
import collections
import numpy as np

from Utils.database import Database
from tqdm import tqdm

from Utils import config
from feature_generator import TAEngine
import warnings

warnings.filterwarnings("ignore")


class DataEngine:
    def __init__(
        self,
        history_to_use,
        data_granularity_minutes,  # default=15
        is_save_dict,
        is_load_dict,
        dict_path,
        min_volume_filter,
        is_test,
        future_bars_for_testing,
        volatility_filter,
        stocks_list,
    ):
        print("Data engine has been initialized...")
        self.db_name = config.STOCK_DATABASE_NAME
        self.db_obj = Database()
        self.conn = self.db_obj.connect_database(self.db_name)
        self.col_list = self.conn.collection_names()
        self.DATA_GRANULARITY_MINUTES = data_granularity_minutes
        self.IS_SAVE_DICT = is_save_dict
        self.IS_LOAD_DICT = is_load_dict
        self.DICT_PATH = dict_path
        self.VOLUME_FILTER = min_volume_filter
        self.FUTURE_FOR_TESTING = future_bars_for_testing
        self.IS_TEST = is_test
        self.VOLATILITY_THRESHOLD = volatility_filter
        self.CLOSE_PRICE_INDEX = 4

        # Stocks list
        self.directory_path = str(os.path.dirname(os.path.abspath(__file__)))
        self.stocks_file_path = self.directory_path + f"/stocks/{stocks_list}"
        self.stocks_list = []

        # Load stock names in a list
        self.load_stocks_from_file()

        # Load Technical Indicator engine
        self.taEngine = TAEngine(history_to_use=history_to_use)

        # Dictionary to store data. This will only store and save data if the argument is_save_dictionary is 1.
        self.features_dictionary_for_all_symbols = {}

        # Data length
        self.stock_data_length = []

        # Create an instance of the Binance Client with no api key and no secret
        # (api key and secret not required for the functionality needed for this script)
        # self.binance_client = Client("", "")
        self.binance_client = None

    def load_stocks_from_file(self):
        """
        Load stock names from the file
        """
        print("Loading all stocks from file...")
        stocks_list = open(self.stocks_file_path, "r").readlines()
        stocks_list = [str(item).strip("\n") for item in stocks_list]

        # Load symbols
        stocks_list = list(sorted(set(stocks_list)))
        print("Total number of stocks: %d" % len(stocks_list))
        self.stocks_list = stocks_list

    def get_most_frequent_key(self, input_list):
        counter = collections.Counter(input_list)
        counter_keys = list(counter.keys())
        frequent_key = counter_keys[0]
        return frequent_key

    def new_get_data(self, symbol):
        if "sh" in symbol or "sz" in symbol:
            col_name = symbol
        elif "basic_info" == symbol:
            return [], [], True
        elif int(symbol) >= 600000:
            col_name = "sh{}".format(symbol)
        else:
            col_name = "sz{}".format(symbol)

        df = self.db_obj.get_data(self.db_name, col_name)
        if df.shape[0] < 30:
            return [], [], True

        df["Datetime"] = df["date"]
        df["Open"] = df["open"].astype(float)
        df["High"] = df["high"].astype(float)
        df["Low"] = df["low"].astype(float)
        df["Close"] = df["close"].astype(float)
        df["Volume"] = df["volume"].astype(float)

        if self.IS_TEST == 1:
            future_prices_list = df.iloc[
                -(self.FUTURE_FOR_TESTING + 1) :, :
            ].values.tolist()
            historical_prices = df.iloc[: -self.FUTURE_FOR_TESTING, :]
            history_data = historical_prices[
                [
                    "Datetime",
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume",
                ]
            ]
            # print(history_data)
            return history_data, future_prices_list, False
        else:
            # No testing
            history_data = df[
                [
                    "Datetime",
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume",
                ]
            ]
            # print(history_data)
            return history_data, [], False

    def calculate_volatility(self, stock_price_data):

        stock_price_data_list = stock_price_data.values.tolist()
        close_prices = [
            float(item[self.CLOSE_PRICE_INDEX]) for item in stock_price_data_list
        ]
        close_prices = [item for item in close_prices if item != 0]
        volatility = np.std(close_prices)
        return volatility

    def collect_data_for_all_tickers(self):
        """
        从mongodb里面获得所以股票以及其价格数据
        """
        print("Loading data for all stocks from mongodb...")
        features = []
        symbol_names = []
        historical_price_info = []
        future_price_info = []

        # Any stock with very low volatility is ignored. You can change this line to address that.
        # for symbol in self.col_list
        for i in tqdm(range(len(self.col_list))):
            symbol = self.col_list[i]

            # stock_price_data, future_prices, not_found = self.get_data(symbol)
            stock_price_data, future_prices, not_found = self.new_get_data(symbol)

            if not not_found:
                volatility = self.calculate_volatility(stock_price_data)
                print("volatility, {} {}".format(volatility, symbol))
                # Filter low volatility stocks
                if volatility < self.VOLATILITY_THRESHOLD:  # default=0.05,
                    continue

                features_dictionary = self.taEngine.get_technical_indicators(
                    stock_price_data
                )
                print("features_dictionary keys, {}".format(features_dictionary.keys()))
                feature_list = self.taEngine.get_features(features_dictionary)

                # Add to dictionary
                self.features_dictionary_for_all_symbols[symbol] = {
                    "features": features_dictionary,
                    "current_prices": stock_price_data,
                    "future_prices": future_prices,
                }

                # Save dictionary after every 100 symbols
                if (
                    len(self.features_dictionary_for_all_symbols) % 100 == 0
                    and self.IS_SAVE_DICT == 1
                ):
                    np.save(self.DICT_PATH, self.features_dictionary_for_all_symbols)

                if np.isnan(feature_list).any():
                    continue

                # Check for volume
                average_volume_last_30_tickers = np.mean(
                    list(stock_price_data["Volume"])[-30:]
                )
                if average_volume_last_30_tickers < self.VOLUME_FILTER:
                    continue

                # Add to lists
                features.append(feature_list)
                symbol_names.append(symbol)
                historical_price_info.append(stock_price_data)
                future_price_info.append(future_prices)

        print("features len {}".format(len(features)))
        # print('historical_price_info {}'.format(historical_price_info))
        print("future_price_info len {}".format(len(future_price_info)))
        print("symbol_names len {}".format(len(symbol_names)))

        # Sometimes, there are some errors in feature generation or price extraction, let us remove that stuff
        (
            features,
            historical_price_info,
            future_price_info,
            symbol_names,
        ) = self.remove_bad_data(
            features, historical_price_info, future_price_info, symbol_names
        )

        return features, historical_price_info, future_price_info, symbol_names

    def load_data_from_dictionary(self):
        # Load data from dictionary
        print("Loading data from dictionary")
        dictionary_data = np.load(self.DICT_PATH, allow_pickle=True).item()

        features = []
        symbol_names = []
        historical_price_info = []
        future_price_info = []
        for symbol in dictionary_data:
            feature_list = self.taEngine.get_features(
                dictionary_data[symbol]["features"]
            )
            current_prices = dictionary_data[symbol]["current_prices"]
            future_prices = dictionary_data[symbol]["future_prices"]

            # Check if there is any null value
            if np.isnan(feature_list).any():
                continue

            features.append(feature_list)
            symbol_names.append(symbol)
            historical_price_info.append(current_prices)
            future_price_info.append(future_prices)

        # Sometimes, there are some errors in feature generation or price extraction, let us remove that stuff
        (
            features,
            historical_price_info,
            future_price_info,
            symbol_names,
        ) = self.remove_bad_data(
            features, historical_price_info, future_price_info, symbol_names
        )

        return features, historical_price_info, future_price_info, symbol_names

    def remove_bad_data(
        self, features, historical_price_info, future_price_info, symbol_names
    ):
        """
        Remove bad data i.e data that had some errors while scraping or feature generation
        """
        length_dictionary = collections.Counter([len(feature) for feature in features])
        length_dictionary = list(length_dictionary.keys())
        print("length_dictionary is {}".format(len(length_dictionary)))
        most_common_length = length_dictionary[0]

        (
            filtered_features,
            filtered_historical_price,
            filtered_future_prices,
            filtered_symbols,
        ) = ([], [], [], [])
        for i in range(0, len(features)):
            if len(features[i]) == most_common_length:
                filtered_features.append(features[i])
                filtered_symbols.append(symbol_names[i])
                filtered_historical_price.append(historical_price_info[i])
                filtered_future_prices.append(future_price_info[i])

        return (
            filtered_features,
            filtered_historical_price,
            filtered_future_prices,
            filtered_symbols,
        )
