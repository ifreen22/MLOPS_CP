import os
import urllib.request
import pandas as pd
from app.ml_services.alert_clustering.config import DATASET_URL, DATA_DIR

def download_and_load_dataset():
    file_path = os.path.join(DATA_DIR, "HDFS_2k.log")
    if not os.path.exists(file_path):
        print("Downloading LogHub HDFS dataset...")
        urllib.request.urlretrieve(DATASET_URL, file_path)
    
    with open(file_path, "r") as f:
        lines = [line.strip() for line in f.readlines()]
        
    df = pd.DataFrame({"raw_log": lines})
    return df
