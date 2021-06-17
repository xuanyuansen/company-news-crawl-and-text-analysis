# -*- coding: UTF-8 -*-
# https://gitee.com/quarky/pytorch-sentiment-analysis/blob/master/4%20-%20Convolutional%20Sentiment%20Analysis.ipynb
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
import os
import pandas as pd

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class RNN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(RNN, self).__init__()

        self.hidden_size = hidden_size

        self.i2h = nn.Linear(input_size + hidden_size, hidden_size)
        self.i2o = nn.Linear(input_size + hidden_size, output_size)
        self.softmax = nn.LogSoftmax(dim=1)

    def forward(self, input, hidden):
        combined = torch.cat((input, hidden), 1)
        hidden = self.i2h(combined)
        output = self.i2o(combined)
        output = self.softmax(output)
        return output, hidden

    def initHidden(self):
        return torch.zeros(1, self.hidden_size)

    pass


def line_to_tensor(data: list[list]):
    tensor = torch.zeros(len(data), 1, len(data[0]))
    for li, letter in enumerate(data):
        tensor[li][0] = torch.from_numpy(np.array(letter))
    return tensor


def random_training_example(data: list[list], label):
    category_tensor = torch.tensor([label], dtype=torch.long)
    line_tensor = line_to_tensor(data)
    return label, category_tensor, line_tensor


def category_from_output(output):
    top_n, top_i = output.topk(1)
    print(top_n)
    print(top_i)
    category_i = top_i[0].item()
    return category_i, category_i


def train_rnn(rnn: RNN, category_tensor, line_tensor):
    learning_rate = 0.001  # If you set this too high, it might explode. If too low, it might not learn
    hidden = rnn.initHidden()

    rnn.zero_grad()

    for i in range(line_tensor.size()[0]):
        output, hidden = rnn(line_tensor[i], hidden)
    # print('output', output)
    criterion = nn.NLLLoss()
    loss = criterion(output, category_tensor)
    loss.backward()

    # Add parameters' gradients to their values, multiplied by learning rate
    for p in rnn.parameters():
        p.data.add_(p.grad.data, alpha=-learning_rate)

    return output, loss.item()


###################################
# text cnn
# N*W的数据
class CustomChanDataset(Dataset):
    def __init__(
        self,
        feature_data_frame: pd.DataFrame,
        label_data_frame: pd.DataFrame,
        max_feature_length: int,
    ):
        # assert feature_data_frame.shape[0] == label_data_frame.shape[0]
        self.feature_data: pd.DataFrame = feature_data_frame
        self.max_feature_length = max_feature_length
        self.label: pd.DataFrame = label_data_frame
        self.idx_list = list(self.feature_data.index)

    def __len__(self):
        return self.feature_data.shape[0]

    # 这个地方做了补零
    def __getitem__(self, idx):
        origin_idx = self.idx_list[idx]
        # img_path = os.path.join(self.img_dir, self.img_labels.iloc[idx, 0])
        raw_feature = self.feature_data.loc[origin_idx, ["features"]].values.tolist()[0]
        # print(raw_feature)
        feature = raw_feature[0]
        # print("feature 0 {} ".format(feature))
        industry_feature = raw_feature[1]
        # print("industry_feature  {} ".format(industry_feature))
        concept_feature = raw_feature[2]
        # print("concept_feature {} ".format(concept_feature))

        tensor_industry = torch.from_numpy(np.array(industry_feature)).to(device)
        tensor_concept = torch.from_numpy(np.array(concept_feature)).to(device)

        # feature list[list]
        tensor_feature: torch.Tensor = torch.zeros(
             self.max_feature_length, len(feature[0])
        )

        print(tensor_feature.shape)
        for idx in range(0, len(feature) - 1):
            gap = self.max_feature_length - len(feature)
            tensor_feature[idx+gap] = torch.from_numpy(np.array(feature[idx]))

        print(tensor_feature.shape)
        print(tensor_feature.t().shape)
        label = self.label.loc[origin_idx]
        label_tensor = torch.tensor(label, dtype=torch.long).to(device)
        return (tensor_feature.t().to(device), tensor_industry, tensor_concept), label_tensor


