import os
import google.generativeai as genai
import PyPDF2

# ------------------------------
# 1. Configure Gemini API Key
# ------------------------------
# Replace with your Gemini API key
os.environ["GOOGLE_API_KEY"] = "AIzaSyCuylDW1ku-fjQzJRICwgcA6tytt4G_WZY"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# ------------------------------
# 2. Extract text from PDF invoice
# ------------------------------
def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

# ------------------------------
# 3. Send to Gemini for fraud analysis
# ------------------------------
def analyze_invoice(file_path):
    invoice_text = extract_text_from_pdf(file_path)

    if not invoice_text.strip():
        return "No text found in PDF. Please check the file."

    model = genai.GenerativeModel("gemini-1.5-flash")  # Use correct model name
    prompt = f"""
    Analyze the following invoice text for fraud risk.
    Give a fraud risk score (0-10) and reasons if it's suspicious.

    Invoice text:
    {invoice_text}
    """

    response = model.generate_content(prompt)
    return response.text

# ------------------------------
# 4. Run the script
# ------------------------------
if __name__ == "__main__":
    pdf_path = "invoice.pdf"  # <-- Replace with your PDF filename
    result = analyze_invoice(pdf_path)
    print("\nInvoice Analysis Result:\n")
    print(result)
