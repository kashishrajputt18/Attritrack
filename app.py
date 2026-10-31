from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, csv, io
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("ATTRITRACK_SECRET", "demo-secret-change-before-deployment")
DB = os.path.join(os.path.dirname(__file__), "attritrack.db")

def connect():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def setup():
    c = connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT UNIQUE, name TEXT NOT NULL,
      email TEXT, department TEXT NOT NULL, role TEXT NOT NULL, password_hash TEXT NOT NULL,
      salary REAL DEFAULT 0, years REAL DEFAULT 1, promotion REAL DEFAULT 1,
      satisfaction INTEGER DEFAULT 3, workload INTEGER DEFAULT 3, overtime INTEGER DEFAULT 0,
      performance INTEGER DEFAULT 3, created_at TEXT);
    CREATE TABLE IF NOT EXISTS feedback(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, experience INTEGER,
      salary_satisfaction INTEGER, work_life_balance INTEGER, workload INTEGER,
      growth_opportunities INTEGER, comments TEXT, created_at TEXT,
      FOREIGN KEY(user_id) REFERENCES users(id));
    """)
    if not c.execute("SELECT id FROM users WHERE employee_id='admin'").fetchone():
        c.execute("INSERT INTO users(employee_id,name,email,department,role,password_hash,created_at) VALUES(?,?,?,?,?,?,?)",
          ("admin","HR Administrator","hr@attritrack.local","Human Resources","admin",generate_password_hash("Admin@123"),datetime.now().isoformat(timespec="minutes")))
    if c.execute("SELECT COUNT(*) n FROM users WHERE role='employee'").fetchone()["n"] == 0:
        # 50 fictional demo employees for a college project. Seed only when the employee table is empty.
        first_names = ["Aarav","Riya","Kabir","Meera","Ishaan","Ananya","Vihaan","Sana","Aditya","Pooja","Rahul","Nisha","Arjun","Kavya","Dev","Simran","Manav","Ira","Kunal","Aditi","Yash","Tanya","Rohan","Neha","Varun","Diya","Sahil","Mahi","Reyansh","Sneha","Aman","Priya","Harsh","Anika","Dhruv","Muskan","Jay","Shreya","Nikhil","Ayesha","Samar","Palak","Abhinav","Ishita","Rajat","Lavanya","Gaurav","Tara","Mohit","Khushi"]
        last_names = ["Sharma","Verma","Singh","Gupta","Rao","Mehta","Khan","Patel","Joshi","Malhotra","Kapoor","Das","Mishra","Saini","Bansal","Chopra","Iyer","Reddy","Shah","Arora"]
        departments = ["IT","Finance","Marketing","Operations","Human Resources"]
        sample = []
        for i in range(50):
            fname = first_names[i]
            lname = last_names[(i * 3) % len(last_names)]
            eid = f"EMP{i+1:03d}"
            name = f"{fname} {lname}"
            dept = departments[i % len(departments)]
            email = f"{fname.lower()}.{lname.lower()}{i+1}@company.com"
            salary = 32000 + ((i * 1739) % 42000)
            years = (i % 10) + 1
            promotion = (i % 6) + 0.5
            satisfaction = (i % 5) + 1
            workload = ((i * 2) % 5) + 1
            overtime = 1 if i % 4 == 0 else 0
            performance = ((i * 3) % 5) + 1
            sample.append((eid,name,email,dept,salary,years,promotion,satisfaction,workload,overtime,performance))
        for e in sample:
            c.execute("""INSERT INTO users(employee_id,name,email,department,role,password_hash,salary,years,promotion,satisfaction,workload,overtime,performance,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (e[0],e[1],e[2],e[3],"employee",generate_password_hash("Emp@123"),*e[4:],datetime.now().isoformat(timespec="minutes")))
    c.commit(); c.close()

