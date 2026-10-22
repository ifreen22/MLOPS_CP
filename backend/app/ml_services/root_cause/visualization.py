import os
import torch
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix
import numpy as np

def generate_visualizations(builder, sage_model, X_test, y_test):
    vis_dir = os.path.join(os.path.dirname(__file__), "visualizations")
    os.makedirs(vis_dir, exist_ok=True)
    
    # 1. Service Dependency Graph
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(builder.G, seed=42)
    nx.draw(builder.G, pos, with_labels=True, node_color='lightblue', 
            node_size=3000, font_size=10, font_weight='bold', arrows=True)
    plt.title("Sock Shop Microservice Dependency Graph")
    plt.savefig(os.path.join(vis_dir, "dependency_graph.png"))
    plt.close()
    
    # 2. Highlighted Root Cause Example
    sample_idx = 0
    X_sample = X_test[sample_idx].unsqueeze(0)
    y_true = y_test[sample_idx].item()
    
    sage_model.eval()
    with torch.no_grad():
        out = sage_model(X_sample, builder.A_tensor)
        y_pred = torch.argmax(out, dim=1).item()
        
    color_map = []
    for i in range(builder.num_nodes):
        if i == y_pred and i == y_true:
            color_map.append('green') # Correct RCA
        elif i == y_pred:
            color_map.append('red') # False RCA
        else:
            color_map.append('lightgray')
            
    plt.figure(figsize=(10, 8))
    nx.draw(builder.G, pos, with_labels=True, node_color=color_map, 
            node_size=3000, font_size=10, font_weight='bold', arrows=True)
    plt.title(f"Root Cause Isolation (Green = Correctly Isolated: {builder.idx_to_node[y_pred]})")
    plt.savefig(os.path.join(vis_dir, "highlighted_root_cause.png"))
    plt.close()
    
    # 3. Confusion Matrix
    y_true_all = y_test.numpy()
    with torch.no_grad():
        out_all = sage_model(X_test, builder.A_tensor)
        y_pred_all = torch.argmax(out_all, dim=1).numpy()
        
    cm = confusion_matrix(y_true_all, y_pred_all)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=builder.services, yticklabels=builder.services)
    plt.xlabel('Predicted Root Cause')
    plt.ylabel('Actual Root Cause')
    plt.title('Root Cause Confusion Matrix (GraphSAGE)')
    plt.savefig(os.path.join(vis_dir, "confusion_matrix.png"))
    plt.close()
    
    # 4. Feature Importance (via Weights of First Layer)
    weights = sage_model.sage1.weight.detach().numpy()
    # Weights for self_feat are first num_node_features
    # We take absolute mean across hidden dims
    feat_imp = np.mean(np.abs(weights[:, :5]), axis=0)
    features = ['CPU', 'Memory', 'Latency', 'Errors', 'Anomaly Score']
    
    plt.figure(figsize=(8, 5))
    sns.barplot(x=features, y=feat_imp, palette='viridis')
    plt.title("Feature Importance (GraphSAGE Input Layer)")
    plt.ylabel("Absolute Weight Magnitude")
    plt.savefig(os.path.join(vis_dir, "feature_importance.png"))
    plt.close()
    
    print("Visualizations saved successfully!")

if __name__ == "__main__":
    from app.ml_services.root_cause.graph_builder import SockShopGraphBuilder
    from app.ml_services.root_cause.models import GraphSAGE
    
    builder = SockShopGraphBuilder(seed=42)
    X, y = builder.generate_fault_dataset(500)
    split = int(len(X) * 0.8)
    X_train, y_train = X[:split], y[:split]
    X_test, y_test = X[split:], y[split:]
    
    sage = GraphSAGE(5, 16, builder.num_nodes)
    
    # Quick train
    optimizer = torch.optim.Adam(sage.parameters(), lr=0.01)
    for _ in range(50):
        optimizer.zero_grad()
        out = sage(X_train, builder.A_tensor)
        loss = torch.nn.CrossEntropyLoss()(out, y_train)
        loss.backward()
        optimizer.step()
        
    generate_visualizations(builder, sage, X_test, y_test)
