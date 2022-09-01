import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
from TimeDistributed import TimeDistributed

class RNN(nn.Module):
    def __init__(self, embed_mat, opt):
        super(RNN, self).__init__()
        self.opt = opt
        
        D = opt['embed_dim']
        if opt['use_char_word'] or opt['use_word_char']:
            V_char = opt['char_embed_num']
            V_word = opt['word_embed_num']
            embedding_char = torch.from_numpy(embed_mat[:V_char])
            embedding_word = torch.from_numpy(embed_mat[:V_word])
            self.embed_char = nn.Embedding(V_char, D)
            self.embed_word = nn.Embedding(V_word, D)
            self.embed_char.weight.data.copy_(embedding_char)
            self.embed_word.weight.data.copy_(embedding_word)
        else:
            V = opt['embed_num']
            embedding = torch.from_numpy(embed_mat)
            self.embed = nn.Embedding(V, D)
            self.embed.weight.data.copy_(embedding)

        C = opt['class_num']
        dropout = opt['dropout']
        self.hidden_num = hidden_num = 512
        
        self.embed = nn.Embedding(V, D)
        self.embed.weight.data.copy_(embedding)
        
        self.tdfc1 = nn.Linear(D, 512)
        self.td1 = TimeDistributed(self.tdfc1)
        self.tdbn1 = nn.BatchNorm2d(1)
        
        self.tdfc2 = nn.Linear(D, 512)
        self.td2 = TimeDistributed(self.tdfc2)
        self.tdbn2 = nn.BatchNorm2d(1)
        
        self.rnn1 = nn.GRU(512, hidden_num, bidirectional=True, batch_first=True)
        self.rnn2 = nn.GRU(512, hidden_num, bidirectional=True, batch_first=True)
        
        self.fc1 = nn.Linear(hidden_num*4, 2000)
        self.bn1 = nn.BatchNorm1d(2000)
        self.fc2 = nn.Linear(2000, C)
        
    def forward(self, x, y):
        batch_size = x.size(0)

        if self.opt['use_char_word']:
            x = self.embed_char(x.long())
            y = self.embed_word(y.long())
        elif self.opt['use_word_char']:
            x = self.embed_word(x.long())
            y = self.embed_char(y.long())
        else:
            x = self.embed(x.long())
            y = self.embed(y.long())
        
        if self.opt['static']:
            x = x.detach()
        x = F.relu(self.tdbn1(self.td1(x).unsqueeze(1))).squeeze(1)
        
        if self.opt['static']:
            y = y.detach()
        y = F.relu(self.tdbn2(self.td2(y).unsqueeze(1))).squeeze(1)
        
        h0_1 = Variable(torch.randn(2, batch_size, self.hidden_num))
        if self.opt['cuda']:
            h0_1 = h0_1.cuda()
        _, z1 = self.rnn1(x, h0_1)
        x = z1[-2:].transpose(0, 1).contiguous().view(batch_size, -1)

        h0_2 = Variable(torch.randn(2, batch_size, self.hidden_num))
        if self.opt['cuda']:
            h0_2 = h0_2.cuda()
        _, z2 = self.rnn2(y, h0_2)
        y = z2[-2:].transpose(0, 1).contiguous().view(batch_size, -1)
        
        x = torch.cat((x, y), 1)
        
        x = F.relu(self.bn1(self.fc1(x)))
        logit = self.fc2(x)
        return logit
