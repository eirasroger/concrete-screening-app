import os
import sys
import streamlit as st
import asyncio
import json

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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




# --- Session Initialization ---
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



# ... inside the `with col1:` block for the "Determine Exposure Classes" button

with col1:
    if st.button("Determine user-induced requirements", disabled=(not custom_info)):
        if "OPENAI_API_KEY" not in st.secrets or not st.secrets["OPENAI_API_KEY"]:
            st.error("OpenAI API key not found.")
        else:
            with st.spinner("Analyzing custom scenario... (2 steps)"):
                api_key = st.secrets["OPENAI_API_KEY"]
                
                # --- Step 1: Determine Exposure Class ---
                st.write("Step 1: Determining exposure classes...")
                mapping = load_mapping_file(regulation, "exposure_class")
                exp_class_result = determine_exposure_classes_with_llm(custom_info, mapping, regulation, api_key)
                
                st.session_state.custom_info_result = {
                    "input_description": custom_info,
                    **exp_class_result
                }
                
                # --- Step 2: Extract Custom User Constraints ---
                st.write("Step 2: Extracting user-defined technical constraints...")
                user_constraints_result = extract_custom_constraints(custom_info, api_key)
                st.session_state.user_constraints = user_constraints_result

                # Save results if no errors occurred in either call
                if 'error' not in exp_class_result and 'error' not in user_constraints_result:
                    st.success("Custom scenario analysis complete!")
                else:
                    if 'error' in exp_class_result:
                        st.error(f"Exposure class error: {exp_class_result['error']}")
                    if 'error' in user_constraints_result:
                        st.error(f"Custom constraint error: {user_constraints_result['error']}")


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

if st.button("Run EPD data extraction", disabled=(not st.session_state.saved_epd_names)):
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
            
            st.success("Data extraction complete!")

# --- Results Display ---
if st.session_state.analysis_results:
    st.subheader("Extraction results")
    for filename, result in st.session_state.analysis_results.items():
        with st.expander(f"Results for: **{filename}**"):
            if 'error' in result:
                st.error(f"Could not process file: {result['error']}")
            else:
                st.json(result)


st.subheader("User-induced requirement results")



if st.session_state.custom_info_result:
    with st.expander("Custom scenario analysis: Exposure classes", expanded=True): 
        if 'error' in st.session_state.custom_info_result:
            st.error(st.session_state.custom_info_result['error'])
        else:
            st.write("Based on the provided description, the LLM determined the following classes:")
            
            # Display the result list, or a message if it's empty
            classes = st.session_state.custom_info_result.get("assigned_exposure_classes", [])
            if classes:
                st.info(f"**Assigned classes:** `{', '.join(classes)}`")
            else:
                st.warning("No specific exposure classes could be determined from the description.")
            
            # Show the full JSON for transparency
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
st.header("Drawing requirement analysis based on user-provided context")

can_analyze_drawings = st.session_state.saved_drawing_names and st.session_state.custom_info_result

if st.button("Analyze drawings with context", disabled=(not can_analyze_drawings)):
    if "OPENAI_API_KEY" not in st.secrets or not st.secrets["OPENAI_API_KEY"]:
        st.error("OpenAI API key not found.")
    else:
        with st.spinner("Analyzing drawings... This can take a while."):
            api_key = st.secrets["OPENAI_API_KEY"]
            custom_info = st.session_state.custom_info_result['input_description']
            prelim_classes = st.session_state.custom_info_result['assigned_exposure_classes']
            
            # This will store results for each drawing
            all_drawing_results = {}

            for drawing_name in st.session_state.saved_drawing_names:
                st.write(f"Processing: {drawing_name}...")
                drawing_path = os.path.join(DRAWING_INPUT_DIR, drawing_name)
                
                result = analyze_drawing_with_context(
                    api_key=api_key,
                    drawing_path=drawing_path,
                    custom_info=custom_info,
                    preliminary_classes=prelim_classes
                )
                all_drawing_results[drawing_name] = result

            st.session_state.drawing_analysis_results = all_drawing_results
            st.success("Drawing analysis complete!")

# Display drawing analysis results
if st.session_state.drawing_analysis_results:
    st.subheader("Drawing analysis results")
    for filename, result in st.session_state.drawing_analysis_results.items():
        with st.expander(f"Results for: **{filename}**"):
            if 'error' in result:
                st.error(f"Could not process file: {result['error']}")
            else:
                st.json(result)











st.divider()
st.header("Final compliance assessment")


can_run_compliance = (
    st.session_state.custom_info_result and 
    st.session_state.analysis_results and
    "error" not in st.session_state.custom_info_result
)

if st.button("Run full compliance check", disabled=(not can_run_compliance)):
    # Get all necessary data from session state
    exposure_classes = st.session_state.custom_info_result.get("assigned_exposure_classes", [])
    user_constraints = st.session_state.user_constraints
    drawing_reqs = next(iter(st.session_state.drawing_analysis_results.values()), None)

    # Load the main regulation file
    regulation_data = load_regulation_file(regulation)
    
    if "error" in regulation_data:
        st.error(regulation_data["error"])
    else:
        with st.spinner("Performing final compliance checks against all EPDs..."):
            # Determine the final, most stringent requirements from all sources
            final_reqs = get_final_requirements(
                exposure_classes, 
                regulation_data, 
                user_constraints,
                drawing_reqs
            )
            
            st.write("#### Aggregated scenario requirements")
            st.json(final_reqs)

            st.write("#### Compliance check per EPD")
            # Loop through the original filenames of the uploaded EPDs
            for filename in st.session_state.saved_epd_names:
                with st.expander(f"**Assessment for: {filename}**", expanded=True):
                    try:
                        # Construct the path to the output JSON file for the current EPD
                        json_filename = os.path.splitext(filename)[0] + ".json"
                        json_filepath = os.path.join(EPD_OUTPUT_DIR, json_filename)
                        
                        # Load the full EPD data from its JSON file
                        with open(json_filepath, 'r') as f:
                            epd_data = json.load(f)
                        
                        # Calculate metrics FROM THE LOADED EPD DATA
                        epd_metrics = calculate_epd_metrics(epd_data)
                        st.write("##### Calculated EPD metrics")
                        st.json(epd_metrics)

                        # Perform the final pass/fail check with the correct metrics
                        compliance_result = perform_compliance_check(epd_metrics, final_reqs)
                        st.write("##### Verdict")
                        if compliance_result["pass"]:
                            st.success("✅ PASS: This concrete product meets the scenario requirements.")
                        else:
                            st.error("❌ FAIL: This concrete product does not meet one or more scenario requirements.")
                        
                        # Display all the details from the check
                        for detail in compliance_result["details"]:
                            st.info(detail)

                    except FileNotFoundError:
                        st.warning(f"Could not find the analysis result file for {filename}. Please ensure EPD analysis was run successfully.")
                    except Exception as e:
                        st.error(f"An error occurred while checking compliance for {filename}: {e}")
