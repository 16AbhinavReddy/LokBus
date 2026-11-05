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


"""@app.get("/api/routes")
def get_routes():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401
    try:
        with ROUTES_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        buses = []
        for vehicle_number, vehicle_data in data.items():
            observations = vehicle_data.get("observations", [])
            if not observations:
                continue
            latest = max(observations, key=lambda obs: obs.get("timestamp") or 0)
            buses.append({
                "route_name": latest.get("route_name"),
                "first_stop": latest.get("first_stop"),
                "last_stop": latest.get("last_stop"),
                "vehicle_number": vehicle_data.get("vehicle_number", vehicle_number),
            })
        return jsonify(buses)
    except (OSError, ValueError, TypeError, AttributeError):
        app.logger.exception("Unable to load routes")
        return jsonify({"error": "Unable to load routes"}), 500
"""
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
        return jsonify(buses)    
    except (OSError, ValueError, TypeError, AttributeError):
         app.logger.exception("Unable to load routes")
         return jsonify({"error": "Unable to load routes"}), 500

    

if __name__ == "__main__":    
    app.run(debug=True, use_reloader=False)
