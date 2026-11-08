import os
import json
import threading
from pathlib import Path
from flask import Flask, jsonify, request, session, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
import subprocess
import sys
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
import hashlib
import random
from datetime import date


BASE_DIR = Path(__file__).resolve().parent
ROUTES_FILE = BASE_DIR / "all_buses.json"
COLLECTOR_FILE = BASE_DIR / "busnroute.py"
SOURCE_ROUTES_FILE = BASE_DIR / "mumbai_routes.json"
COLLECTION_LOG = BASE_DIR / "bus_collection.log"

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") == "production"

db = SQLAlchemy(app)
try:
    from .review_routes import register_review_routes
except ImportError:
    from review_routes import register_review_routes
register_review_routes(app, db, BASE_DIR)
password_hasher = PasswordHasher()
collection_lock = threading.Lock()
collection_process = None


class User(db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.BigInteger, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())


@app.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    full_name = data.get("full_name", "").strip()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not all([full_name, username, email, password]):
        return jsonify({"error": "All fields are required"}), 400
    if len(password) < 12:
        return jsonify({"error": "Password must contain at least 12 characters"}), 400
    if len(full_name) > 100 or len(username) > 50 or len(email) > 255:
        return jsonify({"error": "One or more fields are too long"}), 400

    user = User(full_name=full_name, username=username, email=email,
                password_hash=password_hasher.hash(password))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username or email already exists"}), 409
    return jsonify({"message": "Registration successful", "user_id": user.user_id}), 201


@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
    if user is None:
        return jsonify({"error": "Invalid credentials"}), 401
    try:
        password_hasher.verify(user.password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return jsonify({"error": "Invalid credentials"}), 401
    session.clear()
    session["user_id"] = user.user_id
    return jsonify({"message": "Login successful"}), 200


@app.get("/profile")
def profile():
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Not authenticated"}), 401
    user = db.session.get(User, user_id)
    if user is None:
        session.clear()
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user_id": user.user_id, "full_name": user.full_name,
                    "username": user.username, "email": user.email,
                    "created_at": user.created_at.isoformat() if user.created_at else None})


@app.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})


@app.route("/register-page", methods=["GET"])
def register_page():
    if "user_id" in session:
        return redirect("/profile-page")
    return render_template("register.html")


@app.route("/login-page", methods=["GET"])
def login_page():
    if "user_id" in session:
        return redirect("/profile-page")
    return render_template("login.html")

@app.route("/review-page", methods=["GET"])
def review_page():
    if "user_id" not in session:
        return redirect("/login-page")
    return render_template("review.html")

@app.route("/profile-page", methods=["GET"])
def profile_page():
    if "user_id" not in session:
        return redirect("/login-page")
    return render_template("profile.html")


@app.route("/", methods=["GET"])
def index():
    if "user_id" in session:
        return redirect("/profile-page")
    return redirect("/login-page")


@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect("/login-page")
    return render_template("home.html")


@app.post("/api/generate-routes")
def generate_routes():
    global collection_process
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    with collection_lock: 
        if not SOURCE_ROUTES_FILE.is_file():
            return jsonify({"error": "mumbai_routes.json not found in frontend/"}), 404
        if not COLLECTOR_FILE.is_file():
            return jsonify({"error": "busnroute.py not found in frontend/"}), 404

        try:
            
            ROUTES_FILE.unlink(missing_ok=True)
            (BASE_DIR / "all_bus_observations.json").unlink(missing_ok=True)
            with COLLECTION_LOG.open("w", encoding="utf-8") as log:
                collection_process = subprocess.Popen([sys.executable, "-u", str(COLLECTOR_FILE)],cwd=BASE_DIR,stdout=log,stderr=subprocess.STDOUT,)
        except OSError:
            app.logger.exception("Unable to start bus collector")
            return jsonify({"error": "Unable to start bus collector"}), 500
    return jsonify({"state": "running"}), 202


@app.get("/api/generate-routes/status")
def generate_routes_status():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401
    with collection_lock:
        process = collection_process
        if process is None:
            return jsonify({"state": "idle"})
        return_code = process.poll()
    if return_code is None:
        return jsonify({"state": "running"})
    if return_code != 0:
        return jsonify({"state": "failed", "error": "Collection failed; check frontend/bus_collection.log"})
    if not ROUTES_FILE.is_file():
        return jsonify({"state": "failed", "error": "Collection finished without producing all_buses.json"})
    return jsonify({"state": "completed"})



