
import torch

import pandas as pd
from torch.utils.data import Dataset, DataLoader
from transformers import BartTokenizer, BartForSequenceClassification

train_df = pd.read_csv('ratings_train.txt', sep='\t')
test_df = pd.read_csv('ratings_test.txt', sep='\t')
train_df.dropna(inplace=True)
test_df.dropna(inplace=True)

train_df = train_df.sample(frac=0.4, random_state=999)
test_df = test_df.sample(frac=0.4, random_state=999)


class NsmcDataset(Dataset):
    ''' Naver Sentiment Movie Corpus Dataset '''

    def __init__(self, df):
        self.df = df

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        text = self.df.iloc[idx, 1]
        label = self.df.iloc[idx, 2]
        return text, label


nsmc_train_dataset = NsmcDataset(train_df)
print(nsmc_train_dataset.__getitem__(0))
train_loader = DataLoader(nsmc_train_dataset, batch_size=1, shuffle=True, num_workers=2)

tokenizer = BartTokenizer.from_pretrained('facebook/bart-large')
model = BartForSequenceClassification.from_pretrained('facebook/bart-large')
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)
import torch.nn.functional as F

optimizer = torch.optim.Adam(model.parameters(), lr=1e-6)

itr = 1
p_itr = 500
epochs = 2
total_loss = 0
total_len = 0
total_correct = 0

model.train()
for epoch in range(epochs):

    for text, label in train_loader:
        optimizer.zero_grad()

        # encoding and zero padding
        encoded_list = [tokenizer.encode(t, add_special_tokens=True) for t in text]
        padded_list = [e + [0] * (512 - len(e)) for e in encoded_list]

        sample = torch.tensor(padded_list)
        sample, label = sample.to(device), label.to(device)
        labels = torch.tensor(label)
        outputs = model(sample, labels=labels)
        loss = outputs.loss
        logits = outputs.logits

        pred = torch.argmax(F.softmax(logits), dim=1)
        correct = pred.eq(labels)
        total_correct += correct.sum().item()
        total_len += len(labels)
        total_loss += loss.item()
        loss.backward()
        optimizer.step()

        if itr % p_itr == 0:
            print('[Epoch {}/{}] Iteration {} -> Train Loss: {:.4f}, Accuracy: {:.3f}'.format(epoch + 1, epochs, itr,
                                                                                              total_loss / p_itr,
                                                                                              total_correct / total_len))
            total_loss = 0
            total_len = 0
            total_correct = 0

        itr += 1

model.eval()  # test mode로 변경, dropout같은 함수가 적용 될지 안될지 결정
# iterate over test data
nsmc_eval_dataset = NsmcDataset(test_df)
test_loader = DataLoader(nsmc_eval_dataset, batch_size=1, shuffle=False, num_workers=2)
total_loss = 0
total_len = 0
total_correct = 0

for text, label in test_loader:
    encoded_list = [tokenizer.encode(t, add_special_tokens=True) for t in text]
    padded_list = [e + [0] * (512 - len(e)) for e in encoded_list]
    sample = torch.tensor(padded_list)
    sample, label = sample.to(device), label.to(device)
    labels = torch.tensor(label)
    outputs = model(sample, labels=labels)
    _, logits = outputs

    pred = torch.argmax(F.softmax(logits), dim=1)
    correct = pred.eq(labels)
    total_correct += correct.sum().item()
    total_len += len(labels)

print('Test accuracy: ', total_correct / total_len)

