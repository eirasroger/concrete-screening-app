import json
from openai import OpenAI
import os


def get_prompt() -> str:
    """
    Returns the prompt for extracting custom technical constraints.
    """
    prompt_file_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'custom_constraints_extractor.txt')
    with open(prompt_file_path, 'r') as f:
        return f.read()


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
        return extracted_data

    except Exception as e:
        return {"error": f"An error occurred during the custom constraint extraction API call: {e}"}

