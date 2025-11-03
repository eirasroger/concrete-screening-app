import os
import json
from openai import OpenAI
import fitz  # PyMuPDF for reading PDFs

def get_prompt_template(template_name: str) -> str:
    """Reads a prompt template from the prompts directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, '..', 'prompts', f"{template_name}.txt")
    try:
        with open(prompt_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "ERROR: Prompt template not found."

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts all text from a given PDF file."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def extract_epd_data(api_key: str, pdf_path: str) -> dict:
    """
    Extracts structured data from an EPD PDF using an LLM.

    Returns a dictionary with the extracted data or an error message.
    """
    if not api_key:
        return {"error": "API Key is missing. Please provide your API key."}

    client = OpenAI(api_key=api_key)
    
    # 1. Extract text from the PDF
    epd_text = extract_text_from_pdf(pdf_path)
    if epd_text.startswith("Error"):
        return {"error": epd_text}
    


    # 2. Get and format the prompt
    prompt_template = get_prompt_template("epd_extraction")
    if prompt_template.startswith("ERROR"):
        return {"error": prompt_template}
    
    prompt = prompt_template.format(epd_text=epd_text) 

    # 3. Make the API call
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        extracted_json = json.loads(response.choices[0].message.content)
        return extracted_json

    except Exception as e:
        return {"error": f"An error occurred during the API call: {e}"}


def save_extraction_result(result_dict: dict, input_filename: str, output_dir: str):
    """Saves the extracted data as a JSON file."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Create a corresponding .json filename
    json_filename = os.path.splitext(input_filename)[0] + ".json"
    output_path = os.path.join(output_dir, json_filename)

    with open(output_path, 'w') as f:
        json.dump(result_dict, f, indent=4)