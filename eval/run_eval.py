"""
Evaluation harness for the EPD extraction step.

Runs the production extraction code over a set of EPD PDFs whose correct values
have been established by hand, and reports how often each field is read
correctly. Results are written to eval/results/ with the model identifier and a
hash of the prompt, so that a later run can be compared against an earlier one.

Usage:
    python eval/run_eval.py --make-template     # create blank ground-truth files
    python eval/run_eval.py                     # run the evaluation
    python eval/run_eval.py --repeats 3         # repeat, to observe variability

The API key is read from --api-key, then the OPENAI_API_KEY environment
variable, then .streamlit/secrets.toml.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(EVAL_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.engine.llm_calls import extract_epd_data, get_prompt_template, MODEL  # noqa: E402
from src.engine.compliance_checker import calculate_epd_metrics  # noqa: E402

EPD_DIR = os.path.join(EVAL_DIR, 'fixtures', 'epds')
GROUND_TRUTH_DIR = os.path.join(EVAL_DIR, 'fixtures', 'ground_truth')
RESULTS_DIR = os.path.join(EVAL_DIR, 'results')

# Tolerance applied when comparing a numeric field. 
TOLERANCES = {
    "density": 1.0,
    "MPa": 0,
    "max_aggregate_size": 0.1,
    "cement_percentage": 0.5,
    "water_percentage": 0.5,
    "calculated_wc": 0.02,
    "cement_content_kg_m3": 5.0,
}

# Fields compared directly against the extracted JSON.
# EPD_name is deliberately not scored: the cover page, the product-name field and
# the product table often give different forms of the name, so there is no single
# correct answer. EPD_registration_number identifies the document unambiguously.
DIRECT_FIELDS = ["EPD_registration_number", "density", "MPa", "max_aggregate_size"]

# Fields derived by the compliance engine. These are the values that actually
# drive a pass/fail verdict, so they are reported separately.
DERIVED_FIELDS = ["calculated_wc", "cement_content_kg_m3"]


def normalise_name(value):
    """Loose string comparison: case and whitespace are ignored."""
    if value is None:
        return None
    return " ".join(str(value).lower().split())


def values_match(field, expected, actual):
    """Returns True when actual matches expected within the field tolerance."""
    if expected is None or actual is None:
        return expected is None and actual is None

    if field == "EPD_registration_number":
        return normalise_name(expected) == normalise_name(actual)

    try:
        tolerance = TOLERANCES.get(field, 0)
        return abs(float(expected) - float(actual)) <= tolerance
    except (TypeError, ValueError):
        return str(expected) == str(actual)


def material_percentage(extracted, keywords, exclude=()):
    """Sums the percentages of materials whose name matches any keyword."""
    total = None
    for material in extracted.get("mat_comp") or []:
        name = (material.get("name") or "").lower()
        if any(k in name for k in keywords) and not any(x in name for x in exclude):
            total = (total or 0) + (material.get("percentage") or 0)
    return total


def compare(expected, extracted):
    """
    Compares one extraction against its ground truth.

    A field absent from the ground-truth file is treated as not yet labelled and
    is skipped rather than counted as a failure.
    """
    comparisons = {}

    for field in DIRECT_FIELDS:
        if field not in expected:
            continue
        actual = extracted.get(field)
        comparisons[field] = {
            "expected": expected[field],
            "actual": actual,
            "match": values_match(field, expected[field], actual),
        }

    # Composition is compared through the two quantities the engine uses.
    for field, keywords, exclude in [
        ("cement_percentage", ("cement", "cem "), ("supplementary", "cementitious")),
        ("water_percentage", ("water", "agua"), ()),
    ]:
        if field not in expected:
            continue
        actual = material_percentage(extracted, keywords, exclude)
        comparisons[field] = {
            "expected": expected[field],
            "actual": actual,
            "match": values_match(field, expected[field], actual),
        }

    metrics = calculate_epd_metrics(extracted)
    for field in DERIVED_FIELDS:
        if field not in expected:
            continue
        comparisons[field] = {
            "expected": expected[field],
            "actual": metrics.get(field),
            "match": values_match(field, expected[field], metrics.get(field)),
        }

    return comparisons


def make_templates():
    """Writes a blank ground-truth file for each PDF that does not have one."""
    pdfs = sorted(f for f in os.listdir(EPD_DIR) if f.lower().endswith('.pdf'))
    if not pdfs:
        print("No PDFs found in " + EPD_DIR)
        return

    created = 0
    for pdf in pdfs:
        target = os.path.join(GROUND_TRUTH_DIR, os.path.splitext(pdf)[0] + '.json')
        if os.path.exists(target):
            print("  exists, left alone : " + os.path.basename(target))
            continue
        template = {
            "_source_pdf": pdf,
            "_labelled_by": "",
            "_labelled_on": "",
            "EPD_registration_number": None,
            "density": None,
            "MPa": None,
            "max_aggregate_size": None,
            "cement_percentage": None,
            "water_percentage": None,
            "calculated_wc": None,
            "cement_content_kg_m3": None,
        }
        with open(target, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2)
        created += 1
        print("  created            : " + os.path.basename(target))
    print("\n{} template(s) created in {}".format(created, GROUND_TRUTH_DIR))


def resolve_api_key(cli_key):
    """Finds an API key from the CLI, the environment, or secrets.toml."""
    if cli_key:
        return cli_key
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    secrets = os.path.join(PROJECT_ROOT, '.streamlit', 'secrets.toml')
    if os.path.exists(secrets):
        try:
            import tomllib
            with open(secrets, 'rb') as f:
                return tomllib.load(f).get("OPENAI_API_KEY")
        except Exception:
            pass
    return None


def prompt_fingerprint():
    """Short hash of the extraction prompt, to tie results to a prompt version."""
    prompt = get_prompt_template("epd_extraction")
    return hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:12]


def run(api_key, repeats):
    pdfs = sorted(f for f in os.listdir(EPD_DIR) if f.lower().endswith('.pdf'))
    if not pdfs:
        print("No PDFs found in " + EPD_DIR + ". Add the evaluation EPDs there first.")
        return 1

    run_record = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "prompt_fingerprint": prompt_fingerprint(),
        "repeats": repeats,
        "files": {},
    }

    field_totals = {}
    skipped = []

    for pdf in pdfs:
        gt_path = os.path.join(GROUND_TRUTH_DIR, os.path.splitext(pdf)[0] + '.json')
        if not os.path.exists(gt_path):
            skipped.append(pdf)
            continue
        with open(gt_path, encoding='utf-8') as f:
            expected = {k: v for k, v in json.load(f).items() if not k.startswith('_')}

        print("\n" + pdf)
        attempts = []
        for i in range(repeats):
            extracted = extract_epd_data(api_key, os.path.join(EPD_DIR, pdf))
            if "error" in extracted:
                print("  run {}: extraction failed - {}".format(i + 1, extracted["error"]))
                attempts.append({"error": extracted["error"]})
                continue

            comparisons = compare(expected, extracted)
            attempts.append({"extracted": extracted, "comparisons": comparisons})

            for field, outcome in comparisons.items():
                totals = field_totals.setdefault(field, {"match": 0, "total": 0})
                totals["total"] += 1
                totals["match"] += 1 if outcome["match"] else 0

            hits = sum(1 for c in comparisons.values() if c["match"])
            print("  run {}: {}/{} fields correct".format(i + 1, hits, len(comparisons)))
            for field, outcome in comparisons.items():
                if not outcome["match"]:
                    print("      {}: expected {!r}, got {!r}".format(
                        field, outcome["expected"], outcome["actual"]))

        run_record["files"][pdf] = attempts

    print("\n" + "=" * 62)
    print("model {}   prompt {}   repeats {}".format(
        MODEL, run_record["prompt_fingerprint"], repeats))
    print("=" * 62)
    print("{:<24} {:>10} {:>12}".format("field", "correct", "accuracy"))
    print("-" * 62)
    overall_match = 0
    overall_total = 0
    for field, totals in field_totals.items():
        pct = 100.0 * totals["match"] / totals["total"] if totals["total"] else 0.0
        print("{:<24} {:>4}/{:<5} {:>11.1f}%".format(
            field, totals["match"], totals["total"], pct))
        overall_match += totals["match"]
        overall_total += totals["total"]
    print("-" * 62)
    overall_pct = 100.0 * overall_match / overall_total if overall_total else 0.0
    print("{:<24} {:>4}/{:<5} {:>11.1f}%".format(
        "OVERALL", overall_match, overall_total, overall_pct))

    if skipped:
        print("\nSkipped, no ground truth file: " + ", ".join(skipped))
        print("Run with --make-template to create one for each.")

    run_record["summary"] = {
        "field_totals": field_totals,
        "overall_match": overall_match,
        "overall_total": overall_total,
        "overall_accuracy": overall_pct,
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out_path = os.path.join(RESULTS_DIR, 'eval_' + stamp + '.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(run_record, f, indent=2)
    print("\nFull record written to " + os.path.relpath(out_path, PROJECT_ROOT))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate EPD extraction against hand-labelled ground truth.")
    parser.add_argument('--make-template', action='store_true',
                        help="create blank ground-truth files for the PDFs present")
    parser.add_argument('--repeats', type=int, default=1,
                        help="number of times to extract each PDF (default 1)")
    parser.add_argument('--api-key',
                        help="OpenAI API key; otherwise taken from the environment or secrets.toml")
    args = parser.parse_args()

    if args.make_template:
        make_templates()
        return 0

    api_key = resolve_api_key(args.api_key)
    if not api_key:
        print("No API key found. Pass --api-key, set OPENAI_API_KEY, "
              "or add it to .streamlit/secrets.toml.")
        return 1

    return run(api_key, max(1, args.repeats))


if __name__ == '__main__':
    raise SystemExit(main())
