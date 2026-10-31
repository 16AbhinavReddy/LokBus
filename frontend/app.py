import os
import json
import subprocess
import sys
from pathlib import Path
from flask import Flask, jsonify, request, session, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

BASE_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = BASE_DIR / "queryagnosticrouteinfo.py"
OUTPUT_PATH = BASE_DIR / "mumbai_routes.json"

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") == "production"

db = SQLAlchemy(app)
password_hasher = PasswordHasher()


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.BigInteger, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True),server_default=db.func.now())


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
    user = User(full_name=full_name,username=username,email=email,password_hash=password_hasher.hash(password))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username or email already exists"}), 409
    return jsonify({"message": "Registration successful","user_id": user.user_id}), 201


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
    return jsonify({"user_id": user.user_id,"full_name": user.full_name,"username": user.username,"email": user.email,"created_at": user.created_at.isoformat() if user.created_at else None})


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

@app.route("/api/generate-routes", methods=["POST"])
def generate_routes():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401
    if not SCRIPT_PATH.exists():
        return jsonify({"error": "Script not found"}), 500
    try:
        OUTPUT_PATH.unlink(missing_ok=True)
        subprocess.run([sys.executable, str(SCRIPT_PATH)],cwd=BASE_DIR,check=True,timeout=600)
        with OUTPUT_PATH.open("r", encoding="utf-8") as file:
            routes = json.load(file)
        return jsonify({"success": True,"count": len(routes)})
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError,OSError, json.JSONDecodeError):
        app.logger.exception("Route generation failed")
        return jsonify({"error": "Route generation failed"}), 500
if __name__ == "__main__":
    app.run(debug=True)
