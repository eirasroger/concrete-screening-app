import json
import os
from typing import List, Dict, Any

# Define paths relative to this file's location
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
REGULATIONS_DIR = os.path.join(BASE_DIR, 'data', 'regulations')

def load_regulation_file(regulation_name: str) -> dict:
    """Loads the main regulation JSON file (e.g., 'EN 206.json')."""
    filename = regulation_name + ".json"
    filepath = os.path.join(REGULATIONS_DIR, filename)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": f"Regulation file not found: {filepath}"}
    except json.JSONDecodeError:
        return {"error": f"Error decoding JSON from {filepath}"}

def get_final_requirements(exposure_classes: List[str], regulation_data: dict) -> Dict[str, Any]:
    """
    Aggregates the most stringent requirements from a list of exposure classes.
    """
    final_reqs = {
        "max_wc": 0.8,
        "min_cement": 100,
        "strength_min_cyl": 12,
        "strength_min_cube": 15
    }

    if not exposure_classes or "error" in regulation_data or exposure_classes == ["X0"]:
        return {"message": "No specific exposure classes to derive requirements from."}
        
    for ec in exposure_classes:
        if ec in regulation_data:
            reqs = regulation_data[ec]
            if reqs.get("max_wc") is not None:
                final_reqs["max_wc"] = min(final_reqs["max_wc"], reqs["max_wc"])
            if reqs.get("min_cement") is not None:
                final_reqs["min_cement"] = max(final_reqs["min_cement"], reqs["min_cement"])
            if reqs.get("strength_min_cyl") is not None:
                final_reqs["strength_min_cyl"] = max(final_reqs["strength_min_cyl"], reqs["strength_min_cyl"])
            if reqs.get("strength_min_cube") is not None:
                final_reqs["strength_min_cube"] = max(final_reqs["strength_min_cube"], reqs["strength_min_cube"])

    return final_reqs

def calculate_epd_metrics(epd_data: dict) -> Dict[str, Any]:
    """
    Calculates key performance metrics from the specific EPD JSON structure you provided.
    """
    metrics = {
        "calculated_wc": None, 
        "cement_content_kg_m3": None,
        "strength_mpa": None
    }
    
    # Extract top-level properties
    density = epd_data.get("density") # Assumes density is in kg/m3
    strength = epd_data.get("MPa")
    
    # Extract material composition from the list of dictionaries
    mat_comp_list = epd_data.get("mat_comp", [])

    water_mass_percent = 0
    cement_mass_percent = 0
    # Loop through the list to find water and cement
    for material in mat_comp_list:
        name_lower = material.get("name", "").lower()
        percentage = material.get("percentage", 0)
        
        if "water" in name_lower:
            water_mass_percent += percentage
        # This will capture "CEMENT" and other variants
        elif "cement" in name_lower:
            cement_mass_percent += percentage

    # Calculate water/cement ratio by mass percentage
    if cement_mass_percent > 0:
        metrics["calculated_wc"] = water_mass_percent / cement_mass_percent
    
    # Calculate cement content in kg/m3 using density
    if density and cement_mass_percent > 0:
        metrics["cement_content_kg_m3"] = (cement_mass_percent / 100) * density
        
    # Store the extracted strength value
    metrics["strength_mpa"] = strength

    return metrics

def perform_compliance_check(epd_metrics: dict, final_reqs: dict) -> Dict[str, Any]:
    """Compares EPD metrics against the final requirements."""
    results = {"pass": True, "details": []}

    # Check 1: Water/Cement Ratio
    if final_reqs.get("max_wc", 1.0) < 1.0 and epd_metrics.get("calculated_wc") is not None:
        if epd_metrics["calculated_wc"] > final_reqs["max_wc"]:
            results["pass"] = False
            results["details"].append(f"FAIL: EPD w/c ratio ({epd_metrics['calculated_wc']:.2f}) exceeds required max ({final_reqs['max_wc']}).")
        else:
            results["details"].append(f"PASS: EPD w/c ratio ({epd_metrics['calculated_wc']:.2f}) meets required max ({final_reqs['max_wc']}).")

    # Check 2: Minimum Cement Content
    if final_reqs.get("min_cement", 0) > 0 and epd_metrics.get("cement_content_kg_m3") is not None:
        if epd_metrics["cement_content_kg_m3"] < final_reqs["min_cement"]:
            results["pass"] = False
            results["details"].append(f"FAIL: EPD cement content ({epd_metrics['cement_content_kg_m3']:.0f} kg/m3) is below required min ({final_reqs['min_cement']} kg/m3).")
        else:
            results["details"].append(f"PASS: EPD cement content ({epd_metrics['cement_content_kg_m3']:.0f} kg/m3) meets required min ({final_reqs['min_cement']} kg/m3).")
            
    # Check 3: Strength Class (defaulting to cylinder strength for now)
    required_strength = final_reqs.get("strength_min_cyl", 0)
    epd_strength = epd_metrics.get("strength_mpa")
    if required_strength > 0 and epd_strength is not None:
        if epd_strength < required_strength:
            results["pass"] = False
            results["details"].append(f"FAIL: EPD strength ({epd_strength} MPa) is below required min cylinder strength ({required_strength} MPa).")
        else:
            results["details"].append(f"PASS: EPD strength ({epd_strength} MPa) meets required min cylinder strength ({required_strength} MPa).")
    
    if not results["details"]:
        results["details"].append("No specific requirements found to check against.")

    return results
