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


def get_final_requirements(
    exposure_classes: List[str], 
    regulation_data: dict, 
    user_constraints: dict = None,
    drawing_reqs: dict = None
) -> Dict[str, Any]:
    """
    Aggregates requirements from all sources, correctly handling all constraints
    by choosing the most stringent value for each.
    """
    # --- Combine all known exposure classes from different sources ---
    combined_classes = set()

    # Helper function to safely add items from potentially nested lists
    def add_to_set(items):
        if not items: return
        for item in items:
            if isinstance(item, list): add_to_set(item) # Recurse for nested lists
            elif isinstance(item, str): combined_classes.add(item)
    
    add_to_set(exposure_classes)
    if drawing_reqs and 'drawing_exposure_classes' in drawing_reqs:
        add_to_set(drawing_reqs['drawing_exposure_classes'])

    # --- Initialize requirements and process against regulations ---
    final_reqs = {
        "max_wc": 1.0,  # Permissive start
        "min_cement": 0,  # Permissive start
        "strength_min_cyl": 0,
        "strength_min_cube": 0,
        "max_aggregate_size": float('inf') # Permissive start for a max value
    }
    
    for ec in combined_classes:
        if ec in regulation_data:
            reqs = regulation_data[ec]
            if reqs.get("max_wc") is not None: final_reqs["max_wc"] = min(final_reqs["max_wc"], reqs["max_wc"])
            if reqs.get("min_cement") is not None: final_reqs["min_cement"] = max(final_reqs["min_cement"], reqs["min_cement"])
            if reqs.get("strength_min_cyl") is not None: final_reqs["strength_min_cyl"] = max(final_reqs["strength_min_cyl"], reqs["strength_min_cyl"])
            if reqs.get("strength_min_cube") is not None: final_reqs["strength_min_cube"] = max(final_reqs["strength_min_cube"], reqs["strength_min_cube"])
            if reqs.get("max_aggregate_size") is not None: final_reqs["max_aggregate_size"] = min(final_reqs["max_aggregate_size"], reqs["max_aggregate_size"])

    # --- Override with more stringent requirements from DRAWINGS ---
    if drawing_reqs and 'element_specific_reqs' in drawing_reqs:
        dwg_specific = drawing_reqs['element_specific_reqs']
        if dwg_specific.get("max_w_c_ratio") is not None: final_reqs["max_wc"] = min(final_reqs["max_wc"], dwg_specific["max_w_c_ratio"])
        if dwg_specific.get("min_cement_content") is not None: final_reqs["min_cement"] = max(final_reqs["min_cement"], dwg_specific["min_cement_content"])
        if dwg_specific.get("strength_class_mpa") is not None: final_reqs["strength_min_cyl"] = max(final_reqs["strength_min_cyl"], dwg_specific["strength_class_mpa"])
        if dwg_specific.get("max_aggregate_size") is not None: final_reqs["max_aggregate_size"] = min(final_reqs["max_aggregate_size"], dwg_specific["max_aggregate_size"])

    # --- Override with more stringent USER constraints (Highest Priority) ---
    if user_constraints:
        if user_constraints.get("max_w_c_ratio") is not None: final_reqs["max_wc"] = min(final_reqs["max_wc"], user_constraints["max_w_c_ratio"])
        if user_constraints.get("min_cement_content") is not None: final_reqs["min_cement"] = max(final_reqs["min_cement"], user_constraints["min_cement_content"])
        if user_constraints.get("min_mpa_strength") is not None: final_reqs["strength_min_cyl"] = max(final_reqs["strength_min_cyl"], user_constraints["min_mpa_strength"])
        if user_constraints.get("max_aggregate_size") is not None: final_reqs["max_aggregate_size"] = min(final_reqs["max_aggregate_size"], user_constraints["max_aggregate_size"])

    # Clean up infinite value if no Dmax was ever specified
    if final_reqs["max_aggregate_size"] == float('inf'):
        final_reqs["max_aggregate_size"] = None
        
    final_reqs["source_exposure_classes"] = sorted(list(combined_classes))
    return final_reqs

