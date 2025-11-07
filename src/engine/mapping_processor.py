

import os
import re
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


def get_few_shot_examples(standard: str) -> list[dict]:
    """
    Returns a list of few-shot examples for the specified standard.
    """
    if standard == "en206":
        return [
            {
                "role": "user",
                "scenario": "Concrete for a bridge deck exposed to de-icing salts.",
                "assistant_response": '{"assigned_exposure_classes": ["XC4", "XD3", "XF4"]}'
            },
            {
                "role": "user",
                "scenario": "The concrete will be used inside a building. high humidity.",
                "assistant_response": '{"assigned_exposure_classes": ["XC3"]}'
            },
            {
                "role": "user",
                "scenario": "A standard house foundation in a dry, inland area.",
                "assistant_response": '{"assigned_exposure_classes": ["X0"]}'
            }
        ]
    elif standard == "as3600":

        return [
            {
                "role": "user",
                "scenario": "Internal slab in a non-aggressive environment.",
                "assistant_response": '{"assigned_exposure_classes": ["A1"]}'
            },
            {
                "role": "user",
                "scenario": "External column in a coastal area subject to airborne salt.",
                "assistant_response": '{"assigned_exposure_classes": ["B2"]}'
            },
            {
                "role": "user",
                "scenario": "Maritime structure exposed to spray from seawater.",
                "assistant_response": '{"assigned_exposure_classes": ["C1"]}'
            }
        ]
    return []



def determine_exposure_classes_with_llm(custom_info: str, mapping: dict, standard: str, api_key: str) -> dict:
    """
    Determines a list of applicable exposure classes using an LLM with a few-shot example set.
    """
    if not custom_info or not api_key:
        return {"error": "Custom info or API key is missing."}
    if "error" in mapping:
        return mapping

    client = OpenAI(api_key=api_key)
   # Normalize the standard input to handle variations like 'EN 206', 'en 206', etc.
    standard_normalized = re.sub(r'\s+', '', standard.lower())

    if standard_normalized == "en206":
        prompt_name = "exposure_class_determination"
        standard_title = "EN 206"
    elif standard_normalized == "as3600":
        prompt_name = "exposure_class_determination_AS3600"
        standard_title = "AS 3600"
    else:
        # The error message now correctly reflects the logic.
        return {"error": f"The provided standard '{standard}' is not supported. Use 'en206' or 'AS3600'."}


    # Load the base instructions from the appropriate text file
    instructions = get_prompt_template(prompt_name)
    if instructions.startswith("ERROR"):
        return {"error": instructions}

    # Serialize mapping data and get the correct few-shot examples
    mapping_str = json.dumps(mapping, indent=2)
    examples = get_few_shot_examples(standard)

    # Construct the full messages payload dynamically
    messages = []
    for example in examples:
        content = f"""{instructions}
---
## Available Exposure Classes ({standard_title})
{mapping_str}
## User-Provided Scenario
{example['scenario']}"""
        messages.append({"role": "user", "content": content})
        messages.append({"role": "assistant", "content": example['assistant_response']})

    # Add the REAL question for the model to answer
    messages.append({
        "role": "user",
        "content": f"""{instructions}
---
## Available Exposure Classes ({standard_title})
{mapping_str}
## User-Provided Scenario
{custom_info}"""
    })

    try:
        # Make the API call
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # 6. Validate the response from the LLM
        if "assigned_exposure_classes" not in result or not isinstance(result["assigned_exposure_classes"], list):
            return {"error": "LLM returned an invalid data format.", "raw_response": result}
        
        return result

    except Exception as e:
        return {"error": f"An API error occurred: {str(e)}"}

def save_custom_analysis_result(result: dict, filename: str = "custom_info_result.json"):
    if not os.path.exists(CUSTOM_INFO_OUTPUT_DIR):
        os.makedirs(CUSTOM_INFO_OUTPUT_DIR)
    
    output_path = os.path.join(CUSTOM_INFO_OUTPUT_DIR, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4)
