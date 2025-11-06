
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
CUSTOM_INFO_OUTPUT_DIR = os.path.join(OUTPUT_DIR, 'custom_information')

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
    """
    Clears the contents of the input and output subdirectories without deleting
    the directories themselves or their .gitkeep files.
    """
    # List of all directories that need to be cleared
    dirs_to_clear = [
        EPD_INPUT_DIR, DRAWING_INPUT_DIR, CUSTOM_INFO_INPUT_DIR,
        EPD_OUTPUT_DIR, os.path.join(OUTPUT_DIR, 'drawings'), CUSTOM_INFO_OUTPUT_DIR
    ]

    for folder in dirs_to_clear:
        # Ensure the directory exists before trying to clear it
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            # If we just created it, no need to clear anything
            continue

        # Iterate through all items in the folder
        for filename in os.listdir(folder):
            # Skip the .gitkeep file
            if filename == ".gitkeep":
                continue

            file_path = os.path.join(folder, filename)
            try:
                # Check if it's a directory and remove it recursively
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                # Check if it's a file and remove it
                elif os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")