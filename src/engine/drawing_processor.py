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

def get_drawing_analysis_prompt():
    """
    Returns a targeted prompt for analyzing technical drawings.
    """
    return """You are a world-class civil engineering AI assistant. Your primary task is to analyze the provided technical drawing to find specific requirements for a concrete element.

**CRITICAL INSTRUCTION: PAY CLOSE ATTENTION TO TITLE BLOCKS**
Your first and most important task is to meticulously read all text inside the main title block (or "cajetín" or similar, pay attention to language variations) on each drawing sheet, especially the first one. This area often contains a "General Notes" (NOTES GENERALS) or "Specifications" section with the most critical information.

**Context from User:**
- **Intended Application:** The user's description of what the concrete is for (e.g., "for the columns").
- **Preliminary Exposure Classes:** A baseline list of exposure classes from the user's text.

**Your Task (Revised Priority):**

1.  **Analyze Title Block First:** Search the title block for general concrete specifications. Look for designations like "HA-25", "C25/30", or specific exposure classes like "IIa" or "XC3". This information applies to the whole project unless overridden by a specific note.
2.  **Locate the Relevant Element:** Use the user's "Intended Application" to find the specific element (e.g., "column," "slab") on the drawing.
3.  **Find Overriding Element-Specific Notes:** Search for any notes directly attached to or referencing that specific element. These notes can override the general specifications from the title block.

**Information to Extract:**

*   `strength_class_mpa`: The compressive strength in MPa. An "HA-25" designation means 25 MPa. A "C30/37" designation means 30 MPa (use the cylinder value).
*   `min_cement_content`: Minimum cement content in kg/m3.
*   `max_w_c_ratio`: Maximum water-to-cement ratio.
*   `max_aggregate_size`: Maximum aggregate size in mm (e.g., D22). "tamany de l'àrid" in catalan.
*   `drawing_exposure_classes`: A list of exposure classes. Note that Spanish code "IIa" corresponds to Eurocode classes.

**Final Output:**
You must return a single, valid JSON object with **three** keys: `element_specific_reqs`, `drawing_exposure_classes`, and `analysis_notes`.

**Example Scenario (based on a title block):**
- User Intended Application: "Indoor application"
- Your Task: You find "Formigó Estructural: HA-25 / B / 20 / IIa" in the title block (and any other relevant information that may apply).
- Your Output should be:
    {{
      "element_specific_reqs": {{ "strength_class_mpa": 25, "min_cement_content": null, "max_w_c_ratio": null, "max_aggregate_size": 20 }},
      "drawing_exposure_classes": ["XC3", "XA1"],
      "analysis_notes": "Found general concrete specification 'HA-25 / B / 20 / IIa' in the title block on sheet E.01."
    }}
...
"""

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


