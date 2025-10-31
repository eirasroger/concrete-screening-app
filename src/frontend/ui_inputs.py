import streamlit as st

def regulation_selector(available_regulations):
    return st.selectbox(
        "Select regulatory schema",
        available_regulations,
        help="Select the applicable regulatory framework."
    )

def custom_info_input():
    return st.text_area(
        "Additional constraints or scenario description",
        placeholder="Describe project-specific requirements, context, or constraints..."
    )

def epd_uploader():
    return st.file_uploader(
        "Upload EPD document(s) (PDF)", type=["pdf"], accept_multiple_files=True,
        help="Upload one or more Environmental Product Declaration PDFs."
    )

def drawing_uploader():
    return st.file_uploader(
        "Upload drawing(s) or project spec (PDF)", type=["pdf"], accept_multiple_files=True,
        help="Upload one or more project drawing PDFs."
    )
