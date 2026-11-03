FUEL CONSUMPTION ANALYSIS SYSTEM
================================

TECH STACK
- Frontend: HTML, CSS
- Backend: Python + Flask
- Database: MySQL
- Analytics: Pandas, NumPy, Matplotlib

STEP 1 — Install software
1. Install Python 3 from https://www.python.org/downloads/
2. During Python setup, enable "Add Python to PATH" if that option appears.
3. Install MySQL Server and MySQL Workbench.
4. Install VS Code.

STEP 2 — Open the project
1. Extract the ZIP file.
2. Open VS Code.
3. Choose File > Open Folder and select the fuel_consumption_analysis folder.
4. Open Terminal > New Terminal.

STEP 3 — Create a virtual environment
In PowerShell, run:
    py -m venv .venv
If "py" is not recognized, try:
    python -m venv .venv

STEP 4 — Install libraries
Run:
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt

STEP 5 — Create the MySQL database
1. Open MySQL Workbench and connect to your local MySQL Server.
2. Open schema.sql from this project.
3. Execute the complete script using the lightning-bolt button.
4. Confirm that database fuel_analysis and its three tables exist.

STEP 6 — Configure MySQL password
1. Open app.py in VS Code.
2. Find DB_CONFIG.
3. Replace YOUR_MYSQL_PASSWORD with the password you set for the MySQL root user.
4. Save app.py.
Do not put your real password in a public repository.

STEP 7 — Run the application
In the VS Code terminal, run:
    .\.venv\Scripts\python.exe app.py

When the terminal says Flask is running, open this address in your browser:
    http://127.0.0.1:5000

Keep the terminal open while using the website. Press Ctrl+C in the terminal to stop it.

SAMPLE FULL-TANK TEST
For vehicle CAR-001, add:
- 2026-01-01, odometer 10000, litres 30, cost 3000, full tank checked
- 2026-01-10, odometer 10300, litres 25, cost 2500, full tank checked

Expected interval mileage = 300 km / 25 litres = 12 km/L.
Expected interval fuel cost per km = ₹2500 / 300 km = ₹8.33/km.
The first full-tank record is only a baseline and has no mileage result.

If partial fill records occur between the two full-tank records, their litres and costs are included in the interval total.

TROUBLESHOOTING
- "pip is not recognized": use the .venv Python command shown above.
- "Access denied for user root": check the DB_CONFIG username and password.
- "Can't connect to MySQL server": start MySQL Server from Windows Services or MySQL Installer.
- "Unknown database fuel_analysis": run schema.sql in MySQL Workbench.
- Port 5000 already in use: change the last line of app.py to app.run(debug=True, port=5001) and open http://127.0.0.1:5001.
- Charts may need a page refresh after entering new records.

MILEAGE LIMITATION
A first full-tank record cannot calculate mileage because there is no previous full-tank odometer checkpoint. Exact full-tank interval mileage is calculated at a later full-tank checkpoint. Partial fills by themselves do not establish exact mileage.


CHART DISPLAY FIX:
- Charts are saved using an absolute path based on app.py, so they work even if
  Flask is launched from a different current directory.
- After replacing your old project files, restart Flask and refresh the browser.
