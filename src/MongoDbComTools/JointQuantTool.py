# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
from jqdatasdk import __version__
from jqdatasdk import auth, is_auth, get_query_count, get_all_securities
from Utils import config
from cryptography.fernet import Fernet
import logging
import pandas as pd


class JointQuantTool(object):
    def __init__(self):
        self.account = b"gAAAAABgsGvpKHcpU381JQ4z-bmo4AhIzYO6OVKguG1ZyZfJDKvLFb_xc8bB6lBDeaDRoyxzY1-QXfhtdNZ7UT-YZAVeoGTMwQ=="
        self.pass_word = b"gAAAAABgwF2bvKX1IFzv6jW6-uofbNWvt-Thoktd_pEUNeCL3UkaFewmEtzUX_KFe3YnjMlf9M3m4fGiEo-NkvzGktTo8QUfe-RPn4GFW2jK9FtLY6lXOiY="
        self.__init_account()
        self.all_stock = None
        self.__set_display()

    def __set_display(self):
        # 显示所有列
        pd.set_option("display.max_columns", None)
        # 显示所有行
        pd.set_option("display.max_rows", None)
        pd.set_option("max_colwidth", 500)

    def __init_account(self):
        _cipher = Fernet(config.cipher_key)
        _account = str(_cipher.decrypt(self.account), encoding="utf-8")
        _password = str(_cipher.decrypt(self.pass_word), encoding="utf-8")
        auth(_account, _password)
        logging.info(is_auth())
        logging.info(__version__)
        logging.info(get_query_count())
        return True

    def get_all_stock(self):
        self.all_stock = get_all_securities()
        return self.all_stock

    pass


if __name__ == "__main__":
    # _cipher = Fernet(config.cipher_key)
    # encrypted_text = _cipher.encrypt(b'Fighton.jukuan999')
    # print(encrypted_text)
    tool = JointQuantTool()
    info = tool.get_all_stock()
    print(info)
    pass
