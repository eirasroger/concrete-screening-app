import os
import json
import base64
import fitz  
from openai import OpenAI
from openai import AsyncOpenAI
import asyncio

def get_prompt_template(template_name: str) -> str:
    """Reads a prompt template from the src/prompts directory."""
    prompt_path = os.path.join(os.getcwd(), 'src', 'prompts', f"{template_name}.txt")
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"DEBUG: Prompt file could not be found at the expected path: {prompt_path}")
        return "ERROR: Prompt template not found."

def extract_epd_data(api_key: str, pdf_path: str) -> dict:
    """
    Extracts structured data from an EPD PDF using the gpt vision model.
    This method converts each PDF page to an image and sends them for visual analysis.

    Returns a dictionary with the extracted data or an error message.
    """
    if not api_key:
        return {"error": "API Key is missing. Please provide your API key."}

    client = OpenAI(api_key=api_key)

    # 1. Get the prompt text that will instruct the model
    prompt_text = get_prompt_template("epd_extraction")
    if prompt_text.startswith("ERROR"):
        return {"error": prompt_text}

    # 2. Convert PDF pages to a list of base64-encoded images
    base64_images = []
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            pix = page.get_pixmap(dpi=200)  
            img_bytes = pix.tobytes("png")
            base64_images.append(base64.b64encode(img_bytes).decode('utf-8'))
        doc.close()
    except Exception as e:
        return {"error": f"Failed to convert PDF to images: {e}"}

    # 3. Construct the message payload for the vision model
    # The first part of the content is always the text prompt
    messages_content = [{"type": "text", "text": prompt_text}]

    # Add each page image to the content list
    for img in base64_images:
        messages_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img}"}
        })
        
    # 4. Make the API call to gpt
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[{"role": "user", "content": messages_content}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        extracted_json = json.loads(response.choices[0].message.content)
        return extracted_json

    except Exception as e:
        return {"error": f"An error occurred during the API call: {e}"}


async def extract_epd_data_async(api_key: str, pdf_path: str) -> dict:
    """Asynchronous version of extract_epd_data for parallel processing."""
    
    # Use the asynchronous client
    client = AsyncOpenAI(api_key=api_key)

    prompt_text = get_prompt_template("epd_extraction")
    if prompt_text.startswith("ERROR"):
        return {"error": prompt_text}

    base64_images = []
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            base64_images.append(base64.b64encode(img_bytes).decode('utf-8'))
        doc.close()
    except Exception as e:
        return {"error": f"Failed to convert PDF to images: {e}"}

    messages_content = [{"type": "text", "text": prompt_text}]
    for img in base64_images:
        messages_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img}"}
        })
        
    try:
        # Use 'await' for the API call
        response = await client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[{"role": "user", "content": messages_content}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        extracted_json = json.loads(response.choices[0].message.content)
        return extracted_json

    except Exception as e:
        return {"error": f"An error occurred during the async API call: {e}"}




def save_extraction_result(result_dict: dict, input_filename: str, output_dir: str):
    """Saves the extracted data as a JSON file."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    json_filename = os.path.splitext(input_filename)[0] + ".json"
    output_path = os.path.join(output_dir, json_filename)

    with open(output_path, 'w') as f:
        json.dump(result_dict, f, indent=4)
