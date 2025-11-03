import os
import sys
import streamlit as st
import asyncio

# This block is the key. It adds the project's root directory to the Python path.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now Python can find the 'src' package.
from src.frontend.ui_inputs import regulation_selector, custom_info_input, epd_uploader, drawing_uploader
from src.backend.regulations import list_regulations
from src.backend.file_handler import save_uploaded_files, clear_io_folders, EPD_INPUT_DIR, EPD_OUTPUT_DIR
from src.backend.llm_calls import extract_epd_data, save_extraction_result, extract_epd_data_async

# --- Session Initialization ---
if 'initialized' not in st.session_state:
    clear_io_folders()
    st.session_state.initialized = True
    st.session_state.saved_epd_names = []
    st.session_state.saved_drawing_names = []
    st.session_state.analysis_results = {}

# --- App Layout ---
st.set_page_config(page_title="Concrete compliance screening", layout="wide")
st.title("Interactive decision support engine for concrete compliance screening")
st.caption("Developed by R. Vergés et al. (2026)")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("Input scenario")
    available_regulations = list_regulations()
    regulation = regulation_selector(available_regulations)
    custom_info = custom_info_input()
    epd_files = epd_uploader()
    drawing_files = drawing_uploader()

    st.divider()
    if st.button("Clear All Uploaded Files"):
        clear_io_folders()
        st.session_state.saved_epd_names = []
        st.session_state.saved_drawing_names = []
        st.session_state.analysis_results = {}
        st.success("Cleared all uploaded files and analysis results.")
        st.rerun()

# --- File Processing Logic ---
# This single block now handles saving files and updating the session state.
if epd_files:
    save_uploaded_files(epd_files, file_type='epd')
    st.session_state.saved_epd_names = [f.name for f in epd_files]
if drawing_files:
    save_uploaded_files(drawing_files, file_type='drawing')
    st.session_state.saved_drawing_names = [f.name for f in drawing_files]

# --- Main Panel ---
st.header("Input summary")
st.write(f"**Selected regulation:** {regulation}")
st.write(f"**Custom information:** {custom_info if custom_info else 'None'}")
st.write(f"**EPD PDFs uploaded:** {st.session_state.saved_epd_names or 'None'}")
st.write(f"**Drawing PDFs uploaded:** {st.session_state.saved_drawing_names or 'None'}")
st.divider()

# --- Analysis Section ---

# We need a small helper function to run our async code from Streamlit's sync environment
def run_async_analysis(api_key, filenames, input_dir):
    async def main():
        tasks = []
        for filename in filenames:
            pdf_path = os.path.join(input_dir, filename)
            # Create a task for each PDF file
            tasks.append(extract_epd_data_async(api_key, pdf_path))
        
        # Run all tasks concurrently and wait for them to complete
        return await asyncio.gather(*tasks)

    return asyncio.run(main())

if st.button("Run EPD Analysis", disabled=(not st.session_state.saved_epd_names)):
    if "OPENAI_API_KEY" not in st.secrets or not st.secrets["OPENAI_API_KEY"]:
        st.error("OpenAI API key not found. Please add it to your .streamlit/secrets.toml file.")
    else:
        with st.spinner("Analyzing all EPDs... This may take a moment."):
            api_key = st.secrets["OPENAI_API_KEY"]
            
            # Run the asynchronous analysis
            results = run_async_analysis(api_key, st.session_state.saved_epd_names, EPD_INPUT_DIR)
            
            # Process the results
            st.session_state.analysis_results = dict(zip(st.session_state.saved_epd_names, results))
            
            for filename, result in st.session_state.analysis_results.items():
                if 'error' not in result:
                    save_extraction_result(result, filename, EPD_OUTPUT_DIR)
            
            st.success("Analysis complete!")

# --- Results Display ---
if st.session_state.analysis_results:
    st.subheader("Extraction Results")
    for filename, result in st.session_state.analysis_results.items():
        with st.expander(f"Results for: **{filename}**"):
            if 'error' in result:
                st.error(f"Could not process file: {result['error']}")
            else:
                st.json(result)

