import torch
import torch.autograd as autograd
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

# CNN model for relation classification
class Size_info:
    def __init__(self, label_size, word_embed_size, entpos_size,
                 numpos_size, max_len):
        self.label_size = int(label_size)
        self.word_embed_size = int(word_embed_size)
        self.entpos_size = int(entpos_size)
        self.numpos_size = int(numpos_size)
        self.max_len = int(max_len)

class Conv_relation_extractor(nn.Module):
    def __init__(self, config, size_info):
        super(Conv_relation_extractor, self).__init__()
        # reading parameters from config
        # import pdb; pdb.set_trace()
        word_embed_dim  = config.getint('CNN', 'word_embed_dim')
        pos_embed_dim   = config.getint('CNN', 'pos_embed_dim')
        total_embed_dim = word_embed_dim + (2 * pos_embed_dim)

        filter_num      = config.getint('CNN', 'filter_num')
        kernel_sizes    = config.get('CNN', 'kernel_sizes')
        kernel_sizes = kernel_sizes.split(' ')
        self.kernel_sizes = [int(x) for x in kernel_sizes]
        free_layer_size = config.getint('CNN', 'free_layer_size')
        output_size     = size_info.label_size
        dropput         = config.getfloat('CNN', 'dropput')

        self.max_len = size_info.max_len
        self.embed_word = nn.Embedding(size_info.word_embed_size, word_embed_dim)
        self.embed_entpos  = nn.Embedding(size_info.entpos_size, pos_embed_dim)
        self.embed_numpos  = nn.Embedding(size_info.numpos_size, pos_embed_dim)

        # adding conv filters
        self.convs = []
        for i in range(len(self.kernel_sizes)):
            conv = nn.Conv1d(1, filter_num, total_embed_dim * self.kernel_sizes[i], stride=total_embed_dim)
            self.convs.append(conv)
        self.dropout = nn.Dropout(dropput)
        self.linear1 = nn.Linear(len(self.kernel_sizes) * filter_num, free_layer_size)
        self.linear2 = nn.Linear(free_layer_size, output_size)

    def forward(self, inp):
        word_embed = self.embed_word(inp.word)
        ent_pos_embed = self.embed_entpos(inp.pos1)
        num_pos_embed = self.embed_numpos(inp.pos2)
        x = torch.cat( (word_embed, ent_pos_embed, num_pos_embed), 1)
        conv_results = [
            F.max_pool1d(F.relu(self.convs[i]), self.max_len - self.kernel_sizes[i] + 1)
                .view(-1, self.kernel_sizes[i])
            for i in range(len(self.kernel_sizes))]

        x = torch.cat(conv_results, 1)
        x = self.dropout(x)
        x = self.linear1(x)
        x = F.relu(x)
        x = self.dropout(x)
        x = self.linear2(x)
        x = nn.SoftMax(x)
        return x
