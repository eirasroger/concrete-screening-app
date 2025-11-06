import streamlit as st

def regulation_selector(available_regulations):
    """Creates a selectbox in the sidebar for regulation selection."""
    return st.sidebar.selectbox(
        "Select regulatory schema",
        available_regulations,
        help="Select the applicable regulatory framework."
    )

def custom_info_input():
    """Creates a text area in the sidebar for custom information."""
    return st.sidebar.text_area(
        "Additional constraints or scenario description",
        placeholder="Describe project-specific requirements, context, or constraints..."
    )

def epd_uploader():
    """Creates a file uploader in the sidebar for EPDs."""
    return st.sidebar.file_uploader(
        "Upload EPD document(s) (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload one or more Environmental Product Declaration PDFs."
    )

def drawing_uploader():
    """Creates a file uploader in the sidebar for drawings."""
    return st.sidebar.file_uploader(
        "Upload drawing(s) or project spec (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload one or more project drawing PDFs."
    )
