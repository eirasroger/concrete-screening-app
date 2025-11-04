
import os
import shutil
import streamlit as st
from typing import List

# Define base paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
INPUT_DIR = os.path.join(BASE_DIR, 'data', 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'output')

# Define specific subfolder paths
EPD_INPUT_DIR = os.path.join(INPUT_DIR, 'epds')
DRAWING_INPUT_DIR = os.path.join(INPUT_DIR, 'drawings')
EPD_OUTPUT_DIR = os.path.join(OUTPUT_DIR, 'epds')
CUSTOM_INFO_INPUT_DIR = os.path.join(INPUT_DIR, 'custom_information') 

def save_uploaded_files(uploaded_files: List[st.runtime.uploaded_file_manager.UploadedFile], file_type: str) -> List[str]:
    """Saves uploaded files to the correct sub-directory (epds or drawings)."""
    if file_type == 'epd':
        target_dir = EPD_INPUT_DIR
    elif file_type == 'drawing':
        target_dir = DRAWING_INPUT_DIR
    else:
        return []

    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    saved_file_paths = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_path = os.path.join(target_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            saved_file_paths.append(file_path)
    
    return saved_file_paths

def save_custom_text(text_content: str, filename: str = "custom_scenario.txt") -> str:
    """Saves custom text information to its designated folder."""
    if not os.path.exists(CUSTOM_INFO_INPUT_DIR):
        os.makedirs(CUSTOM_INFO_INPUT_DIR, exist_ok=True)
    
    file_path = os.path.join(CUSTOM_INFO_INPUT_DIR, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text_content)
    return file_path

def clear_io_folders():
    """Deletes and recreates the input and output folders to ensure a clean state."""
    for folder in [INPUT_DIR, OUTPUT_DIR]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder, exist_ok=True)
        # Recreate all necessary subdirectories
        os.makedirs(os.path.join(folder, 'epds'), exist_ok=True)
        os.makedirs(os.path.join(folder, 'drawings'), exist_ok=True)
        os.makedirs(os.path.join(folder, 'custom_information'), exist_ok=True)