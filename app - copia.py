# app.py
import streamlit as st
import pandas as pd
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple

# ---------------------------
# App config
# ---------------------------
st.set_page_config(page_title="Interactive decision support engine for concrete", layout="wide")

# ---------------------------
# Rule model and helpers
# ---------------------------
# EN 206 Table F.1 (subset) for demonstration.


# For production, store these in a versioned JSON/YAML by jurisdiction and load at runtime.
EN206_RULES: Dict[str, Dict[str, Optional[float]]] = {
    # keys: exposure class; values: per-clause numeric constraints (None if not specified)
    # max_wc: maximum w/c ratio; min_cement: kg/m3; strength_min: strength class as cylinder/cube MPa
    "XC1": {"max_wc": 0.65, "min_cement": 260, "strength_min_cyl": 20, "strength_min_cube": 25},
    "XC2": {"max_wc": 0.60, "min_cement": 280, "strength_min_cyl": 25, "strength_min_cube": 30},
    "XC3": {"max_wc": 0.55, "min_cement": 280, "strength_min_cyl": 30, "strength_min_cube": 37},
    "XC4": {"max_wc": 0.50, "min_cement": 300, "strength_min_cyl": 30, "strength_min_cube": 37},

    "XD1": {"max_wc": 0.55, "min_cement": 300, "strength_min_cyl": 30, "strength_min_cube": 37},
    "XD2": {"max_wc": 0.55, "min_cement": 300, "strength_min_cyl": 30, "strength_min_cube": 37},
    "XD3": {"max_wc": 0.45, "min_cement": 320, "strength_min_cyl": 35, "strength_min_cube": 45},

    "XS1": {"max_wc": 0.50, "min_cement": 300, "strength_min_cyl": 30, "strength_min_cube": 37},
    "XS2": {"max_wc": 0.45, "min_cement": 320, "strength_min_cyl": 35, "strength_min_cube": 45},
    "XS3": {"max_wc": 0.45, "min_cement": 340, "strength_min_cyl": 35, "strength_min_cube": 45},

    "XF1": {"max_wc": 0.55, "min_cement": 300, "strength_min_cyl": 30, "strength_min_cube": 37},
    "XF2": {"max_wc": 0.55, "min_cement": 300, "strength_min_cyl": 25, "strength_min_cube": 30},
    "XF3": {"max_wc": 0.50, "min_cement": 320, "strength_min_cyl": 30, "strength_min_cube": 37},
    "XF4": {"max_wc": 0.45, "min_cement": 340, "strength_min_cyl": 30, "strength_min_cube": 37},

    "XA1": {"max_wc": 0.55, "min_cement": 300, "strength_min_cyl": 30, "strength_min_cube": 37},
    "XA2": {"max_wc": 0.50, "min_cement": 320, "strength_min_cyl": 30, "strength_min_cube": 37},
    "XA3": {"max_wc": 0.45, "min_cement": 360, "strength_min_cyl": 35, "strength_min_cube": 45},


    # XF/XA need additional parameters (min air content etc)
}

@dataclass
class Product:
    name: str
    wc: Optional[float] = None            # water/cement ratio
    cement_kg_m3: Optional[float] = None  # kg/m3
    strength_class: Optional[str] = None  # e.g., "C30/37"

