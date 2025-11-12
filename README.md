# Interactive Decision-Support Engine for Compliance Screening

**➡️ [Try the live application here!](https://concrete-screening-app.streamlit.app/) ⬅️**

*(Note: If the app is asleep due to inactivity, please press the button on the page to wake it. It will load shortly after.)*

## Project Overview

This project presents an interactive decision-support engine designed to automate and streamline the **durability compliance screening** of concrete products. The tool helps engineers and sustainability experts make faster, more informed material selections by evaluating Environmental Product Declarations (EPDs) against project-specific requirements. 


The engine integrates three key data sources:
1.  **Regulatory schemas:** Frameworks like EN 206 (Europe) or AS 3600 (Australia) provide the baseline durability requirements and exposure class thresholds.
2.  **Document intelligence:** A Large Language Model (LLM) performs data extraction from uploaded PDFs, including EPDs and technical drawings, to retrieve critical parameters.
3.  **User-defined context:** Custom text inputs allow users to specify additional constraints, such as unique environmental conditions or performance targets that exceed regulatory minimums.

The system synthesises this information to create a comprehensive screening scenario, ultimately providing a clear "pass/fail" verdict for each concrete product.

While the case study in this project focuses on concrete, the methodological framework is designed for broader application. Its adaptation to other construction products requires updating the associated regulations, prompts, and compliance checks.

## Features

- **Multi-source data integration:** Harmonises requirements from regulatory JSON files, user-defined text, and PDF documents (EPDs and drawings).
- **LLM-powered data extraction:** Automatically parses PDF documents to extract structured technical data, such as material composition, water-to-cement ratios, and characteristic strength.
- **Dynamic compliance engine:** Evaluates concrete products against a consolidated set of the most stringent requirements from all available data sources.
- **Jurisdiction-specific analysis:** Adapts the screening process based on user-selected regulatory schemas (e.g., EN 206 vs. AS 3600).
- **Conflict resolution:** The engine ensures compliance by always adopting the most stringent requirement. If a user's input is stricter than the regulatory standard, the user's value prevails. Conversely, mandatory regulatory minimums are always enforced, even if a user suggests a less stringent value.
- **Interactive UI:** A user-friendly interface built with Streamlit for easy document uploads, requirement definition, and results visualisation.

## Getting Started



You can use the live, deployed application or run a copy locally on your own machine.

### Using the Live App


1.  **Navigate to the app:** [https://concrete-screening-app.streamlit.app/](https://concrete-screening-app.streamlit.app/)
2.  **Wake the app (if needed)**: If the application has been inactive, you may see a "sleeping" screen. Simply press the button to wake it up.
3.  **Provide your API Key:** The application will prompt you to enter your own OpenAI API Key. Your key is not stored and is only used for the duration of your session.
4.  **Start screening:** Follow the on-screen instructions to upload documents and define your scenario.




### Running Locally

Follow these steps to get a local copy up and running.

**Prerequisites:**

- Python 3.12.7 or higher
- An OpenAI API Key

**Quick Start:**

1.  **Clone the repository:**
    ```
    git clone https://github.com/eirasroger/concrete-screening-app
    cd concrete-screening-app
    ```

2.  **Install dependencies:**
    It is recommended to use a virtual environment.
    ```
    pip install -r requirements.txt
    ```

3.  **Configure your API key:**
    - Create a folder named `.streamlit` in the root of your project directory.
    - Inside the `.streamlit` folder, create a new file named `secrets.toml`.
    - Add your OpenAI API key to the file like this:
      ```
      OPENAI_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      ```

*Note: The application is designed to find your API key in the `secrets.toml` file first. If that file is not present, the app will fall back to prompting you for your key directly in the user interface. You can choose whichever method you prefer for local development.*


4.  **Run the application:**
    ```
    streamlit run app.py
    ```
*Depending on your choice in step 3, the app will either load directly or first ask you to provide your API key.*

## Repository Structure
```
.
├── .gitignore # Specifies intentionally untracked files to ignore
├── README.md # This file
├── app.py # The main Streamlit application entry point
├── requirements.txt # Python package dependencies
│
├── .streamlit/
│ └── secrets.toml # Configuration for API keys and other secrets
│
├── data/ # Contains all project data, organised by type
│ ├── input/
│ │ ├── custom_information/ # Folder for user-defined text requirements
│ │ ├── drawings/ # Folder for uploaded technical drawings
│ │ └── epds/ # Folder for uploaded EPD PDF files
│ │
│ ├── mappings/
│ │ ├── en206_exposure_class_mapping.json
│ │ └── as3600_exposure_class_mapping.json
│ │
│ ├── output/
│ │ ├── custom_information/ # Stores extracted data from custom info
│ │ ├── drawings/ # Stores extracted data from drawings
│ │ └── epds/ # Stores extracted data from EPDs
│ │
│ └── regulations/
│ ├── EN_206.json
│ └── AS_3600.json
│
└── src/ # All source code for the application
├── engine/ # Core logic for the compliance engine
│ ├── compliance_checker.py
│ ├── custom_constraints_extractor.py
│ ├── drawing_processor.py
│ ├── file_handler.py
│ ├── llm_calls.py
│ ├── mapping_processor.py
│ └── regulations.py
│
├── prompts/ # Text files containing prompts for the LLM
│ ├── custom_constraints_extractor.txt
│ ├── drawing_processor.txt
│ ├── epd_extraction.txt
│ ├── exposure_class_determination.txt
│ └── exposure_class_determination_AS3600.txt
│
└── UI/ # Modules related to the Streamlit user interface
└── ui_inputs.py
```


## Use Cases

This engine is designed to be flexible and can be adapted to several common industry scenarios:

-   **Scenario 1: Preliminary product screening**

    An engineer has a list of potential concrete suppliers for a new project. They can quickly upload all supplier EPDs and screen them against the default regulatory schema (e.g., EN 206) to create a shortlist of compliant products for a standard application, like an indoor column.

-   **Scenario 2: Detailed design compliance**

    A structural engineer is designing a foundation for a building in a coastal area. They upload the relevant EPDs, a technical drawing of the foundation, and add a custom text requirement: "High durability required for coastal environment with saltwater spray." The engine correctly identifies the need for a more stringent exposure class (e.g., XS3), combines it with requirements from the drawing (like maximum aggregate size), and provides a precise pass/fail verdict for each product.

-   **Scenario 3: Regulatory "what-if" analysis**

    A sustainability consultant wants to compare the availability of compliant products between two different regions (e.g., Europe vs. Australia). They can run the same set of EPDs through the engine twice, first selecting the EN 206 schema and then the AS 3600 schema, to instantly see how regulatory differences impact material eligibility.


## Contact 

Roger Vergés - Corresponding author and lead developer - [roger.verges.eiras@upc.edu](mailto:roger.verges.eiras@upc.edu)



## Additional information 
Related publication: The associated academic paper is currently under review. The DOI will be added here upon acceptance.

### Paper contributors:
- Roger Vergés <sup>1, 2</sup> (<a href="mailto:roger.verges.eiras@upc.edu">roger.verges.eiras@upc.edu</a>) <a href="https://orcid.org/0009-0001-5887-4785" aria-label="ORCID"><img src="https://orcid.org/sites/default/files/images/orcid_16x16.png" alt="ORCID iD" width="16" height="16" style="vertical-align: text-bottom; margin-left: 4px;"></a>
- Kàtia Gaspar <sup>1</sup> (<a href="mailto:katia.gaspar@upc.edu">katia.gaspar@upc.edu</a>) <a href="https://orcid.org/0000-0003-3842-1401" aria-label="ORCID"><img src="https://orcid.org/sites/default/files/images/orcid_16x16.png" alt="ORCID iD" width="16" height="16" style="vertical-align: text-bottom; margin-left: 4px;"></a>
- Núria Forcada <sup>1</sup> (<a href="mailto:nuria.forcada@upc.edu">nuria.forcada@upc.edu</a>) <a href="https://orcid.org/0000-0003-2109-4205" aria-label="ORCID"><img src="https://orcid.org/sites/default/files/images/orcid_16x16.png" alt="ORCID iD" width="16" height="16" style="vertical-align: text-bottom; margin-left: 4px;"></a>
- M. Reza Hosseini <sup>2</sup> (<a href="mailto:mreza.hosseini@unimelb.edu.au">mreza.hosseini@unimelb.edu.au</a>) <a href="https://orcid.org/0000-0001-8675-736X" aria-label="ORCID"><img src="https://orcid.org/sites/default/files/images/orcid_16x16.png" alt="ORCID iD" width="16" height="16" style="vertical-align: text-bottom; margin-left: 4px;"></a>



<sup>1</sup> Group of Construction Research and Innovation (GRIC), Universitat Politècnica de Catalunya — BarcelonaTech (UPC), Terrassa, Catalonia

<sup>2</sup> Faculty of Architecture, Building and Planning, The University of Melbourne, Parkville, Australia
