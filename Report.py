from jamaibase import JamAI, protocol as p
from docx import Document
from io import BytesIO
import random
import string
import json

class Report:
    def __init__(self):
        # Report generation credentials
        self.api_key = "jamai_sk_09081aedfccde72a8cfa4bc4db0ff23fa5bd47406c885b77"
        self.project_id = "proj_b16da81149163e2d3abc96bd"
        self.table_id = "report"
        
        # Initialize JamAI client
        self.jamai = JamAI(api_key=self.api_key, project_id=self.project_id)

    def generate_random_filename(self, extension=".docx"):
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        return f"final_report_{random_str}{extension}"

    def generate_report(self, test_history):
        try:
            # Convert history to formatted string
            test_history_text = json.dumps(test_history, indent=2)

            # Get analysis from JamAI
            completion = self.jamai.add_table_rows(
                "action",
                p.RowAddRequest(
                    table_id=self.table_id,
                    data=[{"input": test_history_text}],
                    stream=False
                )
            )

            if not completion.rows:
                raise Exception("Failed to get a response from JamAI")

            output_row = completion.rows[0].columns
            # Extract text content from each field
            summary = output_row.get("Summary", {}).text if output_row.get("Summary") else 'N/A'
            performances = output_row.get("Performance", {}).text if output_row.get("Performance") else 'N/A'
            trends = output_row.get("Trends", {}).text if output_row.get("Trends") else 'N/A'
            recommendations = output_row.get("Recommendations", {}).text if output_row.get("Recommendations") else 'N/A'

            # Generate document
            doc = Document()
            doc.add_heading("Executive Report", level=1)

            doc.add_heading("Summary of Test History", level=2)
            doc.add_paragraph(summary)

            doc.add_heading("Emotion Recognition Performance", level=2)
            doc.add_paragraph(performances)

            doc.add_heading("Key Insights and Trends", level=2)
            doc.add_paragraph(trends)

            doc.add_heading("Recommendations for Improvement", level=2)
            doc.add_paragraph(recommendations)

            # Save to buffer
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)

            return buffer

        except Exception as e:
            raise Exception(f"Report generation failed: {str(e)}")
        
