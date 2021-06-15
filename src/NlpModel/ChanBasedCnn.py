# -*- coding: UTF-8 -*-
# https://gitee.com/quarky/pytorch-sentiment-analysis/blob/master/4%20-%20Convolutional%20Sentiment%20Analysis.ipynb
import sys

import numpy
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torch.utils.data import Dataset
from torchvision import datasets
from torchvision.transforms import ToTensor
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader
import os
import pandas as pd
from torchvision.io import read_image
import argparse
from torchtext import data


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
    category_i = top_i[0].item()
    return category_i, category_i


def train_rnn(rnn: RNN, category_tensor, line_tensor):
    learning_rate = 0.005  # If you set this too high, it might explode. If too low, it might not learn
    hidden = rnn.initHidden()

    rnn.zero_grad()

    for i in range(line_tensor.size()[0]):
        output, hidden = rnn(line_tensor[i], hidden)

    criterion = nn.NLLLoss()
    loss = criterion(output, category_tensor)
    loss.backward()

    # Add parameters' gradients to their values, multiplied by learning rate
    for p in rnn.parameters():
        p.data.add_(p.grad.data, alpha=-learning_rate)

    return output, loss.item()


# N*W的数据
class CustomChanDataset(Dataset):
    def __init__(self, feature_data_frame: pd.DataFrame, label_data_frame: pd.DataFrame):
        assert feature_data_frame.shape[0] == label_data_frame.shape[0]
        self.feature_data: pd.DataFrame = feature_data_frame
        self.label: pd.DataFrame = label_data_frame

    def __len__(self):
        return self.feature_data.shape[0]

    def __getitem__(self, idx):
        # img_path = os.path.join(self.img_dir, self.img_labels.iloc[idx, 0])
        image = self.feature_data.iloc[idx, :]
        label = self.label.iloc[idx, 0]
        return image, label


def process_data(data: list[np.ndarray]):
    training_data = datasets.FashionMNIST(
        root="data",
        train=True,
        download=True,
        transform=ToTensor()
    )
    print(type(training_data))
    test_data = datasets.FashionMNIST(
        root="data",
        train=False,
        download=True,
        transform=ToTensor()
    )
    print(type(test_data))

    train_dataloader = DataLoader(training_data, batch_size=64, shuffle=True)
    test_dataloader = DataLoader(test_data, batch_size=64, shuffle=True)

    train_features, train_labels = next(iter(train_dataloader))
    print(f"Feature batch shape: {train_features.size()}")
    print(f"Labels batch shape: {train_labels.size()}")
    img = train_features[0].squeeze()
    label = train_labels[0]
    plt.imshow(img, cmap="gray")
    plt.show()
    print(f"Label: {label}")

    # _tensor = torch.from_numpy(data)
    pass


# https://pytorch.org/tutorials/beginner/text_sentiment_ngrams_tutorial.html
class TextClassificationModel(nn.Module):
    """
    The model is composed of the nn.EmbeddingBag layer plus a linear layer for the classification purpose.
     nn.EmbeddingBag with the default mode of “mean” computes the mean value of a “bag” of embeddings.
     Although the text entries here have different lengths,
      nn.EmbeddingBag module requires no padding here since the text lengths are saved in offsets.

    Additionally, since nn.EmbeddingBag accumulates the average across the embeddings on the fly,
    nn.EmbeddingBag can enhance the performance and memory efficiency to process a sequence of tensors.
    """
    def __init__(self, vocab_size, embed_dim, num_class):
        super(TextClassificationModel, self).__init__()
        self.embedding = nn.EmbeddingBag(vocab_size, embed_dim, sparse=True)
        self.fc = nn.Linear(embed_dim, num_class)
        self.init_weights()

    def init_weights(self):
        initrange = 0.5
        self.embedding.weight.data.uniform_(-initrange, initrange)
        self.fc.weight.data.uniform_(-initrange, initrange)
        self.fc.bias.data.zero_()

    def forward(self, text, offsets):
        embedded = self.embedding(text, offsets)
        return self.fc(embedded)


