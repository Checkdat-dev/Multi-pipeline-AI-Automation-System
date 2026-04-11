# MULTI-PIPELINE-AI-AUTOMATION-SYSTEM

## This project is built as a multi-pipeline AI system for processing BIM drawing PDFs.

It consists of three main pipelines:

Pipeline 1 – Extraction & Validation
Extracts metadata from BIM stamp images using AI and validates it against predefined rules.  
Pipeline 2 – Stamp Image Retrieval
Generates and displays stamp images from PDFs for visual inspection.  
Pipeline 3 – Metadata Search
Allows searching and filtering of extracted metadata using labels and their values.
User Workflow

Process for the user:
The system is designed for simple, step-by-step usage through the Streamlit app:

Upload BIM PDFs
Users upload one or multiple drawing PDFs using the interface.
Run Extraction & Validation
The system:
Detects stamp regions
Extracts metadata (28 labels)
Cleans and formats values
Validates against predefined rules
View Stamp Images
Users can visually inspect extracted stamp regions:
28-label stamp
Revision (ANDR) stamp
Download Results
Validated metadata is available as an Excel file for further use.
Search Metadata
Users can:
Select a label (e.g., RITNINGSNUMMER, BLAD, ANDR)
Enter a value
Retrieve matching drawings instantly
Clear Workspace (Optional)
Users can reset the system without affecting master configurations.





















https://multi-pipeline-ai-automation-system-jq2fzpjxxhfuitwgmt3vsf.streamlit.app/
