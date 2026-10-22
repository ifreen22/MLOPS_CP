import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "saved_models")
VIS_DIR = os.path.join(BASE_DIR, "visualizations")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(VIS_DIR, exist_ok=True)

DATASET_URL = "https://raw.githubusercontent.com/logpai/loghub/master/HDFS/HDFS_2k.log"