class TextCNN(nn.Module):
    def __init__(self, args, max_feature_length: int, vocab_industry: int, vocab_concept: int):
        super(TextCNN, self).__init__()
        self.args = args
        # 对应vocab 就是sequence最大的长度 max_length
        # 输入就是 max_length*6
        vocab = max_feature_length
        dim = args.embed_dim  # 每个词向量长度
        class_num = args.class_num  # 类别数
        channel = 1  # 输入的channel数
        kernel_num = args.kernel_num  # 每种卷积核的数量
        Ks = args.kernel_sizes  # 卷积核list，形如[2,3,4]
        # self.embed = nn.Embedding(vocab, dim)  # 词向量，这里直接随机
        # 这里改用 nn.EmbeddingBag 就不用padding
        # self.embedding = nn.EmbeddingBag(vocab, dim, sparse=True)
        self.embedding_i = nn.Embedding(vocab_industry, dim, sparse=False).to(device)
        self.embedding_c = nn.Embedding(vocab_concept, dim, sparse=False).to(device)
        self.fc_base = nn.Linear(vocab, dim).to(device)

        self.convolutions = nn.ModuleList(
            [nn.Conv2d(channel, kernel_num, (K, dim)) for K in Ks]
        ).to(device)  # 卷积层
        self.dropout = nn.Dropout(args.dropout).to(device)
        self.fc = nn.Linear(len(Ks) * kernel_num, class_num).to(device)  # 全连接层
        self.init_weights()

    def init_weights(self):
        init_range = 0.5
        self.embedding_i.weight.data.uniform_(-init_range, init_range)
        self.embedding_c.weight.data.uniform_(-init_range, init_range)
        self.fc.weight.data.uniform_(-init_range, init_range)
        self.fc.bias.data.zero_()
        self.fc_base.weight.data.uniform_(-init_range, init_range)
        self.fc_base.bias.data.zero_()

    # bi 对应的data是N*6的
    def forward(self, _input):
        # x = self.embed(x)  # (N,W,D)
        # print("_input[0].shape {}".format(_input[0].shape))
        # print("_input[1].shape {}".format(_input[1].shape))
        # print("_input[2].shape {}".format(_input[2].shape))
        x = self.fc_base(_input[0])
        # print(x.shape)
        em_industry = self.embedding_i(_input[1])
        # print(em_industry.shape)
        em_concept = self.embedding_c(_input[2])
        # print(em_concept.shape)
        x = torch.cat((x, em_industry, em_concept), dim=1)
        # Ex = self.embedding(x, offsets)

        x = x.unsqueeze(1)  # (N,Ci,W,D)
        x = [
            F.relu(conv(x)).squeeze(3) for conv in self.convolutions
        ]  # len(Ks)*(N, K_num,W)
        x = [
            F.max_pool1d(line, line.size(2)).squeeze(2) for line in x
        ]  # len(Ks)*(N, K_num)

        x = torch.cat(x, 1)  # (N, K_num*len(Ks))

        x = self.dropout(x)
        logit = self.fc(x)
        return logit


# https://pytorch.org/tutorials/beginner/text_sentiment_ngrams_tutorial.html
def save(model, save_dir, save_prefix, steps):
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    save_prefix = os.path.join(save_dir, save_prefix)
    save_path = "{}_steps_{}.pt".format(save_prefix, steps)
    torch.save(model.state_dict(), save_path)


# 这里已经处理好了
def process_data(_data: Dataset):
    train_data_loader = DataLoader(_data, batch_size=64, shuffle=True)
    train_features, train_labels = next(iter(train_data_loader))
    print(f"Feature batch shape: {train_features.size()}")
    print(f"Labels batch shape: {train_labels.size()}")
    feature = train_features[0].squeeze()
    label = train_labels[0]
    print(feature)
    print(f"Label: {label}")
    pass


def evaluate(data_iter: Dataset, model):
    print("evaluating...")
    model.eval()
    corrects, avg_loss = 0, 0

    eval_data_loader = DataLoader(data_iter, batch_size=16, shuffle=True)
    it = iter(eval_data_loader)
    # 循环:
    while True:
        try:
            # 获得下一个值:
            feature, target = next(it)
            if "cuda" == device:
                feature = feature.cuda()
                target = target.cuda()

            # feature, target = batch.text, batch.label
            # feature.data.t_()

            # if args.cuda:
            #     feature, target = feature.cuda(), target.cuda()

            logit = model(feature)
            loss = F.cross_entropy(logit, target)

            avg_loss += loss.item()
            result = torch.max(logit, 1)[1]
            corrects += (result.view(target.size()) == target.data).sum()
        except StopIteration:
            # 遇到StopIteration就退出循环
            break

    size = len(data_iter)
    avg_loss /= size
    accuracy = 100.0 * corrects / size
    print(
        "\nEvaluation - loss: {:.6f} acc: {:.4f} % ({}/{}) \n".format(
            avg_loss, accuracy, corrects, size
        )
    )

    return accuracy


# args.lr
# args.epochs
# args.log_interval
# args.dev_interval
# args.save_best
# args.save_dir
# args.save_interval
def train(train_data_set, eval_data_set, batch_size, model: TextCNN, args):
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    steps = 0
    best_acc = 0
    last_step = 0
    # set model to training mode
    model.train()
    print("training...")
    for epoch in range(1, args.epochs + 1):
        eval_data_loader = DataLoader(
            train_data_set, batch_size=batch_size, shuffle=True
        )
        it = iter(eval_data_loader)
        while True:
            try:
                # 获得下一个值:
                feature, target = next(it)  # (W,N) (N)
                # feature.data.t_()
                if "cuda" == device:
                    feature = feature.cuda()
                    target = target.cuda()

                optimizer.zero_grad()
                logit = model(feature)
                loss = F.cross_entropy(logit, target)
                loss.backward()
                optimizer.step()

                steps += 1
                if steps % args.log_interval == 0:
                    result = torch.max(logit, 1)[1].view(target.size())
                    corrects = (result.data == target.data).sum()
                    accuracy = corrects * 100.0 / batch_size
                    sys.stdout.write(
                        "\rBatch[{}] - loss: {:.6f} acc: {:.4f}%  ({}/{})\n".format(
                            steps, loss.data.item(), accuracy, corrects, batch_size
                        )
                    )
                if steps % args.dev_interval == 0:
                    dev_acc = evaluate(eval_data_set, model)
                    if dev_acc > best_acc:
                        best_acc = dev_acc
                        last_step = steps
                        if args.save_best:
                            save(model, args.save_dir, "best", steps)
                    else:
                        if steps - last_step >= args.early_stop:
                            print("early stop by {} steps.".format(args.early_stop))
                elif steps % args.save_interval == 0:
                    save(model, args.save_dir, "snapshot", steps)
            except StopIteration:
                break
    pass