def parse_strength(strength: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse "C30/37" or "C25/30" into (cylinder, cube) MPa integers.
    Returns (None, None) if parsing fails.
    """
    if not strength:
        return None, None
    s = strength.strip().upper().replace("C", "")
    try:
        parts = s.split("/")
        cyl = int(parts[0]) if parts[0].isdigit() else None
        cube = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        return cyl, cube
    except Exception:
        return None, None

def combine_constraints(selected: List[str], rulebook: Dict[str, Dict[str, Optional[float]]]) -> Dict[str, Optional[float]]:
    """
    Combine multiple exposure classes by taking the most onerous constraint per clause:
    - max_wc: minimum across selected (stricter = smaller)
    - min_cement: maximum across selected (stricter = larger)
    - strength_min: maximum required strengths across selected
    """
    if not selected:
        return {}
    max_wc_vals = []
    min_cement_vals = []
    min_cyl = []
    min_cube = []
    for ex in selected:
        rule = rulebook.get(ex, {})
        if rule.get("max_wc") is not None:
            max_wc_vals.append(rule["max_wc"])
        if rule.get("min_cement") is not None:
            min_cement_vals.append(rule["min_cement"])
        if rule.get("strength_min_cyl") is not None:
            min_cyl.append(rule["strength_min_cyl"])
        if rule.get("strength_min_cube") is not None:
            min_cube.append(rule["strength_min_cube"])
    combined = {
        "max_wc": min(max_wc_vals) if max_wc_vals else None,
        "min_cement": max(min_cement_vals) if min_cement_vals else None,
        "strength_min_cyl": max(min_cyl) if min_cyl else None,
        "strength_min_cube": max(min_cube) if min_cube else None,
    }
    return combined

def check_product(prod: Product, combined_rules: Dict[str, Optional[float]]) -> Tuple[str, List[str]]:
    """
    Return (status, reasons) where status ∈ {"Pass","Fail"} and reasons list explains each clause.
    """
    reasons: List[str] = []
    status = "Pass"

    # w/c
    req_wc = combined_rules.get("max_wc")
    if req_wc is not None:
        if prod.wc is None:
            status = "Fail"
            reasons.append(f"Missing w/c; requires ≤ {req_wc:.2f}")
        elif prod.wc > req_wc:
            status = "Fail"
            reasons.append(f"w/c {prod.wc:.2f} exceeds limit ≤ {req_wc:.2f}")

    # cement content
    req_cem = combined_rules.get("min_cement")
    if req_cem is not None:
        if prod.cement_kg_m3 is None:
            status = "Fail"
            reasons.append(f"Missing cement content; requires ≥ {int(req_cem)} kg/m³")
        elif prod.cement_kg_m3 < req_cem:
            status = "Fail"
            reasons.append(f"Cement {int(prod.cement_kg_m3)} kg/m³ below ≥ {int(req_cem)} kg/m³")

    # strength class
    req_cyl = combined_rules.get("strength_min_cyl")
    req_cube = combined_rules.get("strength_min_cube")
    cyl, cube = parse_strength(prod.strength_class)
    if req_cyl is not None or req_cube is not None:
        if cyl is None or cube is None:
            status = "Fail"
            needed = f"C{req_cyl}/{req_cube}" if (req_cyl and req_cube) else "required strength class"
            reasons.append(f"Missing or unparsable strength class; requires ≥ {needed}")
        else:
            if req_cyl is not None and cyl < req_cyl:
                status = "Fail"
                reasons.append(f"Cylinder {cyl} < required {req_cyl}")
            if req_cube is not None and cube < req_cube:
                status = "Fail"
                reasons.append(f"Cube {cube} < required {req_cube}")

    if not reasons and status == "Pass":
        reasons.append("All selected constraints satisfied")
    return status, reasons

def load_products_from_csv(file) -> List[Product]:
    """
    Optional helper to read a CSV with columns:
    name,wc,cement_kg_m3,strength_class
    Returns a list of Product instances.
    """
    df = pd.read_csv(file)
    products: List[Product] = []
    for _, row in df.iterrows():
        products.append(
            Product(
                name=str(row.get("name", "Unnamed")),
                wc=float(row["wc"]) if pd.notna(row.get("wc")) else None,
                cement_kg_m3=float(row["cement_kg_m3"]) if pd.notna(row.get("cement_kg_m3")) else None,
                strength_class=str(row["strength_class"]) if pd.notna(row.get("strength_class")) else None,
            )
        )
    return products

# ---------------------------
# Sidebar controls
# ---------------------------
with st.sidebar:
    st.header("Scenario")
    jurisdiction = st.selectbox(
        "Jurisdiction",
        ["EN 206", "AS 3600", "Custom"],
        help="Select the regulatory context to apply",
    )
    exposure_classes = st.multiselect(
        "Exposure classes",
        ["XC1", "XC2", "XC3", "XC4", "XD1", "XD2", "XD3", "XS1", "XS2", "XS3","XF1","XF2","XF3","XF4","XA1","XA2","XA3"],
        default=["XC4"],
        help="Choose one or more exposure/durability classes",
    )
    extra_constraints = st.text_input(
        "Additional constraints (optional)",
        placeholder="Add custom constraints here",
    )
    uploaded_files = st.file_uploader(
        "Upload product files (EPD/datasheet PDFs or CSVs)",
        accept_multiple_files=True,
        help="You can upload multiple product documents for screening",
    )
    csv_upload = st.file_uploader(
        "Or upload a Products CSV (name,wc,cement_kg_m3,strength_class)",
        type=["csv"],
        accept_multiple_files=False,
        help="Fast path for testing without parsing PDFs.",
        key="csv_upload",
    )

# ---------------------------
# Main layout
# ---------------------------
st.title("Interactive decision support engine for concrete compliance screening")
st.caption("Developed by R. Vergés, K. Gaspar, N. Forcada, and M. R. Hosseini (2026).")

# Scenario summary
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Jurisdiction", jurisdiction)
with col2:
    st.metric("Exposure", ", ".join(exposure_classes) if exposure_classes else "None")
with col3:
    total_files = len(uploaded_files) if uploaded_files else 0
    total_files += 1 if csv_upload is not None else 0
    st.metric("Uploaded files", total_files)

st.divider()

# Action buttons
c1, c2 = st.columns([1, 1])
with c1:
    run_clicked = st.button("Run checks", type="primary", help="Execute compliance checks")
with c2:
    clear_clicked = st.button("Clear results", help="Reset the table and messages", key="clear_btn")

# ---------------------------
# Run checks
# ---------------------------
if run_clicked:
    st.info("Running rule checks against selected exposure classes.", icon="🔧")

    # Select rulebook by jurisdiction (for now, EN 206 and BS 8500 both map to EN206_RULES as demo)
    if jurisdiction.startswith("EN 206"):
        ruleset = EN206_RULES
    elif jurisdiction.startswith("BS 8500"):
        # In production, provide a BS 8500 mapping dict here
        ruleset = EN206_RULES
    else:
        # Custom: fall back to EN206_RULES or later allow user-defined inputs
        ruleset = EN206_RULES

    # Combine constraints for all selected exposures
    combined = combine_constraints(exposure_classes, ruleset)
    if not exposure_classes:
        st.warning("No exposure classes selected.")
    else:
        with st.expander("Applied limits (combined)"):
            st.write({
                "max w/c (≤)": combined.get("max_wc"),
                "min cement (kg/m³ ≥)": combined.get("min_cement"),
                "min strength class (Cyl/Cube ≥)": f"C{combined.get('strength_min_cyl')}/{combined.get('strength_min_cube')}",
            })

    # Load products:
    products: List[Product] = []

    # CSV route (recommended for quick testing)
    if csv_upload is not None:
        try:
            products = load_products_from_csv(csv_upload)
            st.success(f"Loaded {len(products)} products from CSV.")
        except Exception as e:
            st.error(f"Failed to parse CSV: {e}")

    # If no CSV provided, use mock products for demo
    if not products:
        products = [
            Product(name="Concrete A", wc=0.60, cement_kg_m3=300, strength_class="C25/30"),
            Product(name="Concrete B", wc=0.52, cement_kg_m3=290, strength_class="C30/37"),
            Product(name="Concrete C", wc=0.48, cement_kg_m3=320, strength_class="C30/37"),
        ]
        st.caption("Using mock products. Upload a CSV to test your own data.")

    # Evaluate
    rows = []
    for p in products:
        status, reasons = check_product(p, combined)
        rows.append({
            "Product": p.name,
            "Status": status,
            "Reason": "; ".join(reasons),
            "w/c": p.wc,
            "Cement (kg/m³)": p.cement_kg_m3,
            "Strength": p.strength_class,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    # Download results
    csv_out = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download results (CSV)", data=csv_out, file_name="compliance_results.csv", mime="text/csv")

    # Detail expanders
    for p, r in zip(products, rows):
        with st.expander(f"Details: {p.name}"):
            st.write(f"- Status: {r['Status']}")
            st.write(f"- Reasons: {r['Reason']}")
            st.write(f"- Values: w/c={p.wc}, cement={p.cement_kg_m3} kg/m³, strength={p.strength_class}")

else:
    st.caption("Upload one or more product files (or a CSV) and click Run checks to evaluate compliance.")