def require(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapped(*a,**kw):
            if not session.get("uid"): return redirect(url_for("home"))
            if role and session.get("role") != role:
                flash("You do not have access to that page.","error"); return redirect(url_for("home"))
            return fn(*a,**kw)
        return wrapped
    return deco

def risk(p):
    # Transparent demo indicator only; not a trained or validated ML prediction.
    s=0
    s += 25 if p["satisfaction"]<=2 else (12 if p["satisfaction"]==3 else 0)
    s += 20 if p["promotion"]>=4 else (10 if p["promotion"]>=2 else 0)
    s += 15 if p["workload"]>=4 else 0
    s += 15 if p["overtime"] else 0
    s += 8 if p["years"]<=1 else 0
    s += 7 if p["performance"]<=2 else 0
    return min(s,100)

def level(s): return "High" if s>=55 else ("Moderate" if s>=30 else "Low")

@app.context_processor
def globals_for_templates():
    return {"current_user":session.get("name"),"current_role":session.get("role")}

@app.route("/")
def home():
    if session.get("role")=="admin": return redirect(url_for("dashboard"))
    if session.get("role")=="employee": return redirect(url_for("employee"))
    return render_template("home.html")

@app.route("/login/<role>",methods=["GET","POST"])
def login(role):
    if role not in ("admin","employee"): return redirect(url_for("home"))
    if request.method=="POST":
        c=connect(); u=c.execute("SELECT * FROM users WHERE employee_id=? AND role=?",(request.form.get("username","").strip(),role)).fetchone(); c.close()
        if u and check_password_hash(u["password_hash"],request.form.get("password","")):
            session.clear(); session.update(uid=u["id"],employee_id=u["employee_id"],name=u["name"],role=u["role"])
            return redirect(url_for("dashboard" if role=="admin" else "employee"))
        flash("Incorrect ID or password. Please try again.","error")
    return render_template("login.html",role=role)

@app.route("/logout")
def logout():
    session.clear(); flash("You have signed out.","success"); return redirect(url_for("home"))

@app.route("/employee")
@require("employee")
def employee():
    c=connect(); u=c.execute("SELECT * FROM users WHERE id=?",(session["uid"],)).fetchone()
    fs=c.execute("SELECT * FROM feedback WHERE user_id=? ORDER BY id DESC",(session["uid"],)).fetchall(); c.close()
    return render_template("employee.html",user=u,feedbacks=fs)

@app.route("/feedback",methods=["GET","POST"])
@require("employee")
def feedback():
    if request.method=="POST":
        try:
            vals=[int(request.form[k]) for k in ("experience","salary_satisfaction","work_life_balance","workload","growth_opportunities")]
            if any(v<1 or v>5 for v in vals): raise ValueError
        except (ValueError,KeyError):
            flash("Please rate every item from 1 to 5.","error"); return redirect(url_for("feedback"))
        c=connect(); c.execute("INSERT INTO feedback(user_id,experience,salary_satisfaction,work_life_balance,workload,growth_opportunities,comments,created_at) VALUES(?,?,?,?,?,?,?,?)",
          (session["uid"],*vals,request.form.get("comments","").strip()[:1000],datetime.now().isoformat(timespec="minutes")))
        c.commit(); c.close(); flash("Thank you. Your identified feedback was sent to HR.","success"); return redirect(url_for("employee"))
    return render_template("feedback.html")

@app.route("/admin")
@require("admin")
def dashboard():
    c=connect(); employees=c.execute("SELECT * FROM users WHERE role='employee' ORDER BY name").fetchall()
    feedbacks=c.execute("""SELECT f.*,u.name,u.employee_id,u.department FROM feedback f JOIN users u ON u.id=f.user_id ORDER BY f.id DESC""").fetchall()
    depts=c.execute("SELECT department,COUNT(*) n FROM users WHERE role='employee' GROUP BY department").fetchall(); c.close()
    people=[]
    for row in employees:
        p=dict(row); p["score"]=risk(p); p["level"]=level(p["score"]); people.append(p)
    total=len(people); high=sum(p["level"]=="High" for p in people)
    avg_sat=round(sum(p["satisfaction"] for p in people)/total,1) if total else 0
    avg_exp=round(sum(f["experience"] for f in feedbacks)/len(feedbacks),1) if feedbacks else 0
    return render_template("admin.html",employees=people,feedbacks=feedbacks,depts=depts,total=total,high=high,avg_sat=avg_sat,avg_exp=avg_exp)

@app.route("/admin/employees",methods=["GET","POST"])
@require("admin")
def employees_page():
    if request.method=="POST":
        try:
            eid=request.form["employee_id"].strip().upper(); name=request.form["name"].strip()
            dept=request.form["department"]; pw=request.form["password"]
            vals=[float(request.form.get("salary",0)),float(request.form.get("years",0)),float(request.form.get("promotion",0)),
                  int(request.form.get("satisfaction",3)),int(request.form.get("workload",3)),int(request.form.get("overtime",0)),int(request.form.get("performance",3))]
            if not eid or not name or len(pw)<6 or any(v<1 or v>5 for v in [vals[3],vals[4],vals[6]]): raise ValueError
            c=connect(); c.execute("""INSERT INTO users(employee_id,name,email,department,role,password_hash,salary,years,promotion,satisfaction,workload,overtime,performance,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(eid,name,request.form.get("email",""),dept,"employee",generate_password_hash(pw),*vals,datetime.now().isoformat(timespec="minutes")))
            c.commit(); c.close(); flash("Employee account created.","success")
        except sqlite3.IntegrityError: flash("Employee ID already exists. Use a unique ID.","error")
        except (ValueError,KeyError): flash("Check all fields. Password must have 6+ characters and ratings 1–5.","error")
        return redirect(url_for("employees_page"))
    c=connect(); rows=c.execute("SELECT * FROM users WHERE role='employee' ORDER BY name").fetchall(); c.close()
    return render_template("employees.html",employees=rows)

@app.route("/admin/delete/<int:uid>",methods=["POST"])
@require("admin")
def delete_employee(uid):
    c=connect(); c.execute("DELETE FROM feedback WHERE user_id=?",(uid,)); c.execute("DELETE FROM users WHERE id=? AND role='employee'",(uid,)); c.commit(); c.close()
    flash("Employee and linked feedback deleted.","success"); return redirect(url_for("employees_page"))

@app.route("/admin/feedback/<int:fid>")
@require("admin")
def feedback_detail(fid):
    c=connect(); item=c.execute("SELECT f.*,u.name,u.employee_id,u.department FROM feedback f JOIN users u ON u.id=f.user_id WHERE f.id=?",(fid,)).fetchone(); c.close()
    if not item: return redirect(url_for("dashboard"))
    return render_template("feedback_detail.html",item=item)

@app.route("/admin/export")
@require("admin")
def export():
    c=connect(); rows=c.execute("SELECT employee_id,name,department,email,salary,years,promotion,satisfaction,workload,overtime,performance FROM users WHERE role='employee'").fetchall(); c.close()
    out=io.StringIO(); w=csv.writer(out); w.writerow(["Employee ID","Name","Department","Email","Salary","Years at Company","Years Since Promotion","Satisfaction","Workload","Overtime","Performance"])
    for r in rows: w.writerow(list(r))
    return Response(out.getvalue(),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=attritrack_employee_data.csv"})

setup()
if __name__=="__main__": app.run(debug=True)
