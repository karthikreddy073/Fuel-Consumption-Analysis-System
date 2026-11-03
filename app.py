from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from decimal import Decimal, InvalidOperation
from datetime import date
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "development-secret")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "fuel_analysis"),
    "port": int(os.environ.get("DB_PORT", "3306"))
}



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(BASE_DIR, "static", "charts")
os.makedirs(CHART_DIR, exist_ok=True)


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def fetch_all(query, params=()):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def write_query(query, params=()):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()


def log_invalid(vehicle_id, fill_date, odometer, litres, cost, reason):
    try:
        write_query(
            """INSERT INTO invalid_records
               (vehicle_id, attempted_date, attempted_odometer,
                attempted_litres, attempted_cost, reason)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (vehicle_id or None, fill_date or None, odometer, litres, cost, reason)
        )
    except Error:
        # Keep the main validation message visible even if the log table is unavailable.
        pass


def number(value, field_name):
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid number.")
    if not result.is_finite():
        raise ValueError(f"{field_name} must be a valid number.")
    return result


def build_reports():
    vehicles = fetch_all("SELECT * FROM vehicles ORDER BY vehicle_code")
    records = fetch_all("""
        SELECT fr.*, v.vehicle_code, v.vehicle_type, v.fuel_type
        FROM fuel_records fr
        JOIN vehicles v ON v.vehicle_id = fr.vehicle_id
        ORDER BY fr.vehicle_id, fr.fill_date, fr.record_id
    """)

    # Mileage is calculated only between full-tank checkpoints.
    # Litres and cost include all fills after the previous full tank through
    # the current full tank. A partial-fill-only interval is not labelled exact.
    by_vehicle = {}
    for rec in records:
        by_vehicle.setdefault(rec["vehicle_id"], []).append(rec)

    mileage_rows = []
    for vehicle_id, rows in by_vehicle.items():
        last_full = None
        litres_since_full = 0.0
        cost_since_full = 0.0
        previous_odometer = None

        for rec in rows:
            odo = float(rec["odometer_km"])
            litres = float(rec["litres"])
            cost = float(rec["total_cost"])

            # Database validation should prevent this, but keep the report safe.
            if previous_odometer is not None and odo < previous_odometer:
                mileage_rows.append({
                    "vehicle_code": rec["vehicle_code"],
                    "fill_date": rec["fill_date"],
                    "mileage": None,
                    "cost_per_km": None,
                    "status": "Invalid odometer reading"
                })
                previous_odometer = odo
                continue

            litres_since_full += litres
            cost_since_full += cost

            if rec["full_tank_flag"]:
                if last_full is None:
                    status = "Baseline full tank — mileage unavailable"
                    mileage = None
                    cost_per_km = None
                else:
                    distance = odo - float(last_full["odometer_km"])
                    if distance <= 0 or litres_since_full <= 0:
                        status = "Invalid interval — mileage unavailable"
                        mileage = None
                        cost_per_km = None
                    else:
                        mileage = distance / litres_since_full
                        cost_per_km = cost_since_full / distance
                        status = "Full-tank interval"
                mileage_rows.append({
                    "vehicle_code": rec["vehicle_code"],
                    "fill_date": rec["fill_date"],
                    "mileage": mileage,
                    "cost_per_km": cost_per_km,
                    "status": status
                })
                last_full = rec
                litres_since_full = 0.0
                cost_since_full = 0.0

            previous_odometer = odo

    valid_mileage = [r for r in mileage_rows if r["mileage"] is not None]
    total_cost = sum(float(r["total_cost"]) for r in records)
    total_litres = sum(float(r["litres"]) for r in records)

    vehicle_summary = []
    for vehicle in vehicles:
        own = [r for r in valid_mileage if r["vehicle_code"] == vehicle["vehicle_code"]]
        avg = float(np.mean([r["mileage"] for r in own])) if own else None
        vehicle_summary.append({
            **vehicle,
            "average_mileage": avg,
            "interval_count": len(own)
        })

    monthly_rows = []
    if records:
        df = pd.DataFrame(records)
        df["fill_date"] = pd.to_datetime(df["fill_date"])
        df["month"] = df["fill_date"].dt.to_period("M").astype(str)
        monthly = df.groupby("month", as_index=False).agg(
            total_litres=("litres", "sum"),
            total_cost=("total_cost", "sum"),
            fill_count=("record_id", "count")
        )
        monthly_rows = monthly.to_dict("records")

    invalid_rows = fetch_all("""
        SELECT i.*, v.vehicle_code
        FROM invalid_records i
        LEFT JOIN vehicles v ON v.vehicle_id = i.vehicle_id
        ORDER BY i.invalid_id DESC
        LIMIT 100
    """)

    # Monthly fuel expense chart
    month_labels = [r["month"] for r in monthly_rows]
    costs = [float(r["total_cost"]) for r in monthly_rows]
    plt.figure(figsize=(8, 3.5))
    if month_labels:
        plt.plot(month_labels, costs, marker="o", linewidth=2, markersize=6)
        plt.xticks(rotation=35, ha="right")
        plt.ylabel("Fuel cost (₹)")
        plt.xlabel("Month")
        plt.title("Monthly Fuel Expense")
        plt.grid(axis="y", linestyle="--", alpha=0.35)
        plt.tight_layout()
    else:
        plt.text(0.5, 0.5, "Add fuel records to view monthly expenses",
                 ha="center", va="center", fontsize=11)
        plt.axis("off")
    plt.savefig(os.path.join(CHART_DIR, "monthly_cost.png"), dpi=120)
    plt.close()

    # Vehicle mileage chart
    labels = [r["vehicle_code"] for r in vehicle_summary if r["average_mileage"] is not None]
    values = [r["average_mileage"] for r in vehicle_summary if r["average_mileage"] is not None]
    plt.figure(figsize=(8, 3.5))
    if labels:
        plt.bar(labels, values)
        plt.ylabel("km per litre")
        plt.title("Average Full-Tank Mileage by Vehicle")
        plt.xticks(rotation=25, ha="right")
        plt.grid(axis="y", linestyle="--", alpha=0.35)
        plt.tight_layout()
    else:
        plt.text(0.5, 0.5, "Two full-tank checkpoints are needed for mileage",
                 ha="center", va="center", fontsize=11)
        plt.axis("off")
    plt.savefig(os.path.join(CHART_DIR, "vehicle_mileage.png"), dpi=120)
    plt.close()

    return {
        "vehicles": vehicles,
        "records": list(reversed(records[-100:])),
        "vehicle_summary": vehicle_summary,
        "mileage_rows": list(reversed(mileage_rows[-100:])),
        "monthly_rows": list(reversed(monthly_rows)),
        "invalid_rows": invalid_rows,
        "total_cost": total_cost,
        "total_litres": total_litres,
        "record_count": len(records)
    }


@app.route("/")
def dashboard():
    try:
        data = build_reports()
        return render_template("index.html", data=data, today=date.today().isoformat())
    except Error as exc:
        return (
            "<h2>Could not connect to MySQL</h2>"
            "<p>Check that MySQL Server is running, the database schema was executed, "
            "and DB_CONFIG in app.py has the correct password.</p>"
            f"<pre>{str(exc)}</pre>",
            500
        )


@app.route("/vehicles", methods=["POST"])
def add_vehicle():
    code = request.form.get("vehicle_code", "").strip().upper()
    vehicle_type = request.form.get("vehicle_type", "").strip()
    fuel_type = request.form.get("fuel_type", "").strip()
    if not code or not vehicle_type or not fuel_type:
        flash("Enter the vehicle code, type, and fuel type.", "error")
        return redirect(url_for("dashboard"))
    try:
        write_query(
            "INSERT INTO vehicles (vehicle_code, vehicle_type, fuel_type) VALUES (%s, %s, %s)",
            (code, vehicle_type, fuel_type)
        )
        flash("Vehicle added successfully.", "success")
    except Error as exc:
        flash("Vehicle could not be added. The code may already exist. " + str(exc), "error")
    return redirect(url_for("dashboard"))


@app.route("/fuel-records", methods=["POST"])
def add_fuel_record():
    vehicle_id = request.form.get("vehicle_id", "").strip()
    fill_date = request.form.get("fill_date", "").strip()
    odometer_raw = request.form.get("odometer_km", "").strip()
    litres_raw = request.form.get("litres", "").strip()
    cost_raw = request.form.get("total_cost", "").strip()
    full_tank = request.form.get("full_tank_flag") == "on"

    odometer = litres = cost = None
    try:
        if not vehicle_id:
            raise ValueError("Select a vehicle.")
        if not fill_date:
            raise ValueError("Select the fuel date.")
        odometer = number(odometer_raw, "Odometer reading")
        litres = number(litres_raw, "Litres")
        cost = number(cost_raw, "Total cost")
        if odometer < 0:
            raise ValueError("Odometer reading cannot be negative.")
        if litres <= 0:
            raise ValueError("Litres must be greater than zero.")
        if cost < 0:
            raise ValueError("Total cost cannot be negative.")

        latest = fetch_all("""
            SELECT fill_date, odometer_km FROM fuel_records
            WHERE vehicle_id = %s
            ORDER BY fill_date DESC, record_id DESC LIMIT 1
        """, (int(vehicle_id),))
        if latest:
            latest_date = latest[0]["fill_date"].isoformat()
            latest_odo = Decimal(str(latest[0]["odometer_km"]))
            if fill_date < latest_date:
                raise ValueError("Fuel records must be entered in chronological date order.")
            if odometer < latest_odo:
                raise ValueError(
                    f"Odometer cannot be lower than the previous reading ({latest_odo} km)."
                )

        write_query("""
            INSERT INTO fuel_records
                (vehicle_id, fill_date, odometer_km, litres, total_cost, full_tank_flag)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (int(vehicle_id), fill_date, str(odometer), str(litres), str(cost), full_tank))
        flash("Fuel record added successfully.", "success")
    except (ValueError, Error) as exc:
        log_invalid(vehicle_id, fill_date, str(odometer) if odometer is not None else odometer_raw,
                    str(litres) if litres is not None else litres_raw,
                    str(cost) if cost is not None else cost_raw, str(exc))
        flash(str(exc), "error")

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
