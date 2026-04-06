"""
Invoice Generator — LLM writes professional HTML invoices.
Commands: /invoice create|list|view <id>|export <id>
"""

import os
import json
from datetime import datetime, date


class InvoiceGenerator:
    """Generate professional invoices using LLM and save as HTML."""

    DATA_FILE = "invoices_data.json"
    OUTPUT_DIR = "invoices"

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self._data = self._load()
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def _load(self):
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"invoices": [], "settings": {"currency": "USD", "company_name": "Your Company"}}

    def _save(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def create_invoice(self, details: dict) -> dict:
        """Create a professional invoice."""
        invoice_num = f"INV-{date.today().strftime('%Y%m%d')}-{len(self._data['invoices'])+1:03d}"
        invoice = {
            "id": len(self._data["invoices"]) + 1,
            "number": invoice_num,
            "created_at": datetime.now().isoformat(),
            "due_date": details.get("due_date", "Net 30"),
            "client_name": details.get("client_name", "Client"),
            "client_email": details.get("client_email", ""),
            "client_address": details.get("client_address", ""),
            "items": details.get("items", []),
            "currency": details.get("currency", self._data["settings"].get("currency", "USD")),
            "notes": details.get("notes", ""),
            "company_name": details.get("company_name", self._data["settings"].get("company_name", "Your Company")),
            "company_email": details.get("company_email", ""),
            "status": "draft"
        }

        # Calculate totals
        subtotal = sum(item.get("qty", 1) * item.get("rate", 0) for item in invoice["items"])
        tax_pct = details.get("tax_pct", 0)
        tax = subtotal * tax_pct / 100
        total = subtotal + tax
        invoice["subtotal"] = round(subtotal, 2)
        invoice["tax_pct"] = tax_pct
        invoice["tax"] = round(tax, 2)
        invoice["total"] = round(total, 2)

        # Generate HTML
        html = self._generate_html(invoice)
        filepath = os.path.join(self.OUTPUT_DIR, f"{invoice_num}.html")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)
            invoice["filepath"] = filepath
        except Exception as e:
            invoice["filepath"] = None
            invoice["file_error"] = str(e)

        self._data["invoices"].append(invoice)
        self._save()

        return {
            "success": True,
            "invoice_number": invoice_num,
            "total": invoice["total"],
            "currency": invoice["currency"],
            "filepath": invoice.get("filepath"),
            "message": f"✅ Invoice {invoice_num} created!\n   💰 Total: {invoice['currency']} {invoice['total']}\n   📄 Saved: {invoice.get('filepath','')}"
        }

    def _generate_html(self, inv: dict) -> str:
        """Generate a clean, professional HTML invoice."""
        items_html = ""
        for item in inv["items"]:
            qty = item.get("qty", 1)
            rate = item.get("rate", 0)
            amount = qty * rate
            items_html += f"""
            <tr>
                <td>{item.get('description', '')}</td>
                <td style="text-align:center">{qty}</td>
                <td style="text-align:right">{inv['currency']} {rate:,.2f}</td>
                <td style="text-align:right">{inv['currency']} {amount:,.2f}</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Invoice {inv['number']}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f5f5; color: #333; }}
  .invoice {{ max-width: 800px; margin: 40px auto; background: white; border-radius: 8px;
             box-shadow: 0 2px 20px rgba(0,0,0,0.1); overflow: hidden; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; padding: 40px; }}
  .header h1 {{ font-size: 2rem; font-weight: 300; letter-spacing: 4px; color: #00d4ff; }}
  .header .inv-num {{ font-size: 0.9rem; color: #aaa; margin-top: 5px; }}
  .body {{ padding: 40px; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 40px; }}
  .info-block h3 {{ color: #00d4ff; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px; }}
  .info-block p {{ color: #555; line-height: 1.6; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
  thead th {{ background: #1a1a2e; color: white; padding: 12px 15px; text-align: left; font-weight: 500; }}
  tbody td {{ padding: 12px 15px; border-bottom: 1px solid #eee; }}
  tbody tr:hover {{ background: #f9f9f9; }}
  .totals {{ margin-left: auto; width: 300px; }}
  .totals .row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
  .totals .total-row {{ background: #1a1a2e; color: white; padding: 15px; border-radius: 4px; font-size: 1.1rem; font-weight: 600; }}
  .notes {{ margin-top: 30px; padding: 20px; background: #f9f9f9; border-radius: 4px; border-left: 4px solid #00d4ff; }}
  .footer {{ text-align: center; padding: 20px; color: #999; font-size: 0.85rem; background: #f9f9f9; }}
</style>
</head>
<body>
<div class="invoice">
  <div class="header">
    <h1>INVOICE</h1>
    <div class="inv-num">#{inv['number']} &nbsp;|&nbsp; {inv['created_at'][:10]} &nbsp;|&nbsp; Due: {inv['due_date']}</div>
    <div style="margin-top:10px;font-size:1.2rem">{inv['company_name']}</div>
    <div style="color:#aaa;font-size:0.85rem">{inv['company_email']}</div>
  </div>
  <div class="body">
    <div class="info-grid">
      <div class="info-block">
        <h3>Bill To</h3>
        <p><strong>{inv['client_name']}</strong><br>{inv['client_email']}<br>{inv['client_address']}</p>
      </div>
      <div class="info-block">
        <h3>Invoice Details</h3>
        <p>Invoice #: <strong>{inv['number']}</strong><br>Date: {inv['created_at'][:10]}<br>Due: {inv['due_date']}<br>Status: <span style="color:#00cc66;font-weight:bold">{inv['status'].upper()}</span></p>
      </div>
    </div>
    <table>
      <thead><tr><th style="width:50%">Description</th><th style="width:15%;text-align:center">Qty</th><th style="width:17.5%;text-align:right">Rate</th><th style="width:17.5%;text-align:right">Amount</th></tr></thead>
      <tbody>{items_html}</tbody>
    </table>
    <div class="totals">
      <div class="row"><span>Subtotal</span><span>{inv['currency']} {inv['subtotal']:,.2f}</span></div>
      <div class="row"><span>Tax ({inv['tax_pct']}%)</span><span>{inv['currency']} {inv['tax']:,.2f}</span></div>
      <div class="total-row"><span>TOTAL DUE</span><span>{inv['currency']} {inv['total']:,.2f}</span></div>
    </div>
    {'<div class="notes"><strong>Notes:</strong> ' + inv["notes"] + '</div>' if inv.get("notes") else ''}
  </div>
  <div class="footer">Thank you for your business! &nbsp;|&nbsp; {inv['company_name']}</div>
</div>
</body></html>"""

    def list_invoices(self) -> str:
        """List all invoices."""
        if not self._data["invoices"]:
            return "No invoices yet. Use /invoice create to make one."
        lines = ["🧾 INVOICES:\n"]
        for inv in reversed(self._data["invoices"][-10:]):
            lines.append(f"  [{inv['id']}] {inv['number']} — {inv['client_name']}")
            lines.append(f"       💰 {inv['currency']} {inv['total']} | {inv['created_at'][:10]} | {inv['status'].upper()}")
        return "\n".join(lines)

    def view_invoice(self, inv_id: int) -> str:
        """View a specific invoice."""
        for inv in self._data["invoices"]:
            if inv["id"] == inv_id:
                import sys
                if inv.get("filepath") and os.path.exists(inv["filepath"]):
                    if sys.platform == "win32":
                        os.startfile(os.path.abspath(inv["filepath"]))
                    return f"✅ Opened invoice {inv['number']} in browser."
                return f"Invoice {inv['number']}\nTotal: {inv['currency']} {inv['total']}\nFile: {inv.get('filepath','N/A')}"
        return f"Invoice #{inv_id} not found."
