
import os
import shutil
import time
import uuid
import streamlit as st
from typing import List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
INPUT_DIR = os.path.join(BASE_DIR, 'data', 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'output')

# Root directories, one per document type. The files belonging to a given user
# session are never written here directly: each session gets its own
# sub-directory underneath, so that concurrent users of the deployed
# application cannot read or overwrite one another's documents.
EPD_INPUT_ROOT = os.path.join(INPUT_DIR, 'epds')
DRAWING_INPUT_ROOT = os.path.join(INPUT_DIR, 'drawings')
CUSTOM_INFO_INPUT_ROOT = os.path.join(INPUT_DIR, 'custom_information')
EPD_OUTPUT_ROOT = os.path.join(OUTPUT_DIR, 'epds')
DRAWING_OUTPUT_ROOT = os.path.join(OUTPUT_DIR, 'drawings')
CUSTOM_INFO_OUTPUT_ROOT = os.path.join(OUTPUT_DIR, 'custom_information')

ALL_ROOTS = [
    EPD_INPUT_ROOT, DRAWING_INPUT_ROOT, CUSTOM_INFO_INPUT_ROOT,
    EPD_OUTPUT_ROOT, DRAWING_OUTPUT_ROOT, CUSTOM_INFO_OUTPUT_ROOT,
]

# A session directory older than this is considered abandoned and may be removed.
SESSION_MAX_AGE_SECONDS = 24 * 60 * 60

# Fallback identifier used when no Streamlit session is available, for instance
# when the engine is exercised directly from a test or a script.
_FALLBACK_SESSION_ID = uuid.uuid4().hex


def get_session_id() -> str:
    """
    Returns the identifier of the current user session.

    The identifier is generated once per Streamlit session and kept in the
    session state, which Streamlit already isolates per connected user.
    """
    try:
        if 'session_id' not in st.session_state:
            st.session_state.session_id = uuid.uuid4().hex
        return st.session_state.session_id
    except Exception:
        # No Streamlit script context (tests, scripts): use a process-local id.
        return _FALLBACK_SESSION_ID


def session_dir(root: str) -> str:
    """Returns the current session's sub-directory of `root`, creating it."""
    path = os.path.join(root, get_session_id())
    os.makedirs(path, exist_ok=True)
    return path


def epd_input_dir() -> str:
    """Directory holding the EPD PDFs uploaded in this session."""
    return session_dir(EPD_INPUT_ROOT)


def drawing_input_dir() -> str:
    """Directory holding the drawing PDFs uploaded in this session."""
    return session_dir(DRAWING_INPUT_ROOT)


def custom_info_input_dir() -> str:
    """Directory holding the custom scenario text saved in this session."""
    return session_dir(CUSTOM_INFO_INPUT_ROOT)


def epd_output_dir() -> str:
    """Directory holding the EPD extraction results of this session."""
    return session_dir(EPD_OUTPUT_ROOT)


def custom_info_output_dir() -> str:
    """Directory holding the custom scenario results of this session."""
    return session_dir(CUSTOM_INFO_OUTPUT_ROOT)


def save_uploaded_files(uploaded_files: List[st.runtime.uploaded_file_manager.UploadedFile], file_type: str) -> List[str]:
    """Saves uploaded files to the current session's input sub-directory."""
    if file_type == 'epd':
        target_dir = epd_input_dir()
    elif file_type == 'drawing':
        target_dir = drawing_input_dir()
    else:
        return []

    saved_file_paths = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Keep only the base name, so that an unexpected name cannot place
            # the file outside the session directory.
            safe_name = os.path.basename(uploaded_file.name)
            file_path = os.path.join(target_dir, safe_name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            saved_file_paths.append(file_path)

    return saved_file_paths


def save_custom_text(text_content: str, filename: str = "custom_scenario.txt") -> str:
    """Saves custom text information to the current session's directory."""
    file_path = os.path.join(custom_info_input_dir(), os.path.basename(filename))
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text_content)
    return file_path


def clear_io_folders():
    """
    Removes the documents and results belonging to the current session only.

    Other sessions are left untouched, so that clearing the inputs in one
    browser tab cannot discard another user's work.
    """
    for root in ALL_ROOTS:
        folder = os.path.join(root, get_session_id())
        if not os.path.isdir(folder):
            continue
        try:
            shutil.rmtree(folder)
        except Exception as e:
            print(f"Failed to clear {folder}. Reason: {e}")
        os.makedirs(folder, exist_ok=True)


def purge_stale_session_dirs(max_age_seconds: int = SESSION_MAX_AGE_SECONDS):
    """
    Removes session directories left behind by sessions that have ended.

    Streamlit gives no notification when a user disconnects, so abandoned
    directories are cleaned up on age instead. The threshold is far longer
    than any realistic session, so a directory in active use is never removed.
    """
    cutoff = time.time() - max_age_seconds
    for root in ALL_ROOTS:
        if not os.path.isdir(root):
            continue
        for entry in os.listdir(root):
            if entry == ".gitkeep":
                continue
            path = os.path.join(root, entry)
            try:
                if os.path.isdir(path) and os.path.getmtime(path) < cutoff:
                    shutil.rmtree(path)
            except Exception as e:
                print(f"Failed to purge {path}. Reason: {e}")
