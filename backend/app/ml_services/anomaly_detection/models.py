import torch.nn as nn

class LSTMAutoencoder(nn.Module):
    def __init__(self, n_features, hidden_dim=16):
        super(LSTMAutoencoder, self).__init__()
        self.encoder = nn.LSTM(n_features, hidden_dim, batch_first=True)
        self.decoder = nn.LSTM(hidden_dim, n_features, batch_first=True)
        
    def forward(self, x):
        _, (hidden, _) = self.encoder(x)
        hidden = hidden.permute(1, 0, 2)
        hidden = hidden.repeat(1, x.size(1), 1)
        out, _ = self.decoder(hidden)
        return out
