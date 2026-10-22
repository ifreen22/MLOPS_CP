import torch
import torch.nn as nn
import torch.nn.functional as F

class GCN(nn.Module):
    """
    Pure PyTorch implementation of Graph Convolutional Network.
    Formula: Z = D^-0.5 A_hat D^-0.5 X W
    """
    def __init__(self, num_node_features, hidden_dim, num_nodes):
        super(GCN, self).__init__()
        self.num_nodes = num_nodes
        self.conv1 = nn.Linear(num_node_features, hidden_dim)
        self.conv2 = nn.Linear(hidden_dim, hidden_dim)
        
        # Flatten graph output into classification head
        self.fc = nn.Linear(hidden_dim * num_nodes, num_nodes)

    def forward(self, x, a_norm):
        # x shape: (batch, num_nodes, features)
        # a_norm shape: (num_nodes, num_nodes)
        
        # Message passing 1
        x = torch.matmul(a_norm, x) # Aggregate neighbors
        x = F.relu(self.conv1(x))   # Transform
        x = F.dropout(x, p=0.3, training=self.training)
        
        # Message passing 2
        x = torch.matmul(a_norm, x)
        x = F.relu(self.conv2(x))
        
        # Flatten and classify which node is root cause
        x = x.view(x.size(0), -1) 
        out = self.fc(x)
        return out

class GraphSAGE(nn.Module):
    """
    Pure PyTorch implementation of GraphSAGE (Mean Aggregator).
    Formula: h_v = W * concat(h_v, mean({h_u for u in neighbors}))
    """
    def __init__(self, num_node_features, hidden_dim, num_nodes):
        super(GraphSAGE, self).__init__()
        self.num_nodes = num_nodes
        # W maps concatenated [self_feat, neighbor_feat] -> hidden_dim
        self.sage1 = nn.Linear(num_node_features * 2, hidden_dim)
        self.sage2 = nn.Linear(hidden_dim * 2, hidden_dim)
        
        self.fc = nn.Linear(hidden_dim * num_nodes, num_nodes)

    def forward(self, x, a_adj):
        # We need the strict adjacency matrix (without self loops) to get neighbor means
        # A_adj shape: (num_nodes, num_nodes)
        
        # SAGE Layer 1
        neighbor_sum = torch.matmul(a_adj, x)
        degree = a_adj.sum(dim=1, keepdim=True).clamp(min=1)
        neighbor_mean = neighbor_sum / degree
        concat_1 = torch.cat([x, neighbor_mean], dim=-1)
        h1 = F.relu(self.sage1(concat_1))
        h1 = F.dropout(h1, p=0.3, training=self.training)
        
        # SAGE Layer 2
        neighbor_sum2 = torch.matmul(a_adj, h1)
        neighbor_mean2 = neighbor_sum2 / degree
        concat_2 = torch.cat([h1, neighbor_mean2], dim=-1)
        h2 = F.relu(self.sage2(concat_2))
        
        # Readout
        h2 = h2.view(h2.size(0), -1)
        out = self.fc(h2)
        return out
        
class GAT(nn.Module):
    """
    Simplified Graph Attention Network using PyTorch.
    """
    def __init__(self, num_node_features, hidden_dim, num_nodes):
        super(GAT, self).__init__()
        self.num_nodes = num_nodes
        self.W1 = nn.Linear(num_node_features, hidden_dim, bias=False)
        self.a1 = nn.Parameter(torch.empty(size=(2*hidden_dim, 1)))
        nn.init.xavier_uniform_(self.a1.data, gain=1.414)
        
        self.fc = nn.Linear(hidden_dim * num_nodes, num_nodes)

    def forward(self, x, a_adj):
        batch_size = x.size(0)
        h = self.W1(x) # (batch, N, hidden)
        
        # Create attention mechanism (inefficient loop for simplicity)
        out_h = torch.zeros_like(h)
        for b in range(batch_size):
            # We want to compute e_ij = LeakyReLU(a^T [Whi || Whj])
            h_b = h[b]
            N = self.num_nodes
            
            # Broadcast concat
            h_repeat = h_b.repeat(N, 1)
            h_repeat_interleave = h_b.repeat_interleave(N, dim=0)
            concat_h = torch.cat([h_repeat_interleave, h_repeat], dim=1) # (N*N, 2*hidden)
            
            e = F.leaky_relu(torch.matmul(concat_h, self.a1).squeeze(-1))
            e = e.view(N, N)
            
            # Mask out non-edges
            zero_vec = -9e15 * torch.ones_like(e)
            attention = torch.where(a_adj > 0, e, zero_vec)
            attention = F.softmax(attention, dim=1)
            
            out_h[b] = torch.matmul(attention, h_b)
            
        out_h = F.relu(out_h)
        out_h = out_h.view(batch_size, -1)
        return self.fc(out_h)
