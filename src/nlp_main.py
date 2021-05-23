from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC
import sys
from NlpUtils.information_extract import InformationExtract, random_sequence, calculate_result
from NlpUtils.tokenization import Tokenization
from Utils.utils import set_display

if __name__ == '__main__':
    set_display()
    token_niz = Tokenization()
    info_extract = InformationExtract()
    # result = info_extract.get_collection_word_seg(info_extract.collections[0])
    # for element in info_extract.collections:
    # print("{0} data count {1}".format(element, info_extract.get_count(element)))

    # info_extract.load_seg_word_label()
    print(info_extract.label[0:100])
    print(info_extract.label_pos)
    print(info_extract.label_neg)
    #
    # all_word = info_extract.get_all_word_dictionary()
    # print(all_word)

    info_extract.get_data()
    # print(info_extract.jrj_df[['Date', 'Title', 'Article', 'RuleLabel']][:200])
    # print(info_extract.nbd_df[['Date', 'Title', 'Article', 'RuleLabel']][:200])
    # print(info_extract.cn_stock_df[['Date', 'Title', 'Article', 'RuleLabel']][:200])

    # sys.exit(0)
    # info_extract.write_excel(all_word)
    # print(result)
    # 读数据
    # 从原始文本进行分类
    # filename = 'data/sms_spam.csv'
    data = info_extract.cn_stock_df

    data['text_cut'] = data.apply(lambda row: " ".join(token_niz.cut_words(row['Title']+row['Article'])), axis=1)
    # print(data[0:100])
    print(data.groupby('Category').size())
    print(data.shape)
    # 拆分训练数据集和测试数据集
    size = data.shape[0]
    sequence = random_sequence(round(size*0.3), size)
    sms_train_mask = [sequence[i] == 0 for i in range(size)]
    sms_train = data[sms_train_mask]
    sms_test_mask = [sequence[i] == 1 for i in range(size)]
    sms_test = data[sms_test_mask]

    # 文本转换成TF-IDF向量
    train_labels = sms_train['Category'].values
    train_features = sms_train['text_cut'].values
    count_v1 = CountVectorizer(max_df=0.8, decode_error='ignore')
    counts_train = count_v1.fit_transform(train_features)
    # print(count_v1.get_feature_names())
    # repr(counts_train.shape)
    tfidf_transformer = TfidfTransformer()
    tfidf_train = tfidf_transformer.fit(counts_train).transform(counts_train)

    test_labels = sms_test['Category'].values
    test_features = sms_test['text_cut'].values
    count_v2 = CountVectorizer(vocabulary=count_v1.vocabulary_, max_df=0.8, decode_error='ignore')
    counts_test = count_v2.fit_transform(test_features)
    tfidf_test = tfidf_transformer.fit(counts_test).transform(counts_test)

    # 训练
    clf = MultinomialNB(alpha=0.01)
    clf.fit(tfidf_train, train_labels)

    # 预测
    predict_result = clf.predict(tfidf_test)
    # print(predict_result)

    # 正确率
    correct = [test_labels[i] == predict_result[i] for i in range(len(predict_result))]
    r = len(predict_result)
    t = correct.count(True)
    f = correct.count(False)
    print("测试集大小{0} 分类正确{1} 分类错误{2} 准确率{3}".format(r, t, f, t / float(r)))

    svc_lf = SVC(kernel='linear')  # default with 'rbf'
    svc_lf.fit(tfidf_train, train_labels)
    pred = svc_lf.predict(tfidf_test)
    calculate_result(test_labels, pred)

    pass
