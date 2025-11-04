import json
from openai import OpenAI

def get_prompt():
    """
    Returns the prompt for extracting custom technical constraints.
    """
    return """You are a highly specialized data extraction bot. Your task is to analyze a user's text and extract three specific technical requirements for concrete.

The requirements to look for are:
1.  `min_cement_content` (in kg/m3)
2.  `max_w_c_ratio` (a decimal value)
3.  `min_mpa_strength` (the compressive strength in MPa)

**Instructions:**
- Analyze the user's text for any mention of these values (whether explicit or implicit semantic similarities).
- Return a single JSON object.
- The JSON object must contain exactly these three keys: `min_cement_content`, `max_w_c_ratio`, `min_mpa_strength`.
- If a value is not mentioned or is unclear, its corresponding key in the JSON must have a value of `null`.
- Do not add any other text, explanation, or formatting. Only the JSON object is allowed.

User Text:
"{custom_info}"
"""

def extract_custom_constraints(custom_info: str, api_key: str) -> dict:
    """
    Uses a dedicated LLM call to extract specific technical constraints from user text.
    """
    if not custom_info or not api_key:
        return {"error": "Custom info or API key is missing."}

    client = OpenAI(api_key=api_key)
    prompt_text = get_prompt().format(custom_info=custom_info)

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        extracted_data = json.loads(response.choices[0].message.content)
        
        # Final validation to ensure the structure is correct
        expected_keys = {"min_cement_content", "max_w_c_ratio", "min_mpa_strength"}
        if not expected_keys.issubset(extracted_data.keys()):
            return {"error": "LLM failed to return the correct JSON structure for custom constraints."}
            
        return extracted_data

    except Exception as e:
        return {"error": f"An error occurred during the custom constraint extraction API call: {e}"}

