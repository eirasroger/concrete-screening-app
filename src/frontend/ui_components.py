import streamlit as st
from typing import List


def sidebar_inputs(regulations_list: List[str], exposure_classes: List[str]):
    st.sidebar.header("Scenario")
    jurisdiction = st.sidebar.selectbox("Regulatory schema", regulations_list)
    exposures = st.sidebar.multiselect("Exposure classes", exposure_classes, default=["XC4"])
    custom_info = st.sidebar.text_area("Custom information (optional)")
    uploaded_files = st.sidebar.file_uploader("Upload product files (PDF or CSV)", accept_multiple_files=True)
    csv_upload = st.sidebar.file_uploader("Or upload products CSV", type=["csv"], help="CSV with columns: name,wc,cement_kg_m3,strength_class")
    return jurisdiction, exposures, custom_info, uploaded_files, csv_upload
