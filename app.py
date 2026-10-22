
from flask import Flask, request, render_template_string
import sqlite3
import pandas as pd
from datetime import date

app = Flask(__name__)

def db():
    con = sqlite3.connect("emi.db")
    con.execute("""CREATE TABLE IF NOT EXISTS emi(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer TEXT, due REAL, paid REAL, due_date TEXT)""")
    return con

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>PaySync IQ</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{font-family:Arial;background:#eef2ff;padding:20px;color:#172554}
h1{color:#2563eb}.cards{display:flex;gap:12px;flex-wrap:wrap}
.card,form{background:white;padding:18px;border-radius:12px;margin:12px 0}
.card{flex:1;min-width:130px}input,button{padding:10px;margin:5px}
button{background:#2563eb;color:white;border:0;cursor:pointer}
table{width:100%;background:white;border-collapse:collapse}
td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}
</style>
</head>
<body>
<h1>PaySync IQ</h1>
<p>Smart EMI Payment Reconciliation & Tracking System</p>

<div class="cards">
<div class="card">Collected<h2>₹{{ collected }}</h2></div>
<div class="card">Pending<h2>₹{{ pending }}</h2></div>
<div class="card">Overdue<h2>₹{{ overdue }}</h2></div>
</div>

<form method="post">
<h3>Add EMI Payment</h3>
<input name="customer" placeholder="Customer Name" required>
<input name="due" type="number" min="0.01" step="0.01" placeholder="EMI Amount" required>
<input name="paid" type="number" min="0" step="0.01" placeholder="Paid Amount" required>
<input name="due_date" type="date" required>
<button>Save Record</button>
</form>

<div class="card"><canvas id="chart"></canvas></div>
<h3>EMI Reconciliation Report</h3>
<table>
<tr><th>Customer</th><th>Due</th><th>Paid</th><th>Pending</th><th>Status</th></tr>
{% for r in rows %}
<tr><td>{{r.customer}}</td><td>₹{{r.due}}</td>
<td>₹{{r.paid}}</td><td>₹{{r.pending}}</td><td>{{r.status}}</td></tr>
{% endfor %}
</table>

<script>
new Chart(document.getElementById('chart'),{
 type:'doughnut',
 data:{labels:['Collected','Pending','Overdue'],
 datasets:[{data:[{{collected}},{{pending-overdue}},{{overdue}}]}]},
 options:{plugins:{legend:{position:'bottom'}}}
});
</script>
</body></html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    con = db()
    if request.method == "POST":
        due, paid = float(request.form["due"]), float(request.form["paid"])
        if due <= 0 or paid < 0 or paid > due:
            con.close()
            return "Invalid amount! Paid amount must be between 0 and EMI amount. <a href='/'>Go back</a>"
        con.execute("INSERT INTO emi(customer,due,paid,due_date) VALUES(?,?,?,?)",
          (request.form["customer"], due, paid, request.form["due_date"]))
        con.commit()

    data = con.execute("SELECT * FROM emi").fetchall()
    con.close()
    df = pd.DataFrame(data, columns=["id","customer","due","paid","due_date"])

    if not df.empty:
        df["pending"] = (df["due"]-df["paid"]).clip(lower=0)
        df["status"] = df.apply(lambda r:
          "Paid" if r.pending == 0 else
          "Overdue" if r.due_date < str(date.today()) else
          "Partial" if r.paid > 0 else "Pending", axis=1)
        rows = df.to_dict("records")
        collected, pending = df.paid.sum(), df.pending.sum()
        overdue = df.loc[df.status=="Overdue","pending"].sum()
    else:
        rows, collected, pending, overdue = [], 0, 0, 0

    return render_template_string(HTML, rows=rows,
       collected=collected, pending=pending, overdue=overdue)

if __name__ == "__main__":
    app.run(debug=True)
