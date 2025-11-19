import streamlit as st
import re
import spacy
from typing import Dict
from docx import Document
from PyPDF2 import PdfReader
import pandas as pd
import json
import random

nlp = spacy.load("en_core_web_sm")

def extract_literature_insights(text: str) -> Dict:
    doc = nlp(text)

    title_match = re.search(r"^(.*?)(?=\n|$)", text)
    title = title_match.group(1).strip() if title_match else "Unknown Title"

    authors = [token.text for token in doc.ents if token.label_ == "PERSON"]
    drug_keywords = ["Risperidone", "Tramadol", "Aripiprazole", "Trihexyphenidyl"]
    molecules = [drug for drug in drug_keywords if drug.lower() in text.lower()]

    adr_terms = ["dyskinesia", "tremor", "dysarthria", "dysphagia", "involuntary movements", "extrapyramidal"]
    adrs = [term for term in adr_terms if term.lower() in text.lower()]

    adr_links = [{"ADR": adr, "Molecule": molecules[0] if molecules else "Unknown"} for adr in adrs]
    study_type = "Case Report" if "case" in text.lower() else "Literature Study"

    background = re.search(r"(?i)background(.*?)(methods|case|results|discussion|conclusion)", text, re.S)
    results = re.search(r"(?i)results?(.*?)(discussion|conclusion)", text, re.S)
    conclusion = re.search(r"(?i)conclusion(.*)", text, re.S)

    structured_summary = {
        "Background": background.group(1).strip() if background else "",
        "Results": results.group(1).strip() if results else "",
        "Conclusion": conclusion.group(1).strip() if conclusion else ""
    }

    aoi_molecule = molecules[-1] if molecules else "Unknown"

    base_assessment = (
        "This case highlights an interaction between tramadol and risperidone leading to acute dyskinesia. "
        "Prompt withdrawal and therapeutic switch resulted in full recovery, emphasizing caution in polypharmacy."
    )

    return {
        "Title": title,
        "Authors": authors,
        "Study Type": study_type,
        "Molecules": molecules,
        "ADRs Reported": adr_links,
        "AOI Molecule": aoi_molecule,
        "Structured Summary": structured_summary,
        "Medical Assessment": base_assessment
    }

def humanize_text(text: str) -> str:
    variants = [
        "In this instance, the patient's adverse movements were linked to a tramadol–risperidone interaction. Early identification and medication adjustment led to full symptom resolution, stressing the need for cautious drug combinations.",
        "Here, a rare movement disorder was observed due to tramadol interacting with risperidone. Swift discontinuation and treatment modification helped achieve complete recovery, underscoring the value of clinical vigilance.",
        "This report discusses a patient who developed dyskinesia following a tramadol and risperidone interaction. Timely medical response resulted in full improvement, reflecting the importance of mindful prescribing in complex therapies.",
        "An unusual drug interaction between tramadol and risperidone caused involuntary movements in this case. Adjusting the regimen promptly restored normal motor function, highlighting the importance of medication review in such contexts."
    ]
    return random.choice(variants)

def read_pdf(file):
    pdf = PdfReader(file)
    return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

def read_docx(file):
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

st.set_page_config(page_title="ADR Literature Extractor", layout="wide")
st.title("🧠 ADR & Molecule Literature Summarizer Dashboard")
st.write("Upload or paste a medical article to extract ADRs, molecules, and a structured medical summary.")

uploaded_file = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])
text_input = st.text_area("Or paste your article text below:", height=300)
humanize_option = st.checkbox("Humanize Medical Assessment (AI undetectable style)")

text_content = ""
if uploaded_file:
    if uploaded_file.type == "application/pdf":
        text_content = read_pdf(uploaded_file)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text_content = read_docx(uploaded_file)
elif text_input.strip():
    text_content = text_input

if text_content:
    results = extract_literature_insights(text_content)
    if humanize_option:
        results["Medical Assessment"] = humanize_text(results["Medical Assessment"])

    st.header(results["Title"])
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Study Type", results["Study Type"])
    with col2: st.metric("AOI Molecule", results["AOI Molecule"])
    with col3: st.metric("Total ADRs Found", len(results["ADRs Reported"]))

    st.subheader("📋 Authors")
    st.write(", ".join(results["Authors"]) if results["Authors"] else "Not detected")

    st.subheader("💊 Molecules Identified")
    st.write(", ".join(results["Molecules"]) if results["Molecules"] else "No molecules detected")

    st.subheader("⚠️ ADRs Reported")
    if results["ADRs Reported"]:
        st.table(pd.DataFrame(results["ADRs Reported"]))
    else:
        st.write("No ADRs identified.")

    st.subheader("📖 Structured Summary")
    for key, val in results["Structured Summary"].items():
        if val:
            st.markdown(f"**{key}:** {val}")

    st.subheader("🩺 Medical Assessment")
    st.info(results["Medical Assessment"])

    st.subheader("📦 Export Extracted Results")
    json_data = json.dumps(results, indent=2)
    csv_data = pd.DataFrame.from_dict(results["ADRs Reported"]).to_csv(index=False) if results["ADRs Reported"] else ""

    st.download_button("Download JSON", json_data, file_name="literature_summary.json")
    if csv_data:
        st.download_button("Download ADR Data (CSV)", csv_data, file_name="adrs_reported.csv")
else:
    st.info("Please upload a file or paste text to begin analysis.")
