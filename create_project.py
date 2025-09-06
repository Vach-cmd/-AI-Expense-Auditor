import os

# ----------------- Paths -----------------
base_dir = os.getcwd()
backend_dir = os.path.join(base_dir, "backend")
frontend_dir = os.path.join(base_dir, "frontend")
frontend_src = os.path.join(frontend_dir, "src")
frontend_components = os.path.join(frontend_src, "components")

# ----------------- Create folders -----------------
os.makedirs(backend_dir, exist_ok=True)
os.makedirs(frontend_components, exist_ok=True)

# ----------------- Backend files -----------------
backend_files = {
    "requirements.txt": """fastapi
uvicorn
pdfplumber
python-multipart""",
    
    "main.py": """from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3, os
from datetime import datetime
import pdfplumber

app = FastAPI(title="AI Expense Auditor MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "auditor.db"
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(\"\"\"
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor TEXT,
        amount TEXT,
        date TEXT,
        risk_score TEXT,
        reasons TEXT
    )
    \"\"\")
    conn.commit()
    conn.close()
init_db()

KNOWN_VENDORS = ["Tata Ltd", "Infosys", "Reliance", "Wipro"]

def analyze_invoice(vendor_name, amount):
    reasons = []
    risk_score = "Low Risk"

    if vendor_name not in KNOWN_VENDORS:
        reasons.append("Unknown vendor detected")
        risk_score = "High Risk"

    try:
        amt = float(amount.replace(\",\", \"\").replace(\"$\",\"\")) 
        if amt > 100000:
            reasons.append("Unusually high invoice amount")
            risk_score = "High Risk"
    except:
        pass

    if not reasons:
        reasons.append("No suspicious activity found")

    return risk_score, reasons

def extract_invoice_data(file_path):
    vendor = "Unknown Vendor"
    amount = "0"
    date = datetime.now().strftime("%Y-%m-%d")
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
            for line in text.split("\\n"):
                if "Vendor:" in line:
                    vendor = line.split("Vendor:")[-1].strip()
                if "Amount:" in line:
                    amount = line.split("Amount:")[-1].strip()
                if "Date:" in line:
                    date = line.split("Date:")[-1].strip()
    except Exception as e:
        print("Error reading PDF:", e)
    return vendor, amount, date

@app.get("/")
def home():
    return {"ok": True, "app": "AI Expense Auditor MVP", "docs": "/docs"}

@app.post("/invoices")
async def upload_invoice(file: UploadFile = File(...)):
    try:
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
        vendor, amount, date = extract_invoice_data(file_path)
        risk_score, reasons = analyze_invoice(vendor, amount)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO invoices (vendor, amount, date, risk_score, reasons) VALUES (?, ?, ?, ?, ?)",
            (vendor, amount, date, risk_score, ", ".join(reasons))
        )
        conn.commit()
        conn.close()
        os.remove(file_path)
        return {
            "vendor": vendor,
            "amount": amount,
            "date": date,
            "risk_score": risk_score,
            "reasons": reasons
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/reports")
def get_reports():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT vendor, amount, date, risk_score, reasons FROM invoices")
    rows = cursor.fetchall()
    conn.close()
    reports = [
        {"vendor": r[0], "amount": r[1], "date": r[2], "risk_score": r[3], "reasons": r[4]}
        for r in rows
    ]
    return {"reports": reports}
"""
}

# ----------------- Frontend files -----------------
frontend_files = {
    "package.json": """{
  "name": "frontend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  }
}""",

    "src/index.js": """import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./App.css";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);""",

    "src/App.js": """import React, { useState } from "react";
import InvoiceCard from "./components/InvoiceCard";

export default function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);

  const uploadInvoice = async () => {
    if (!file) return alert("Select a file first");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("http://127.0.0.1:8000/invoices", { method: "POST", body: formData });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      alert("Upload failed");
    }
  };

  return (
    <div className="container">
      <h1>AI Invoice Fraud Detector</h1>
      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={uploadInvoice}>Upload Invoice</button>
      {result && <InvoiceCard result={result} />}
    </div>
  );
}""",

    "src/components/InvoiceCard.js": """import React from "react";

export default function InvoiceCard({ result }) {
  return (
    <div className={`invoice-card ${result.risk_score === "High Risk" ? "high" : "low"}`}>
      <h2>Analysis Result</h2>
      <p><strong>Vendor:</strong> {result.vendor}</p>
      <p><strong>Amount:</strong> {result.amount}</p>
      <p><strong>Date:</strong> {result.date}</p>
      <p><strong>Risk Score:</strong> {result.risk_score}</p>
      <p><strong>Reasons:</strong> {result.reasons.join(", ")}</p>
    </div>
  );
}""",

    "src/App.css": """.container {
  padding: 20px;
  font-family: Arial, sans-serif;
}
button {
  margin-top: 10px;
  padding: 10px 20px;
}
.invoice-card {
  margin-top: 20px;
  padding: 20px;
  border-radius: 8px;
  color: #fff;
}
.invoice-card.low { background-color: green; }
.invoice-card.high { background-color: red; }"""
}

# ----------------- Create backend files -----------------
for filename, content in backend_files.items():
    with open(os.path.join(backend_dir, filename), "w", encoding="utf-8") as f:
        f.write(content)

# ----------------- Create frontend files -----------------
for filename, content in frontend_files.items():
    path = os.path.join(frontend_dir, filename) if "/" not in filename else os.path.join(frontend_dir, *filename.split("/"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("✅ Project structure created successfully!")
