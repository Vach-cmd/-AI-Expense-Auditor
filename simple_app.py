"""
Simple AI Expense Auditor - Minimal Working Version
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# In-memory storage for demo
invoices = []
users = [
    {
        "id": 1,
        "username": "admin",
        "password": "admin123",
        "role": "admin",
        "email": "admin@example.com"
    }
]

# Simple fraud detection
def detect_fraud(invoice_data):
    """Simple fraud detection logic"""
    fraud_score = 0.0
    flags = []
    
    # Check for duplicate amounts
    amount = invoice_data.get('amount', 0)
    if amount in [100.00, 200.00, 500.00, 1000.00]:  # Round amounts
        fraud_score += 0.3
        flags.append('round_amount')
    
    # Check for high amounts
    if amount > 1000:
        fraud_score += 0.4
        flags.append('high_amount')
    
    # Check vendor name
    vendor = invoice_data.get('vendor_name', '').lower()
    if 'test' in vendor or 'demo' in vendor:
        fraud_score += 0.8
        flags.append('suspicious_vendor')
    
    return {
        'overall_score': min(fraud_score, 1.0),
        'flags': flags,
        'risk_level': 'high' if fraud_score > 0.7 else 'medium' if fraud_score > 0.3 else 'low'
    }

@app.route('/')
def index():
    """Simple HTML interface"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Expense Auditor</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; }
            .form-group { margin: 20px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
            .result { margin-top: 20px; padding: 15px; border-radius: 5px; }
            .low-risk { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
            .medium-risk { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
            .high-risk { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
            .invoices { margin-top: 30px; }
            .invoice { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ AI Expense Auditor</h1>
            <p style="text-align: center; color: #666;">Automated fraud detection for expense invoices</p>
            
            <form id="invoiceForm">
                <div class="form-group">
                    <label>Vendor Name:</label>
                    <input type="text" id="vendorName" required>
                </div>
                
                <div class="form-group">
                    <label>Amount ($):</label>
                    <input type="number" id="amount" step="0.01" required>
                </div>
                
                <div class="form-group">
                    <label>Description:</label>
                    <textarea id="description" rows="3"></textarea>
                </div>
                
                <div class="form-group">
                    <label>Category:</label>
                    <select id="category">
                        <option value="travel">Travel</option>
                        <option value="office">Office Supplies</option>
                        <option value="meals">Meals</option>
                        <option value="software">Software</option>
                        <option value="other">Other</option>
                    </select>
                </div>
                
                <button type="submit">🔍 Analyze Invoice</button>
            </form>
            
            <div id="result"></div>
            
            <div class="invoices">
                <h3>Recent Invoices</h3>
                <div id="invoicesList"></div>
            </div>
        </div>
        
        <script>
            document.getElementById('invoiceForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const invoiceData = {
                    vendor_name: document.getElementById('vendorName').value,
                    amount: parseFloat(document.getElementById('amount').value),
                    description: document.getElementById('description').value,
                    category: document.getElementById('category').value,
                    date: new Date().toISOString().split('T')[0]
                };
                
                try {
                    const response = await fetch('/api/analyze', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(invoiceData)
                    });
                    
                    const result = await response.json();
                    displayResult(result);
                    loadInvoices();
                } catch (error) {
                    alert('Error analyzing invoice: ' + error.message);
                }
            });
            
            function displayResult(result) {
                const resultDiv = document.getElementById('result');
                const riskClass = result.fraud_analysis.risk_level + '-risk';
                
                resultDiv.innerHTML = `
                    <div class="result ${riskClass}">
                        <h3>Fraud Analysis Results</h3>
                        <p><strong>Risk Level:</strong> ${result.fraud_analysis.risk_level.toUpperCase()}</p>
                        <p><strong>Fraud Score:</strong> ${(result.fraud_analysis.overall_score * 100).toFixed(1)}%</p>
                        <p><strong>Flags:</strong> ${result.fraud_analysis.flags.join(', ') || 'None'}</p>
                    </div>
                `;
            }
            
            async function loadInvoices() {
                try {
                    const response = await fetch('/api/invoices');
                    const invoices = await response.json();
                    
                    const invoicesList = document.getElementById('invoicesList');
                    invoicesList.innerHTML = invoices.map(invoice => `
                        <div class="invoice">
                            <strong>${invoice.vendor_name}</strong> - $${invoice.amount}
                            <br><small>${invoice.category} • ${invoice.date}</small>
                            <br><span style="color: ${invoice.fraud_analysis.risk_level === 'high' ? '#dc3545' : invoice.fraud_analysis.risk_level === 'medium' ? '#ffc107' : '#28a745'}">
                                Risk: ${invoice.fraud_analysis.risk_level.toUpperCase()} (${(invoice.fraud_analysis.overall_score * 100).toFixed(1)}%)
                            </span>
                        </div>
                    `).join('');
                } catch (error) {
                    console.error('Error loading invoices:', error);
                }
            }
            
            // Load invoices on page load
            loadInvoices();
        </script>
    </body>
    </html>
    """
    return html

@app.route('/api/analyze', methods=['POST'])
def analyze_invoice():
    """Analyze invoice for fraud"""
    try:
        invoice_data = request.get_json()
        
        # Add ID and timestamp
        invoice_data['id'] = len(invoices) + 1
        invoice_data['created_at'] = datetime.now().isoformat()
        
        # Perform fraud analysis
        fraud_analysis = detect_fraud(invoice_data)
        invoice_data['fraud_analysis'] = fraud_analysis
        
        # Store invoice
        invoices.append(invoice_data)
        
        return jsonify({
            'message': 'Invoice analyzed successfully',
            'invoice': invoice_data,
            'fraud_analysis': fraud_analysis
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices')
def get_invoices():
    """Get all invoices"""
    return jsonify(invoices)

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'invoices_count': len(invoices)
    })

if __name__ == '__main__':
    print("🚀 Starting AI Expense Auditor...")
    print("📊 Access the application at: http://localhost:5000")
    print("🔍 API endpoints available at: http://localhost:5000/api/")
    print("👤 Demo: Upload invoices to see fraud detection in action!")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
