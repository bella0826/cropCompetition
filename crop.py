import torch
import os
import timm
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import matplotlib.pyplot as plt
from torch.autograd import Variable
from torch.utils.data import Dataset, DataLoader, random_split
from torchvision import models, transforms, datasets
import numpy as np
import time

root_path = "../YuAn/crops_dataset/"
EPOCHS = 20
device = torch.device("cuda:1" if torch.cuda.is_available() else "cpu")
print(device)

resize = 320
#center_crop = 224
data_transform = transforms.Compose([
    transforms.Resize((resize, resize)),
    transforms.ToTensor()
])

train_data = datasets.ImageFolder(root_path, transform = data_transform)
print(train_data.classes)

#train_data, valid_data = torch.utils.data.random_split(dataset = data, lengths = [train_size, valid_size])
train_loader = DataLoader(dataset = train_data, batch_size = 20, shuffle = True)
#valid_loader = DataLoader(dataset = valid_data, batch_size = 16, shuffle = True, num_workers = 2)

# dataset_size = len(train_data)
# print('\ndataset_size =', dataset_size)
# val_size = len(valid_data)
# print('\nval_size =', val_size)

def build_model():
    model = timm.create_model("convnext_base", pretrained = True, num_classes = 33)
    for name, param in model.named_parameters():
        param.requires_grad = True
    # 提取fully-connected layer中固定的參數
    # number od crops = 33
    print(model.get_classifier())
    model = model.to(device)
    print(model)
    return model

def train(model, x_train, epochs, batch_size=8):
    def acc_cal(pred, t):
        matrix = np.argmax(pred, axis=1)
        compare = matrix - t
        accuracy = (t.shape[0] - np.count_nonzero(compare)) / t.shape[0]
        return accuracy

    criterion = nn.CrossEntropyLoss().to(device)
    optimizer = optim.Adam(model.parameters())
    train_state = []
    torch.cuda.empty_cache()
    early_stopping_count = -1
    early_stopping_loss = 0
    all_time = time.time()
    for epoch in range(epochs):
        epoch_t = time.time()
        train_loss, train_acc = 0, 0
        val_loss, val_acc = 0, 0
        count, count2 = 0, 0
        dicts = {}
        for x_batch, y_batch in x_train:
            optimizer.zero_grad()
            batch_data = x_batch.to(device)
            target = y_batch.to(device)
            outputs = model(batch_data)
            loss = criterion(outputs, target)
            train_loss += loss.item()
            train_pred = outputs.detach().cpu().numpy()
            train_trg = target.cpu().numpy()
            acc = acc_cal(train_pred, train_trg)
            train_acc += acc
            count += 1
            loss.backward()
            optimizer.step()
            if count % 10 == 0:
                batch_t = time.time()
                t = round(batch_t - epoch_t)
                loss_per_10_batch = round(train_loss/count, 5)
                acc_per_10_batch = round(train_acc/count, 5)
                print("[{}] {}/{} loss:{:>9.5f}, acc:{:>9.5f}, ---cost time: {}s".format(epoch, count, len(x_train), loss_per_10_batch, acc_per_10_batch, t), end="\r")
        avg_loss = train_loss / count
        avg_acc = train_acc / count
        t = time.time() - all_time
        print("[{}] {}/{} loss:{:>9.5f}, acc:{:>9.5f}, ---cost time: {}s".format(epoch, len(x_train), len(x_train), round(avg_loss, 5), round(avg_acc, 5), t))
        dicts["train_loss"] = avg_loss
        dicts["train_acc"] = avg_acc
        if early_stopping_loss < avg_loss:
            early_stopping_count += 1
            torch.save(model.state_dict(), f"./path/timm_model_{epoch}({early_stopping_count}).pth")
            if early_stopping_count >= 3:
                return model
        else:
            early_stopping_count = 0
        early_stopping_loss = avg_loss
    print('Finished Training')
    return train_state

model = build_model()
criterion = nn.CrossEntropyLoss().to(device)
optimizer = optim.Adam(model.parameters())
train_state = train(model, train_loader, epochs=EPOCHS, batch_size=30)
torch.save(model.state_dict(),'./convnext_base.pth')