def allocate_display_staff(buses, service_date):
    if not buses:
        return {}
    # Serialize concurrent allocation requests.
    db.session.execute(text("SELECT pg_advisory_xact_lock(740699)"))    
    for bus in buses:
        db.session.execute(text("""INSERT INTO buses (vehicle_number) VALUES (:vehicle_number) ON CONFLICT (vehicle_number) DO NOTHING"""),
            {"vehicle_number": bus["vehicle_number"]})
    db.session.flush()
    # Already saved assignments for this date.
    saved_rows = db.session.execute(text("""SELECT vehicle_number, driver_id, conductor_id, driver_is_fallback, conductor_is_fallback FROM display_staff_assignments WHERE service_date = :service_date"""),
        {"service_date": service_date}).mappings().all()
    saved = {row["vehicle_number"]: dict(row) for row in saved_rows}
    used_drivers = {row["driver_id"] for row in saved_rows}
    used_conductors = {row["conductor_id"] for row in saved_rows}
    current_rows = db.session.execute(text(""" SELECT vehicle_number, driver_id, conductor_id FROM service_assignments WHERE service_date = :service_date ORDER BY vehicle_number"""),{"service_date": service_date}).mappings().all()
    reserved_drivers = {row["driver_id"] for row in current_rows if row["driver_id"] is not None}
    reserved_conductors = { row["conductor_id"] for row in current_rows if row["conductor_id"] is not None}
    drivers = [ dict(row) for row in db.session.execute(text("""SELECT driver_id, driver_name FROM drivers WHERE driver_id NOT LIKE 'SIM_DRIVER_%' ORDER BY driver_id""")).mappings().all()]
    conductors = [dict(row) for row in db.session.execute(text("""SELECT conductor_id, conductor_name FROM conductors WHERE conductor_id NOT LIKE 'SIM_CONDUCTOR_%' ORDER BY conductor_id""")).mappings().all()]
    driver_ids = {d["driver_id"] for d in drivers}
    conductor_ids = {c["conductor_id"] for c in conductors}
    # Recorded assignments, ordered by date and route match.
    recorded_rows = db.session.execute(text("""SELECT sa.vehicle_number, sa.driver_id, sa.conductor_id, sa.service_date, rt.route_name FROM service_assignments sa JOIN routes rt ON rt.route_id = sa.route_id WHERE sa.service_date <= :service_date ORDER BY sa.vehicle_number, sa.service_date DESC, sa.assignment_id DESC"""),{"service_date": service_date}).mappings().all()
    recorded = {}
    for row in recorded_rows:
        recorded.setdefault(row["vehicle_number"], []).append(dict(row))
    new_buses = sorted([bus for bus in buses if bus["vehicle_number"] not in saved],key=lambda b: b["vehicle_number"])
    pending = {}
    for bus in new_buses:
        number = bus["vehicle_number"]
        route_name = bus.get("route_name")
        candidates = recorded.get(number, [])
        candidates = sorted(candidates,key=lambda r: (r["service_date"] == service_date,r["route_name"] == route_name),reverse=True)
        driver_id = None
        conductor_id = None
        for candidate in candidates:
            candidate_driver = candidate["driver_id"]
            candidate_conductor = candidate["conductor_id"]
            driver_reserved_elsewhere = (candidate["service_date"] != service_date and candidate_driver in reserved_drivers)
            conductor_reserved_elsewhere = (candidate["service_date"] != service_date and candidate_conductor in reserved_conductors)
            if (driver_id is None and candidate_driver in driver_ids and candidate_driver not in used_drivers and not driver_reserved_elsewhere):
                driver_id = candidate_driver
                used_drivers.add(driver_id)
            if (conductor_id is None and candidate_conductor in conductor_ids and candidate_conductor not in used_conductors and not conductor_reserved_elsewhere):
                conductor_id = candidate_conductor
                used_conductors.add(conductor_id)
            if driver_id and conductor_id:
                break
        pending[number] = {
            "driver_id": driver_id,
            "conductor_id": conductor_id,
            "driver_is_fallback": driver_id is None,
            "conductor_is_fallback": conductor_id is None
        }
    available_drivers = [ d["driver_id"] for d in drivers if d["driver_id"] not in used_drivers and d["driver_id"] not in reserved_drivers]
    available_conductors = [ c["conductor_id"] for c in conductors if c["conductor_id"] not in used_conductors and c["conductor_id"] not in reserved_conductors]
    random.shuffle(available_drivers)
    random.shuffle(available_conductors)
    for number, assignment in pending.items():
        if assignment["driver_id"] is None:
            if available_drivers:
                assignment["driver_id"] = available_drivers.pop()
            else:                
                token = hashlib.sha256(f"{service_date}:{number}".encode()).hexdigest()[:24] simulated_id = f"SIM_DRIVER_{token}"
                db.session.execute(text("""INSERT INTO drivers (driver_id, driver_name) VALUES (:driver_id, :driver_name) ON CONFLICT (driver_id) DO NOTHING"""),{
                        "driver_id": simulated_id,
                        "driver_name": f"Simulated Driver ({number})"
                    }
                )
                assignment["driver_id"] = simulated_id
        if assignment["conductor_id"] is None:
            if available_conductors:
                assignment["conductor_id"] = available_conductors.pop()
            else:
                token = hashlib.sha256(f"{service_date}:{number}".encode()).hexdigest()[:24]
                simulated_id = f"SIM_CONDUCTOR_{token}"
                db.session.execute(text("""INSERT INTO conductors (conductor_id, conductor_name) VALUES (:conductor_id, :conductor_name) ON CONFLICT (conductor_id) DO NOTHING"""),
                    {
                        "conductor_id": simulated_id,
                        "conductor_name": f"Simulated Conductor ({number})"
                    }
                )
                assignment["conductor_id"] = simulated_id
                db.session.execute(text("""INSERT INTO display_staff_assignments ( service_date, vehicle_number, driver_id, conductor_id, driver_is_fallback, conductor_is_fallback) VALUES (:service_date, :vehicle_number, :driver_id, :conductor_id, :driver_is_fallback, :conductor_is_fallback) ON CONFLICT (service_date, vehicle_number) DO NOTHING"""), {
                "service_date": service_date,
                "vehicle_number": number,
                **assignment
            }
        )
    db.session.commit()
    result_rows = db.session.execute(text("""SELECT vehicle_number, driver_id, conductor_id, driver_is_fallback, conductor_is_fallback FROM display_staff_assignments WHERE service_date = :service_date"""),{"service_date": service_date}).mappings().all()
    return {row["vehicle_number"]: dict(row) for row in result_rows}

