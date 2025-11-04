

import os
import json
from openai import OpenAI
from .llm_calls import get_prompt_template

# Define paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MAPPINGS_DIR = os.path.join(BASE_DIR, 'data', 'mappings')
CUSTOM_INFO_OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'output', 'custom_information')


def load_mapping_file(regulation_name: str, mapping_type: str = "exposure_class") -> dict:
    """
    Loads a specific mapping JSON file based on the regulation and type.
    Example filename: 'en206_exposure_class_mapping.json'
    """
    # --- FIX: Remove spaces from the regulation name ---
    cleaned_regulation_name = regulation_name.lower().replace(" ", "")
    
    mapping_filename = f"{cleaned_regulation_name}_{mapping_type}_mapping.json"
    mapping_path = os.path.join(MAPPINGS_DIR, mapping_filename)
    
    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": f"Mapping file not found at {mapping_path}"}
    except json.JSONDecodeError:
        return {"error": f"Could not decode JSON from {mapping_path}"}


def determine_exposure_classes_with_llm(custom_info: str, mapping: dict, api_key: str) -> dict:
    """
    Determines a list of applicable exposure classes using an LLM with a few-shot example set.
    """
    if not custom_info or not api_key:
        return {"error": "Custom info or API key is missing."}
    if "error" in mapping:
        return mapping

    client = OpenAI(api_key=api_key)

    # 1. Load the base instructions from your text file
    instructions = get_prompt_template("exposure_class_determination")
    if instructions.startswith("ERROR"):
        return {"error": instructions}

    # 2. Serialize your mapping data to a string
    mapping_str = json.dumps(mapping, indent=2)

    try:
        # 3. Construct the full messages payload with instructions and few-shot examples
        messages = [
            # Example 1: A complex, multi-class scenario to teach the model
            {
                "role": "user",
                "content": f"""{instructions}

---

## Available Exposure Classes (EN 206)
{mapping_str}

## User-Provided Scenario
Concrete for a bridge deck exposed to de-icing salts."""
            },
            {
                "role": "assistant",
                "content": '{"assigned_exposure_classes": ["XC4", "XD3", "XF4"]}'
            },
            # Example 2: Your specific simple case to ensure it gets it right
            {
                "role": "user",
                "content": f"""{instructions}

---

## Available Exposure Classes (EN 206)
{mapping_str}

## User-Provided Scenario
The concrete will be used inside a building. high humidity."""
            },
            {
                "role": "assistant",
                "content": '{"assigned_exposure_classes": ["XC3"]}'
            },
            # Example 3: A case that should correctly default to X0
            {
                "role": "user",
                "content": f"""{instructions}

---

## Available Exposure Classes (EN 206)
{mapping_str}

## User-Provided Scenario
A standard house foundation in a dry, inland area."""
            },
            {
                "role": "assistant",
                "content": '{"assigned_exposure_classes": ["X0"]}'
            },
            # The REAL question for the model to answer now
            {
                "role": "user",
                "content": f"""{instructions}

---

## Available Exposure Classes (EN 206)
{mapping_str}

## User-Provided Scenario
{custom_info}"""
            }
        ]

        # 4. Make the API call
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=messages,
            temperature=0.1, 
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # 5. Validate the response from the LLM
        if "assigned_exposure_classes" not in result or not isinstance(result["assigned_exposure_classes"], list):
             return {"error": "LLM returned an invalid data format.", "raw_response": result}
        
        return result

    except Exception as e:
        return {"error": f"An error occurred during the API call: {e}"}

def save_custom_analysis_result(result: dict, filename: str = "custom_info_result.json"):
    if not os.path.exists(CUSTOM_INFO_OUTPUT_DIR):
        os.makedirs(CUSTOM_INFO_OUTPUT_DIR)
    
    output_path = os.path.join(CUSTOM_INFO_OUTPUT_DIR, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4)
