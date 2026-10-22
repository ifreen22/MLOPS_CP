import numpy as np
import networkx as nx
import torch

class SockShopGraphBuilder:
    def __init__(self, seed=42):
        np.random.seed(seed)
        torch.manual_seed(seed)
        
        # Define the 7 core Sock Shop microservices
        self.services = [
            "frontend", "orders", "payment", 
            "user", "catalogue", "cart", "shipping"
        ]
        
        # Build Directed Acyclic Graph (DAG) dependencies
        self.edges = [
            ("frontend", "orders"),
            ("frontend", "user"),
            ("frontend", "catalogue"),
            ("frontend", "cart"),
            ("orders", "payment"),
            ("orders", "shipping"),
            ("cart", "catalogue")
        ]
        
        self.node_to_idx = {name: idx for idx, name in enumerate(self.services)}
        self.idx_to_node = {idx: name for idx, name in enumerate(self.services)}
        self.num_nodes = len(self.services)
        
        self.G = nx.DiGraph()
        self.G.add_nodes_from(self.services)
        self.G.add_edges_from(self.edges)
        
        # Create Adjacency Matrix (A) and Degree Matrix (D) for GNNs
        A = nx.to_numpy_array(self.G)
        self.A_tensor = torch.FloatTensor(A)
        
        # Add self-loops for GCN: A_hat = A + I
        self.A_hat = self.A_tensor + torch.eye(self.num_nodes)
        
        # D_hat^-0.5
        D_hat = torch.diag(torch.sum(self.A_hat, dim=1))
        self.D_hat_inv_sqrt = torch.pow(D_hat, -0.5)
        self.D_hat_inv_sqrt[torch.isinf(self.D_hat_inv_sqrt)] = 0.0
        
        # Normalized Adjacency: D^-0.5 A_hat D^-0.5
        self.A_norm = torch.mm(torch.mm(self.D_hat_inv_sqrt, self.A_hat), self.D_hat_inv_sqrt)

    def generate_fault_dataset(self, num_samples=500):
        """
        Generates simulated telemetry for the microservices.
        Features per node (5): [cpu, memory, latency, error_rate, anomaly_score]
        """
        X_list = []
        Y_list = []
        
        for _ in range(num_samples):
            # 1. Base telemetry (normal state)
            X = np.random.normal(loc=0.1, scale=0.05, size=(self.num_nodes, 5))
            X = np.clip(X, 0, 1)
            
            # 2. Inject Root Cause Fault in a random node
            root_cause_idx = np.random.randint(0, self.num_nodes)
            Y_list.append(root_cause_idx)
            
            fault_type = np.random.choice(['cpu_spike', 'memory_leak', 'network_drop'])
            
            if fault_type == 'cpu_spike':
                X[root_cause_idx, 0] = np.random.uniform(0.8, 1.0) # CPU
                X[root_cause_idx, 2] = np.random.uniform(0.6, 1.0) # Latency
                X[root_cause_idx, 4] = np.random.uniform(0.7, 1.0) # Anomaly
            elif fault_type == 'memory_leak':
                X[root_cause_idx, 1] = np.random.uniform(0.8, 1.0) # Memory
                X[root_cause_idx, 4] = np.random.uniform(0.6, 0.9)
            elif fault_type == 'network_drop':
                X[root_cause_idx, 2] = np.random.uniform(0.9, 1.0) # Latency
                X[root_cause_idx, 3] = np.random.uniform(0.7, 1.0) # Error Rate
                X[root_cause_idx, 4] = np.random.uniform(0.8, 1.0)
                
            # 3. Propagate faults to upstream dependents
            # In microservices, if Payment fails, Orders latency spikes.
            # We use BFS on reversed graph to propagate upstream.
            rev_G = self.G.reverse()
            for upstream_node in nx.descendants(rev_G, self.idx_to_node[root_cause_idx]):
                u_idx = self.node_to_idx[upstream_node]
                # Upstream experiences latency and errors, but NOT cpu/memory spikes
                X[u_idx, 2] = min(1.0, X[u_idx, 2] + np.random.uniform(0.3, 0.7))
                X[u_idx, 3] = min(1.0, X[u_idx, 3] + np.random.uniform(0.1, 0.5))
                X[u_idx, 4] = min(1.0, X[u_idx, 4] + np.random.uniform(0.2, 0.5))
                
            X_list.append(torch.FloatTensor(X))
            
        return torch.stack(X_list), torch.LongTensor(Y_list)

if __name__ == "__main__":
    builder = SockShopGraphBuilder()
    X, y = builder.generate_fault_dataset(10)
    print("X shape:", X.shape)
    print("Y shape:", y.shape)
    print("Adjacency Norm shape:", builder.A_norm.shape)
