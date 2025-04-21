import os
import pandas as pd
import pdfrw
from pdf2image import convert_from_path
from tqdm import tqdm
import json

class ProcessingLogic:
    def __init__(self, mapping_path="field_mappings.json"):
        with open(mapping_path, "r") as f:
            self.field_mappings = json.load(f)

    def get_field_mapping(self, subject):
        return self.field_mappings.get(subject)

    def process_files(self, csv_file, pdf_file, output_folder, subject):
        field_mapping = self.get_field_mapping(subject)
        if not field_mapping:
            return "Invalid subject selected.", 400

        try:
            df = pd.read_csv(csv_file)
        except Exception as e:
            return f"Failed to load CSV file: {e}", 400

        missing_columns = [column for column in field_mapping.values() if column not in df.columns]
        if missing_columns:
            return f"Missing columns in CSV file: {', '.join(missing_columns)}", 400

        processed_names = set()
        for i, row in tqdm(df.iterrows(), total=df.shape[0], desc="Processing students"):
            try:
                pdf_reader = pdfrw.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    form_fields = page[pdfrw.PdfName.Annots]
                    if form_fields is None:
                        continue
                    for field in form_fields:
                        if field.T is None:
                            continue
                        field_name = field.T[1:-1]
                        if field_name in field_mapping:
                            col_name = field_mapping[field_name]
                            value = row[col_name]
                            field_value = str(int(value)) if isinstance(value, (int, float)) and float(value).is_integer() else str(value)
                            field.update(pdfrw.PdfDict(V=field_value))
                            field.update(pdfrw.PdfDict(AP=None))
                            field.update(pdfrw.PdfDict(Ff=1))

                folder_name = row["Candidate_Name"]
                if folder_name not in processed_names:
                    folder_path = os.path.join(output_folder, folder_name)
                    os.makedirs(folder_path, exist_ok=True)
                    processed_names.add(folder_name)

                if pd.isna(row["Candidate_Name"]):
                    continue

                file_name = f"{row['CS_Name']}.pdf"
                temp_filled_pdf = os.path.join(folder_path, "temp_" + file_name)
                pdfrw.PdfWriter().write(temp_filled_pdf, pdf_reader)

                images = convert_from_path(temp_filled_pdf, dpi=300, fmt="png")
                with open(os.path.join(folder_path, file_name), "wb") as output_file:
                    images[0].save(output_file, save_all=True, append_images=images[1:], format="PDF", quality=100)

                os.remove(temp_filled_pdf)
            except Exception as e:
                continue

        return f"Successfully processed {len(processed_names)} students.", 200
