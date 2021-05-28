import logging

from sklearn.feature_extraction.text import CountVectorizer
from NlpModel.information_extract import InformationExtract
from NlpModel.tokenization import Tokenization
from Utils.utils import set_display

if __name__ == "__main__":
    set_display()
    token_niz = Tokenization()
    info_extract = InformationExtract()

    info_extract.build_2_class_classify_model()

    text_score = info_extract.predict_score(
        "◎记者 朱文彬 ○编辑 邱江上市公司遭实控人签署协议转让股权和出售" + "资产，作为重大事项，及时、准确地进行信息披露，本应是"
    )
    logging.info("test score is {0}".format(text_score))

    to_predict_data = info_extract.df[info_extract.df["ClassifyLabel"] == "unknown"]

    to_predict_labels = to_predict_data["ClassifyLabel"].values
    to_predict_features = to_predict_data["text_cut"].values
    count_v3 = CountVectorizer(
        vocabulary=info_extract.vocabulary, max_df=0.8, decode_error="ignore"
    )
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
            predict_result[idx],
            predict_proba[idx],
            to_predict_data[["Article", "Title"]].iloc[idx, :],
        )
        print("----------------------------------------")
    pass
