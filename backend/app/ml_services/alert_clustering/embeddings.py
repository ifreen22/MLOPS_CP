from sentence_transformers import SentenceTransformer
import time

class EmbeddingGenerator:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        
    def generate(self, texts: list):
        return self.model.encode(texts, show_progress_bar=False)

def benchmark_embeddings(texts: list):
    models = [
        'all-MiniLM-L6-v2',
        'BAAI/bge-base-en-v1.5'
    ]
    
    results = {}
    for name in models:
        start_time = time.time()
        generator = EmbeddingGenerator(name)
        embeddings = generator.generate(texts)
        duration = time.time() - start_time
        
        results[name] = {
            'embeddings': embeddings,
            'time_seconds': duration,
            'dimensions': embeddings.shape[1]
        }
        print(f"[{name}] Encoded {len(texts)} logs in {duration:.2f}s (Dims: {embeddings.shape[1]})")
        
    return results
