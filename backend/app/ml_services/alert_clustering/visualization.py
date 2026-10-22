try:
    import umap
except ImportError:
    umap = None
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import seaborn as sns
import os
from app.ml_services.alert_clustering.config import VIS_DIR

def plot_umap(embeddings, labels, model_name):
    if umap is None:
        return
    reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, n_components=2, random_state=42)
    embedding_2d = reducer.fit_transform(embeddings)
    
    plt.figure(figsize=(10, 8))
    sns.scatterplot(x=embedding_2d[:, 0], y=embedding_2d[:, 1], hue=labels, palette="Spectral", s=15, legend='full')
    plt.title(f'UMAP Projection - {model_name}')
    plt.savefig(os.path.join(VIS_DIR, f'umap_{model_name.lower()}.png'))
    plt.close()

def plot_tsne(embeddings, labels, model_name):
    tsne = TSNE(n_components=2, random_state=42)
    embedding_2d = tsne.fit_transform(embeddings)
    
    plt.figure(figsize=(10, 8))
    sns.scatterplot(x=embedding_2d[:, 0], y=embedding_2d[:, 1], hue=labels, palette="Spectral", s=15, legend='full')
    plt.title(f't-SNE Projection - {model_name}')
    plt.savefig(os.path.join(VIS_DIR, f'tsne_{model_name.lower()}.png'))
    plt.close()
    
def generate_all_visualizations(embeddings, labels_dict):
    for name, labels in labels_dict.items():
        plot_umap(embeddings, labels, name)
        # To save time, we will only plot t-SNE for the best models, but we can do it for all if required.
        # plot_tsne(embeddings, labels, name)
