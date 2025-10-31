import os
import sys
import streamlit as st

# This block is the key. It adds the project's root directory to the Python path.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now Python can find the 'src' package.
from src.frontend.ui_inputs import regulation_selector, custom_info_input, epd_uploader, drawing_uploader
from src.backend.regulations import list_regulations


st.set_page_config(page_title="Concrete compliance screening", layout="wide")
st.title("Interactive decision support engine for concrete compliance screening")
st.caption("Developed by R. Vergés et al. (2026)")



available_regulations = list_regulations() # Will return e.g. ["en206", "as3600"]



st.header("Input scenario")


regulation = regulation_selector(available_regulations)
custom_info = custom_info_input()
epd_files = epd_uploader()
drawing_files = drawing_uploader()


st.divider()
st.header("Input summary")
st.write(f"**Selected regulation:** {regulation}")
st.write(f"**Custom information:** {custom_info if custom_info else 'None'}")


if epd_files:
    st.write(f"**EPD PDFs uploaded:** {[f.name for f in epd_files]}")
else:
    st.write("**EPD PDFs uploaded:** None")


if drawing_files:
    st.write(f"**Drawing PDFs uploaded:** {[f.name for f in drawing_files]}")
else:
    st.write("**Drawing PDFs uploaded:** None")
