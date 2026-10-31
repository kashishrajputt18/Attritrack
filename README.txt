ATTRITRACK — HR ANALYTICS & EMPLOYEE FEEDBACK SYSTEM
BCA Final-Year Project (student demo)

QUICK START (Windows)
1. Extract this ZIP.
2. Open the extracted AttriTrack_Professional folder.
3. Click the folder address bar, type cmd, and press Enter.
4. Run these commands one by one:
   py -m venv venv
   venv\Scripts\activate
   py -m pip install -r requirements.txt
   py app.py
5. Open Chrome and visit: http://127.0.0.1:5000
Keep Command Prompt open while using the website. Press Ctrl+C there to stop it.

DEMO LOGINS
HR/Admin: ID admin | Password Admin@123
Employee: ID EMP001 to EMP050 | Password Emp@123

FEATURES
- HR/Admin dashboard with workforce KPIs and department distribution
- Employee directory and employee account creation/deletion
- Employee feedback form and feedback history
- HR feedback review and CSV export
- 50 fictional sample employee records created only when the database has no employees
- Responsive blue-and-white professional interface
- Transparent rule-based demo risk indicator

IMPORTANT PROJECT NOTE
The risk indicator is a rule-based demonstration score, not a trained or validated machine-learning model. Sample employees are fictional. Do not use this demo for real employment decisions.

DATABASE
The application uses SQLite and creates attritrack.db automatically in the project folder.
