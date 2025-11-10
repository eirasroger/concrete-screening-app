import os
import json
import base64
import fitz  
from openai import OpenAI
from typing import List

def pdf_to_base64_images(pdf_path: str) -> List[str]:
    """Converts each page of a PDF into a base64 encoded image."""
    base64_images = []
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            pix = page.get_pixmap(dpi=600)
            img_bytes = pix.tobytes("png")
            base64_images.append(base64.b64encode(img_bytes).decode('utf-8'))
        doc.close()
        return base64_images
    except Exception as e:
        return {"error": f"Failed to convert PDF to images: {e}"}

def get_drawing_analysis_prompt() -> str:
    """
    Returns a targeted prompt for analyzing technical drawings by reading from a file.
    """
    # Construct the path to the prompt file relative to the current script
    prompt_file_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'drawing_processor.txt')
    with open(prompt_file_path, 'r') as f:
        return f.read()

def analyze_drawing_with_context(api_key: str, drawing_path: str, custom_info: str, preliminary_classes: List[str]) -> dict:
    """
    Analyzes a drawing PDF using an LLM, focusing on the user's intended application.
    """
    # This function's internal logic (API call, image conversion) remains the same.
    # The only change is the prompt it uses.
    client = OpenAI(api_key=api_key)
    
    prompt_text = get_drawing_analysis_prompt().format(
        custom_info=custom_info or "Not specified. Analyze for general requirements.",
        preliminary_exposure_classes=json.dumps(preliminary_classes)
    )

    images = pdf_to_base64_images(drawing_path)
    if isinstance(images, dict) and "error" in images:
        return images

    messages_content = [{"type": "text", "text": prompt_text}]
    for img in images:
        messages_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img}"}
        })

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[{"role": "user", "content": messages_content}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        analysis_result = json.loads(response.choices[0].message.content)
        return analysis_result

    except Exception as e:
        return {"error": f"An error occurred during the drawing analysis API call: {e}"}