def calculate_epd_metrics(epd_data: dict) -> Dict[str, Any]:
    """
    Calculates key performance metrics from the specific EPD JSON structure.
    """
    metrics = {
        "calculated_wc": None, 
        "cement_content_kg_m3": None,
        "strength_mpa": epd_data.get("MPa"),
        "max_aggregate_size": epd_data.get("max_aggregate_size")
    }
    
    density = epd_data.get("density")
    mat_comp_list = epd_data.get("mat_comp", [])

    water_mass_percent = 0
    cement_mass_percent = 0
    for material in mat_comp_list:
        name_lower = material.get("name", "").lower()
        percentage = material.get("percentage", 0)
        
        if "water" in name_lower or "agua" in name_lower: water_mass_percent += percentage
        elif "cement" in name_lower or "cem " in name_lower: cement_mass_percent += percentage

    if cement_mass_percent > 0:
        metrics["calculated_wc"] = water_mass_percent / cement_mass_percent
    
    if density and cement_mass_percent > 0:
        metrics["cement_content_kg_m3"] = (cement_mass_percent / 100) * density
        
    return metrics

def perform_compliance_check(epd_metrics: dict, final_reqs: dict) -> Dict[str, Any]:
    """Compares EPD metrics against the final, aggregated requirements."""
    results = {"pass": True, "details": []}

    # Check 1: Water/Cement Ratio
    required_wc = final_reqs.get("max_wc")
    epd_wc = epd_metrics.get("calculated_wc")
    if required_wc is not None and epd_wc is not None and required_wc < 1.0:
        if epd_wc > required_wc:
            results["pass"] = False
            results["details"].append(f"FAIL: EPD w/c ratio ({epd_wc:.2f}) exceeds required max ({required_wc}).")
        else:
            results["details"].append(f"PASS: EPD w/c ratio ({epd_wc:.2f}) meets required max ({required_wc}).")

    # Check 2: Minimum Cement Content
    required_cement = final_reqs.get("min_cement")
    epd_cement = epd_metrics.get("cement_content_kg_m3")
    if required_cement is not None and epd_cement is not None and required_cement > 0:
        if epd_cement < required_cement:
            results["pass"] = False
            results["details"].append(f"FAIL: EPD cement content ({epd_cement:.0f} kg/m3) is below required min ({required_cement} kg/m3).")
        else:
            results["details"].append(f"PASS: EPD cement content ({epd_cement:.0f} kg/m3) meets required min ({required_cement} kg/m3).")
            
    # Check 3: Strength Class (defaulting to cylinder strength)
    required_strength = final_reqs.get("strength_min_cyl")
    epd_strength = epd_metrics.get("strength_mpa")
    if required_strength is not None and epd_strength is not None and required_strength > 0:
        if epd_strength < required_strength:
            results["pass"] = False
            results["details"].append(f"FAIL: EPD strength ({epd_strength} MPa) is below required min cylinder strength ({required_strength} MPa).")
        else:
            results["details"].append(f"PASS: EPD strength ({epd_strength} MPa) meets required min cylinder strength ({required_strength} MPa).")
    
    # Check 4: Maximum Aggregate Size
    required_dmax = final_reqs.get("max_aggregate_size")
    epd_dmax = epd_metrics.get("max_aggregate_size")
    if required_dmax is not None and epd_dmax is not None:
        if epd_dmax > required_dmax:
            results["pass"] = False
            results["details"].append(f"FAIL: EPD aggregate size ({epd_dmax} mm) exceeds required max ({required_dmax} mm).")
        else:
            results["details"].append(f"PASS: EPD aggregate size ({epd_dmax} mm) meets required max ({required_dmax} mm).")

    if not results["details"]:
        results["details"].append("No specific requirements found to check against.")

    return results