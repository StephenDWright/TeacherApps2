import streamlit as st
import base64
import os
import uuid
import zipfile
import io
from logic import ProcessingLogic

st.set_page_config(page_title="SBA Automation App")

# Load external CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Logo and header
with open("tw_logo.png", "rb") as image_file:
    encoded_logo = base64.b64encode(image_file.read()).decode()
    st.markdown(f"""
    <div class="tw-header">
        <img src='data:image/png;base64,{encoded_logo}' class="tw-logo">
        <h1 class="tw-title">SBA Automation App</h1>
    </div>
    """, unsafe_allow_html=True)

# Instructions card
st.markdown("""
<div class="tw-card">
  <h4>🪜 How to Use This App</h4>
  <ol style='padding-left: 1.2rem;'>
    <li><b>📥 Download Templates:</b> Choose a level and subject to get the blank PDF + CSV.</li>
    <li><b>✍️ Fill Out CSV:</b> Enter student details and filenames using the template headers.</li>
    <li><b>✍️ Fill Out PDF:</b> Enter SIGNATURE and YEAR in the PDF Template.</li>       
    <li><b>📤 Upload Files:</b> Submit your filled CSV and blank PDF to generate customized coversheets.</li>
  </ol>
</div>
""", unsafe_allow_html=True)

st.divider()

# Step 1: Download Templates
st.markdown("""
<div class="tw-card info">
    <h4 class="step-header">📥 <span class="step-number">Step 1:</span> Select Subject and Download Templates</h4>
    <p>This selection determines how the uploaded data will be processed.</p>
</div>
""", unsafe_allow_html=True)

level = st.radio("Select Level", ["CSEC", "CAPE"], horizontal=True)
subject_map = {
    "CSEC": ["English A", "Economics", "History", "Geography", "POB", "Accounts"],
    "CAPE": ["Communication Studies", "Caribbean Studies", "Economics", "History", "Geography"]
}
subject = st.selectbox("Select Subject", subject_map[level])

# Template download section
TEMPLATE_FILES = {
    "CSEC": {
        "English A": ["english_a_template.pdf", "english_a_template.csv"],
        "Economics": ["economics_template.pdf", "economics_template.csv"],
        "History": ["history_template.pdf", "history_template.csv"],
        "Geography": ["geo_template.pdf", "geo_template.csv"],
        "POB": ["pob_template.pdf", "pob_template.csv"],
        "Accounts": ["accounts_template.pdf", "accounts_template.csv"]
    },
    "CAPE": {
        "Communication Studies": ["comm_studies_template.pdf", "comm_studies_template.csv"],
        "Caribbean Studies": ["carib_studies_template.pdf", "carib_studies_template.csv"],
        "Economics": ["econ_cape_template.pdf", "econ_cape_template.csv"],
        "History": ["history_cape_template.pdf", "history_cape_template.csv"],
        "Geography": ["geo_cape_template.pdf", "geo_cape_template.csv"]
    }
}

template_dir = os.path.join("templates")
os.makedirs(template_dir, exist_ok=True)
pdf_file_name, csv_file_name = TEMPLATE_FILES[level][subject]
pdf_path = os.path.join(template_dir, pdf_file_name)
csv_path = os.path.join(template_dir, csv_file_name)

for filepath in [pdf_path, csv_path]:
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            f.write("Template content here" if filepath.endswith(".csv") else "%PDF-1.4")

with open(pdf_path, "rb") as f:
    pdf_data = f.read()
with open(csv_path, "rb") as f:
    csv_data = f.read()

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📄 Download PDF Template", data=pdf_data, file_name=pdf_file_name, mime="application/pdf", key="pdf")
    with col2:
        st.download_button("📊 Download CSV Template", data=csv_data, file_name=csv_file_name, mime="text/csv", key="csv")

    with st.expander("📄 See Required Fields in This PDF Template"):
        try:
            from pdfrw import PdfReader, PdfName

            reader = PdfReader(pdf_path)
            all_fields = set()

            for page in reader.pages:
                annotations = page[PdfName.Annots]
                if annotations:
                    for annot in annotations:
                        if annot.T:
                            field_name = annot.T.to_unicode().strip()
                            all_fields.add(field_name)

            if all_fields:
                st.markdown(", ".join(sorted(all_fields)))
            else:
                st.warning("No form fields found in the PDF template.")
        except Exception as e:
            st.error(f"Could not extract fields from PDF: {e}")

st.divider()

# Step 2: Upload Files
st.markdown("""
<div class="tw-card info">
    <h4 class="step-header">📤 <span class="step-number">Step 2:</span> Upload Filled Templates to Generate Coversheets</h4>
    <p>Ensure your CSV and PDF match the selected subject's format above.</p>
</div>
""", unsafe_allow_html=True)

csv_file = st.file_uploader("Upload SBA Data (CSV File)", type=["csv"], help="Use the CSV template you just downloaded to fill in student information.")
pdf_file = st.file_uploader("Upload PDF Template", type=["pdf"], help="This should be the blank SBA coversheet template you downloaded.")

if csv_file and pdf_file:
    if st.button("🚀 Start Generating Coversheets"):
        st.info("Generating coversheets based on the selected subject. Please wait...")
        progress = st.progress(0, text="📤 Starting generation...")
        with st.spinner("Processing files. This may take a moment..."):
            session_id = str(uuid.uuid4())
            output_folder = os.path.join("output", session_id)
            os.makedirs(output_folder, exist_ok=True)

            csv_path = os.path.join(output_folder, 'uploaded.csv')
            pdf_path = os.path.join(output_folder, 'template.pdf')

            with open(csv_path, 'wb') as f:
                f.write(csv_file.getbuffer())
            with open(pdf_path, 'wb') as f:
                f.write(pdf_file.getbuffer())

            progress.progress(33, text="🔍 Validating files and preparing...")
            logic = ProcessingLogic()
            message, status = logic.process_files(csv_path, pdf_path, output_folder, subject)
            progress.progress(66, text="🛠️ Generating coversheets...")

            if status == 200:
                progress.progress(100, text="✅ Done! Coversheets ready.")
                st.success(message)
                st.divider()
                
                # Step 3: Download Results
                st.markdown("""
                <div class="tw-card success">
                    <h4 class="step-header">📥 <span class="step-number">Step 3:</span> Download Completed Cover Sheets</h4>
                    <p>Press the button below to download all your generated coversheets.</p>
                </div>
                """, unsafe_allow_html=True)

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zipf:
                    for student_folder in os.listdir(output_folder):
                        student_path = os.path.join(output_folder, student_folder)
                        if os.path.isdir(student_path):
                            for file in os.listdir(student_path):
                                if file.endswith(".pdf"):
                                    file_path = os.path.join(student_path, file)
                                    zipf.write(file_path, arcname=os.path.join(student_folder, file))
                zip_buffer.seek(0)

                st.download_button(
                    label="⬇️ Download All as ZIP",
                    data=zip_buffer,
                    file_name="sba_coversheets.zip",
                    mime="application/zip"
                )
            else:
                st.error(message)
                if "Missing columns" in message:
                    st.warning("Please ensure that the correct subject is selected above. The uploaded files must match the format for that subject.")

# Footer
st.markdown("""
<div class="tw-footer">
    <p>Built with ❤️ by <strong>TW Solutions</strong></p>
</div>
""", unsafe_allow_html=True)