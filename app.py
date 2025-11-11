import os
import sys
import streamlit as st
import asyncio
import json

# --- App Layout (must be the first Streamlit command) ---
st.set_page_config(page_title="Concrete compliance screening", layout="wide")

# --- Project Root Setup ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- API Key Initialization ---
# Initialize the key in session state if it's not already there.
if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = ""

# --- Main Application Function ---
def main_app():
    """
    This function contains the entire Streamlit application logic
    and is only called after the API key has been provided.
    """
    
    # --- Imports ---
    from src.UI.ui_inputs import regulation_selector, custom_info_input, epd_uploader, drawing_uploader
    from src.engine.regulations import list_regulations
    from src.engine.file_handler import save_uploaded_files, clear_io_folders, EPD_INPUT_DIR, EPD_OUTPUT_DIR
    from src.engine.llm_calls import extract_epd_data, save_extraction_result, extract_epd_data_async
    from src.engine.compliance_checker import load_regulation_file, get_final_requirements, calculate_epd_metrics, perform_compliance_check
    from src.engine.mapping_processor import load_mapping_file, determine_exposure_classes_with_llm, save_custom_analysis_result
    from src.engine.custom_constraints_extractor import extract_custom_constraints
    from src.engine.drawing_processor import analyze_drawing_with_context
    from src.engine.file_handler import DRAWING_INPUT_DIR 

    # --- App Title & Session Initialization ---
    st.title("Interactive decision support engine for concrete compliance screening")
    st.caption("Developed by R. Vergés et al. (2026)")

    if 'initialized' not in st.session_state:
        clear_io_folders()
        st.session_state.initialized = True
        st.session_state.saved_epd_names = []
        st.session_state.saved_drawing_names = []
        st.session_state.analysis_results = {}
        st.session_state.custom_info_result = None
        st.session_state.user_constraints = None

    if 'user_constraints' not in st.session_state:
        st.session_state.user_constraints = None 
    if 'drawing_analysis_results' not in st.session_state:
        st.session_state.drawing_analysis_results = {}

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
    col1, col2 = st.columns(2)

    with col1:
        st.header("Custom user scenario analysis")
        if st.button("Determine user-induced requirements", disabled=(not custom_info)):
            if not st.session_state.openai_api_key:
                st.error("OpenAI API key not found.")
            else:
                with st.spinner("Analysing custom scenario... (2 steps)"):
                    api_key = st.session_state.openai_api_key
                    
                    st.write("Step 1: Determining exposure classes...")
                    mapping = load_mapping_file(regulation, "exposure_class")
                    exp_class_result = determine_exposure_classes_with_llm(custom_info, mapping, regulation, api_key)
                    
                    st.session_state.custom_info_result = {
                        "input_description": custom_info,
                        **exp_class_result
                    }
                    
                    st.write("Step 2: Extracting user-defined technical constraints...")
                    user_constraints_result = extract_custom_constraints(custom_info, api_key)
                    st.session_state.user_constraints = user_constraints_result

                    if 'error' not in exp_class_result and 'error' not in user_constraints_result:
                        st.success("Custom scenario analysis complete!")
                    else:
                        if 'error' in exp_class_result:
                            st.error(f"Exposure class error: {exp_class_result['error']}")
                        if 'error' in user_constraints_result:
                            st.error(f"Custom constraint error: {user_constraints_result['error']}")

 

    if st.session_state.custom_info_result:
        st.markdown("##### Custom user requirement results")
        with st.expander("Custom scenario analysis: Exposure classes", expanded=True): 
            if 'error' in st.session_state.custom_info_result:
                st.error(st.session_state.custom_info_result['error'])
            else:
                st.write("Based on the provided description, the LLM determined the following classes:")
                classes = st.session_state.custom_info_result.get("assigned_exposure_classes", [])
                if classes:
                    st.info(f"**Assigned classes:** `{', '.join(classes)}`")
                else:
                    st.warning("No specific exposure classes could be determined from the description.")
                st.json(st.session_state.custom_info_result)

    if st.session_state.user_constraints:
        with st.expander("User-defined technical constraints", expanded=True):
            if 'error' in st.session_state.user_constraints:
                st.error(st.session_state.user_constraints['error'])
            else:
                st.write("The following technical constraints were extracted from your custom information:")
                st.json(st.session_state.user_constraints)

    # --- Drawing Analysis Section ---
    st.divider()
    st.header("Drawing/Project documentation requirement analysis")
    can_analyze_drawings = st.session_state.saved_drawing_names and st.session_state.custom_info_result

    if st.button("Analyse drawings with user-defined context", disabled=(not can_analyze_drawings)):
        if not st.session_state.openai_api_key:
            st.error("OpenAI API key not found.")
        else:
            with st.spinner("Analysing drawings... This can take a while."):
                api_key = st.session_state.openai_api_key
                custom_info_data = st.session_state.custom_info_result
                all_drawing_results = {}
                for drawing_name in st.session_state.saved_drawing_names:
                    st.write(f"Processing: {drawing_name}...")
                    result = analyze_drawing_with_context(
                        api_key=api_key,
                        drawing_path=os.path.join(DRAWING_INPUT_DIR, drawing_name),
                        custom_info=custom_info_data['input_description'],
                        preliminary_classes=custom_info_data['assigned_exposure_classes']
                    )
                    all_drawing_results[drawing_name] = result
                st.session_state.drawing_analysis_results = all_drawing_results
                st.success("Drawing analysis complete!")

    if st.session_state.drawing_analysis_results:
        st.markdown("#### Drawing analysis results")
        for filename, result in st.session_state.drawing_analysis_results.items():
            with st.expander(f"Results for: **{filename}**"):
                st.json(result)


    # --- EPD Data Extraction Section ---
    def run_async_analysis(api_key, filenames, input_dir):
        async def main():
            tasks = [extract_epd_data_async(api_key, os.path.join(input_dir, filename)) for filename in filenames]
            return await asyncio.gather(*tasks)
        return asyncio.run(main())

    st.divider()
    st.header("EPD data extraction")
    if st.button("Run EPD data extraction", disabled=(not st.session_state.saved_epd_names)):
        if not st.session_state.openai_api_key:
            st.error("OpenAI API key not found.")
        else:
            with st.spinner("Analysing all EPDs... This may take a moment."):
                api_key = st.session_state.openai_api_key
                results = run_async_analysis(api_key, st.session_state.saved_epd_names, EPD_INPUT_DIR)
                st.session_state.analysis_results = dict(zip(st.session_state.saved_epd_names, results))
                
                for filename, result in st.session_state.analysis_results.items():
                    if 'error' not in result:
                        save_extraction_result(result, filename, EPD_OUTPUT_DIR)
                st.success("Data extraction complete!")

    # --- Results Display Sections ---
    if st.session_state.analysis_results:
        st.markdown("#### EPD data extraction results")
        for filename, result in st.session_state.analysis_results.items():
            with st.expander(f"Results for: **{filename}**"):
                if 'error' in result:
                    st.error(f"Could not process file: {result['error']}")
                else:
                    st.json(result)

    # --- Final Compliance Section ---
    st.divider()
    st.header("Final compliance assessment")
    can_run_compliance = (st.session_state.custom_info_result and st.session_state.analysis_results and "error" not in st.session_state.custom_info_result)

    if st.button("Run full compliance check", disabled=(not can_run_compliance)):
        exposure_classes = st.session_state.custom_info_result.get("assigned_exposure_classes", [])
        user_constraints = st.session_state.user_constraints
        drawing_reqs = next(iter(st.session_state.drawing_analysis_results.values()), None)
        regulation_data = load_regulation_file(regulation)
        
        if "error" in regulation_data:
            st.error(regulation_data["error"])
        else:
            with st.spinner("Performing final compliance checks against all EPDs..."):
                final_reqs = get_final_requirements(exposure_classes, regulation_data, user_constraints, drawing_reqs)
                st.write("#### Aggregated scenario requirements")
                st.json(final_reqs)
                st.write("#### Compliance check per EPD")
                for filename in st.session_state.saved_epd_names:
                    with st.expander(f"**Assessment for: {filename}**", expanded=True):
                        try:
                            json_path = os.path.join(EPD_OUTPUT_DIR, os.path.splitext(filename)[0] + ".json")
                            with open(json_path, 'r') as f:
                                epd_data = json.load(f)
                            
                            epd_metrics = calculate_epd_metrics(epd_data)
                            st.write("##### Calculated EPD metrics")
                            st.json(epd_metrics)
                            
                            compliance_result = perform_compliance_check(epd_metrics, final_reqs)
                            st.write("##### Verdict")
                            if compliance_result["pass"]:
                                st.success("✅ PASS: This concrete product meets the scenario requirements.")
                            else:
                                st.error("❌ FAIL: This concrete product does not meet one or more scenario requirements.")
                            for detail in compliance_result["details"]:
                                st.info(detail)
                        except FileNotFoundError:
                            st.warning(f"Could not find analysis results for {filename}.")
                        except Exception as e:
                            st.error(f"An error occurred for {filename}: {e}")

# --- API KEY GATE ---

# Try to load the key from secrets.toml first.
secrets_paths = [
    os.path.join(os.path.expanduser("~"), ".streamlit", "secrets.toml"),
    os.path.join(project_root, ".streamlit", "secrets.toml")
]
secrets_exist = any(os.path.exists(path) for path in secrets_paths)
if secrets_exist and not st.session_state.openai_api_key:
    try:
        st.session_state.openai_api_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        pass

# If the key is available, run the main app. Otherwise, show the login screen.
if st.session_state.openai_api_key:
    main_app()
else:
    st.title("Welcome")
    st.header("Please provide your OpenAI API Key to continue")
    
    api_key_input = st.text_input(
        "OpenAI API Key",
        placeholder="sk-...",
        help="Your key is not stored. It is only used for this session.",
        key="api_key_input_widget"
    )

    if st.button("Submit Key"):
        st.session_state.openai_api_key = api_key_input
        st.rerun()

