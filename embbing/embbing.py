import torch.nn as nn
import torch


class Ebbing(nn.Module):
    def __init__(self):
        super(Ebbing, self).__init__()
        self.embedding = nn.Embedding(512, 3)

    def forward(self, x):
        return self.embedding(x)


if __name__ == "__main__":
    model = Ebbing()
    number = torch.tensor([[1,2], [2,4], [3,2]])
    print(model(number))