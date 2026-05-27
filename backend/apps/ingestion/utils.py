import os
import pandas as pd
from django.core.files.storage import default_storage


def validate_csv_file(file):
    """Validate that uploaded file is CSV"""
    if not file.name.endswith('.csv'):
        raise ValueError('File must be CSV format')
    
    if file.size > 50 * 1024 * 1024:  # 50MB limit
        raise ValueError('File too large (max 50MB)')
    
    return True


def get_file_rows_count(file_path):
    """Count rows in CSV file"""
    try:
        df = pd.read_csv(file_path)
        return len(df)
    except:
        return 0


def save_upload_file(file, folder='uploads'):
    """Save uploaded file to storage"""
    filename = f"{folder}/{file.name}"
    path = default_storage.save(filename, file)
    return default_storage.url(path)


def delete_upload_file(file_path):
    """Delete uploaded file from storage"""
    if default_storage.exists(file_path):
        default_storage.delete(file_path)