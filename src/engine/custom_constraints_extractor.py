import os

from .llm_calls import MODEL, TEMPERATURE, build_client
from .schemas import CustomConstraints


def get_prompt() -> str:
    """
    Returns the prompt for extracting custom technical constraints.
    """
    prompt_file_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'custom_constraints_extractor.txt')
    with open(prompt_file_path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_custom_constraints(custom_info: str, api_key: str) -> dict:
    """
    Uses a dedicated LLM call to extract specific technical constraints from user text.
    """
    if not custom_info or not api_key:
        return {"error": "Custom info or API key is missing."}

    client = build_client(api_key)
    prompt_text = get_prompt().format(custom_info=custom_info)

    try:
        response = client.chat.completions.parse(
            model=MODEL,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=TEMPERATURE,
            response_format=CustomConstraints
        )

        message = response.choices[0].message
        if message.refusal:
            return {"error": f"The model declined to answer: {message.refusal}"}
        if message.parsed is None:
            return {"error": "The model returned no parsable content."}

        return message.parsed.model_dump()

    except Exception as e:
        return {"error": f"An error occurred during the custom constraint extraction API call: {e}"}

