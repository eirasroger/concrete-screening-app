# Extraction evaluation

This directory measures how accurately the application reads data from EPD
documents. It runs the same extraction code the application uses, compares the
result against values established by hand, and reports per-field accuracy.

## Layout

```
eval/
├── run_eval.py                 # the harness
├── fixtures/
│   ├── epds/                   # the EPD PDFs (not committed, see below)
│   ├── ground_truth/           # hand-established correct values, one JSON per PDF
│   └── manifest.json           # publisher, registration number and URL of each EPD
└── results/                    # one record per run (not committed)
```

The PDFs themselves are not committed, because EPDs are published by their
issuing organisations under their own terms. `manifest.json` records where each
document came from, so that the evaluation set can be reconstructed by anyone
who wishes to repeat the measurement.

## Procedure

1. Place the EPD PDFs in `fixtures/epds/`.

2. Create a blank ground-truth file for each:

   ```
   python eval/run_eval.py --make-template
   ```

3. Fill in each file in `fixtures/ground_truth/` by reading the EPD. This step
   is deliberately manual: the purpose of the evaluation is to compare the
   model against a human reading of the document, so the expected values must
   be established independently of the model.

   - A field set to `null` means the value is genuinely absent from the EPD.
     The extraction is expected to return `null` too, and is marked correct
     when it does.
   - A field deleted from the file is treated as not yet labelled and is
     skipped rather than counted as a failure. Partial labelling is therefore
     fine to start with.
   - Record who labelled the file and when, in `_labelled_by` and
     `_labelled_on`.

4. Run the evaluation:

   ```
   python eval/run_eval.py
   ```

   Each run costs one API call per document. The key is taken from `--api-key`,
   then `OPENAI_API_KEY`, then `.streamlit/secrets.toml`.

## What is measured

Two groups of fields are reported separately.

**Fields read directly from the document** — `EPD_registration_number`,
`density`, `MPa` and `max_aggregate_size`, plus the cement and water
percentages taken from the material composition table.

`EPD_name` is extracted by the application but is deliberately not scored. The
cover page, the product-name field and the product table frequently give
different forms of the name, so there is no single correct answer to compare
against; the registration number identifies the document unambiguously
instead.

**Values derived by the compliance engine** — `calculated_wc` and
`cement_content_kg_m3`. These are the quantities that actually determine a
pass or fail verdict, so an error here matters more than an error in a field
that no check consults.

Numeric comparisons use the tolerances declared in `TOLERANCES` at the top of
`run_eval.py`, chosen so that a difference too small to change a compliance
verdict is not counted as an error. The registration number is compared
ignoring case and spacing.

## Repeated runs

The model is not deterministic. To see how much the output varies between
identical requests:

```
python eval/run_eval.py --repeats 3
```

Each repetition is scored separately, so a field that is read correctly two
times out of three is reported as 67%.

## Interpreting the results

Every run writes a record to `results/` containing the model identifier, a
fingerprint of the prompt, and the full comparison for each document. The
fingerprint changes whenever the extraction prompt is edited, which is what
makes two runs comparable: a change in accuracy can be attributed to a prompt
revision, a model change, or neither.

Keep the sample size in mind when quoting a figure. Six documents with eight
labelled fields give around fifty comparisons, which is enough to expose a
field that fails systematically.