def save(model, save_dir, save_prefix, steps):
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    save_prefix = os.path.join(save_dir,save_prefix)
    save_path = '{}_steps_{}.pt'.format(save_prefix,steps)
    torch.save(model.state_dict(),save_path)


def evaluate(data_iter, model, args):
    model.eval()
    corrects, avg_loss = 0, 0
    for batch in data_iter:
        feature, target = batch.text, batch.label
        feature.data.t_()

        if args.cuda:
            feature, target = feature.cuda(), target.cuda()

        logit = model(feature)
        loss = F.cross_entropy(logit, target)

        avg_loss += loss.data[0]
        result = torch.max(logit, 1)[1]
        corrects += (result.view(target.size()).data == target.data).sum()

    size = len(data_iter.dataset)
    avg_loss /= size
    accuracy = 100.0 * corrects / size
    print('\nEvaluation - loss: {:.6f} acc: {:.4f}%({}/{}) \n'.format(avg_loss, accuracy, corrects, size))

    return accuracy


def train(train_iter, dev_iter, model, args):
    if args.cuda:
        model.cuda(args.device)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    steps = 0
    best_acc = 0
    last_step = 0
    model.train()
    print('training...')
    for epoch in range(1, args.epochs + 1):
        for batch in train_iter:
            feature, target = batch.text, batch.label  # (W,N) (N)
            feature.data.t_()

            if args.cuda:
                feature, target = feature.cuda(), target.cuda()

            optimizer.zero_grad()
            logit = model(feature)
            loss = F.cross_entropy(logit, target)
            loss.backward()
            optimizer.step()

            steps += 1
            if steps % args.log_interval == 0:
                result = torch.max(logit, 1)[1].view(target.size())
                corrects = (result.data == target.data).sum()
                accuracy = corrects * 100.0 / batch.batch_size
                sys.stdout.write('\rBatch[{}] - loss: {:.6f} acc: {:.4f}$({}/{})'.format(steps,
                                                                                         loss.data.item(),
                                                                                         accuracy,
                                                                                         corrects,
                                                                                         batch.batch_size))
            if steps % args.dev_interval == 0:
                dev_acc = evaluate(dev_iter, model, args)
                if dev_acc > best_acc:
                    best_acc = dev_acc
                    last_step = steps
                    if args.save_best:
                        save(model, args.save_dir, 'best', steps)
                else:
                    if steps - last_step >= args.early_stop:
                        print('early stop by {} steps.'.format(args.early_stop))
            elif steps % args.save_interval == 0:
                save(model, args.save_dir, 'snapshot', steps)


class TextCNN(nn.Module):
    def __init__(self, args):
        super(TextCNN, self).__init__()
        self.args = args

        # vocab = args.embed_num   # 已知词的数量
        dim = args.embed_dim  # 每个词向量长度
        class_num = args.class_num  # 类别数
        channel = 1  # 输入的channel数
        kernel_num = args.kernel_num  # 每种卷积核的数量
        Ks = args.kernel_sizes  # 卷积核list，形如[2,3,4]

        # self.embed = nn.Embedding(vocab, dim)  # 词向量，这里直接随机
        # 第一层直接改成全连接层
        self.fc_base = nn.Linear(6, dim)  # 全连接层

        self.convs = nn.ModuleList(
            [nn.Conv2d(channel, kernel_num, (K, dim)) for K in Ks]
        )  # 卷积层
        self.dropout = nn.Dropout(args.dropout)
        self.fc = nn.Linear(len(Ks) * kernel_num, class_num)  #全连接层

    # bi 对应的data是N*6的
    def forward(self, x):
        # x = self.embed(x)  # (N,W,D)
        x = self.fc_base(x)

        x = x.unsqueeze(1)  # (N,Ci,W,D)
        x = [F.relu(conv(x)).squeeze(3) for conv in self.convs]  # len(Ks)*(N,Knum,W)
        x = [
            F.max_pool1d(line, line.size(2)).squeeze(2) for line in x
        ]  # len(Ks)*(N,Knum)

        x = torch.cat(x, 1)  # (N,Knum*len(Ks))

        x = self.dropout(x)
        logit = self.fc(x)
        return logit


