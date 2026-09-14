import os
import json
import base64
import fitz  
from typing import List

from .llm_calls import MODEL, TEMPERATURE, build_client
from .schemas import DrawingAnalysis

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
    
    prompt_file_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'drawing_processor.txt')
    with open(prompt_file_path, 'r', encoding='utf-8') as f:
        return f.read()

def analyze_drawing_with_context(api_key: str, drawing_path: str, custom_info: str, preliminary_classes: List[str]) -> dict:
    """
    Analyzes a drawing PDF using an LLM, focusing on the user's intended application.
    """
    client = build_client(api_key)
    
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
        response = client.chat.completions.parse(
            model=MODEL,
            messages=[{"role": "user", "content": messages_content}],
            temperature=TEMPERATURE,
            response_format=DrawingAnalysis
        )

        message = response.choices[0].message
        if message.refusal:
            return {"error": f"The model declined to answer: {message.refusal}"}
        if message.parsed is None:
            return {"error": "The model returned no parsable content."}

        return message.parsed.model_dump()

    except Exception as e:
        return {"error": f"An error occurred during the drawing analysis API call: {e}"}


