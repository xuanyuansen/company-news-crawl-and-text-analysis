# -*- coding:utf-8 -*-
import logging
import sys

# from sklearn.feature_extraction.text import CountVectorizer
from information_extract import InformationExtract
from tokenization import Tokenization
import pandas as pd

# 显示所有列
pd.set_option("display.max_columns", None)
# 显示所有行
pd.set_option("display.max_rows", None)
pd.set_option("max_colwidth", 500)
# from Utils.utils import set_display

if __name__ == "__main__":
    # set_display()
    token_niz = Tokenization()
    info_extract = InformationExtract()
    if sys.argv[1] == "get_words":
        dict_of_words = info_extract.get_all_word_dictionary_of_new_data()
        info_extract.write_excel(dict_of_words, threshold=200)
    else:
        info_extract.build_2_class_classify_model(force_train_model=False)

        text_score = info_extract.predict_score(
            "◎记者 朱文彬 ○编辑 邱江上市公司遭实控人签署协议转让股权和出售" + "资产，作为重大事项，及时、准确地进行信息披露，本应是"
        )
        logging.info("test score is {0}".format(text_score))
        raw_data = info_extract.get_train_data_set()
        to_predict_data = raw_data[raw_data["ClassifyLabel"] == "unknown"]

        to_predict_labels = to_predict_data["ClassifyLabel"].values

        to_predict_data["text_cut"] = to_predict_data.apply(
            lambda row: " ".join(token_niz.cut_words(row["Title"] + row["Article"])),
            axis=1,
        )
        to_predict_features = to_predict_data["text_cut"].values
        count_v3 = info_extract.count_vector_rise

        counts_to_predict_data = count_v3.fit_transform(to_predict_features)

        tfidf_to_predict_data = info_extract.tfidf_transformer.fit(
            counts_to_predict_data
        ).transform(counts_to_predict_data)

        # 预测
        predict_result = info_extract.svm_model.predict(tfidf_to_predict_data)
        predict_proba = info_extract.svm_model.predict_proba(tfidf_to_predict_data)
        predict_proba_nb_label = info_extract.bayes_model.predict(tfidf_to_predict_data)
        predict_proba_nb = info_extract.bayes_model.predict_proba(tfidf_to_predict_data)
        for idx in range(0, len(predict_result)):
            print("----------------------------------------")
            print(
                "----nb--------{0}---------{1}--------".format(
                    predict_proba_nb_label[idx], predict_proba_nb[idx]
                )
            )
            print(
                "----svm--------{0}---------{1}--------\n{2}".format(
                    predict_result[idx],
                    predict_proba[idx],
                    to_predict_data[["Article", "Title"]].iloc[idx, :],
                )
            )
            print("----------------------------------------")
    pass
