import re
import pandas as pd

def clean_log(log: str) -> str:
    # Lowercase
    log = log.lower()
    
    # Remove timestamps (e.g., 081109 203615 or 2023-01-01 10:00:00)
    log = re.sub(r'\d{6} \d{6}', '', log)
    log = re.sub(r'\d{4}-\d{2}-\d{2}[t\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:z|[+-]\d{2}:\d{2})?', '', log)
    
    # Remove IP addresses
    log = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '<IP>', log)
    
    # Remove UUIDs / Hex strings
    log = re.sub(r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b', '<UUID>', log)
    log = re.sub(r'\b0x[a-f0-9]+\b', '<HEX>', log)
    
    # Remove block IDs (HDFS specific: blk_...)
    log = re.sub(r'blk_-?\d+', '<BLOCK>', log)
    
    # Remove pure numbers (e.g., sizes, ports)
    log = re.sub(r'\b\d+\b', '<NUM>', log)
    
    # Remove extra spaces
    log = re.sub(r'\s+', ' ', log).strip()
    
    return log

def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df['cleaned_log'] = df['raw_log'].apply(clean_log)
    # Remove exact duplicates to prevent overwhelming clustering with the exact same repetitive log
    df = df.drop_duplicates(subset=['cleaned_log']).reset_index(drop=True)
    return df