@app.route("/api/routes", methods=["GET"])
def get_routes():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401
    try:       
        with ROUTES_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)        
        rating_rows = db.session.execute(text("""SELECT vehicle_number, average_rating, rated_review_count
            FROM bus_average_ratings""")).mappings().all()
        ratings = {
            str(row["vehicle_number"]).strip().upper(): {
                "average_rating": (
                    float(row["average_rating"])
                    if row["average_rating"] is not None
                    else None
                ),
                "rated_review_count": row["rated_review_count"]
            }
            for row in rating_rows        }
        buses = []
        for vehicle_number, vehicle_data in data.items():
            observations = vehicle_data.get("observations", [])
            if not observations:
                continue
            latest = max(observations,key=lambda obs: obs.get("timestamp") or 0)
            number = str(vehicle_data.get("vehicle_number", vehicle_number)).strip().upper()
            rating_info = ratings.get(number, {"average_rating": None,"rated_review_count": 0})
            buses.append({
                "route_name": latest.get("route_name"),
                "first_stop": latest.get("first_stop"),
                "last_stop": latest.get("last_stop"),
                "vehicle_number": number,
                "average_rating": rating_info["average_rating"],
                "rated_review_count": rating_info["rated_review_count"]
            })
        assignments = allocate_display_staff(buses, date.today())
        driver_rows = db.session.execute(text("""SELECT driver_id, driver_name, average_rating, rated_review_count FROM driver_average_ratings""")).mappings().all()
        driver_ratings = {row["driver_id"]: dict(row) for row in driver_rows}
        conductor_rows = db.session.execute(text("""SELECT conductor_id, conductor_name, average_rating, rated_review_count FROM conductor_average_ratings""")).mappings().all()
        conductor_ratings = {row["conductor_id"]: dict(row) for row in conductor_rows}
        for bus in buses:
            assignment = assignments.get(bus["vehicle_number"], {})
            driver = driver_ratings.get(assignment.get("driver_id"), {})
            conductor = conductor_ratings.get(assignment.get("conductor_id"), {})
            bus["driver"] = {"driver_id": assignment.get("driver_id"),"driver_name": driver.get("driver_name"),"average_rating": (float(driver["average_rating"]) if driver.get("average_rating") is not None else None),
            "rated_review_count": driver.get("rated_review_count", 0),"is_fallback": assignment.get("driver_is_fallback", False)}
            bus["conductor"] = {"conductor_id": assignment.get("conductor_id"),"conductor_name": conductor.get("conductor_name"),"average_rating": (float(conductor["average_rating"]) if conductor.get("average_rating") is not None else None
            ),"rated_review_count": conductor.get("rated_review_count", 0),"is_fallback": assignment.get("conductor_is_fallback", False)}
        return jsonify(buses)    
    except (OSError, ValueError, TypeError, AttributeError):
         app.logger.exception("Unable to load routes")
         return jsonify({"error": "Unable to load routes"}), 500

    

if __name__ == "__main__":    
    app.run(debug=True, use_reloader=False)
