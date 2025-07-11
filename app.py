from flask import Flask, request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask import render_template
from flask import send_file
import mysql.connector
import sqlite3
import os
from datetime import timedelta

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET", "secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=5)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)

jwt = JWTManager(app)

def get_sqlite_conn():
    conn = sqlite3.connect("/data/users.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_mysql_conn():
    return mysql.connector.connect(
        # host=os.environ.get("DB_HOST", "mysql"),
        # user=os.environ.get("DB_USER", "rfiduser"),
        # password=os.environ.get("DB_PASSWORD", "rfidpass"),
        # database=os.environ.get("DB_NAME", "rfid_db")
        host=os.environ.get("DB_HOST", "mysql"),
        user=os.environ.get("DB_USER", "rfiduser"),
        password=os.environ.get("DB_PASSWORD", "rfidpass"),
        database=os.environ.get("DB_NAME", "rfid_db")
    )

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        conn = get_sqlite_conn()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and user["password"] == password:
            access_token = create_access_token(identity=username)
            refresh_token = create_refresh_token(identity=username)
            return jsonify(access_token=access_token, refresh_token=refresh_token)
        return jsonify({"msg": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify(access_token=access_token)

@app.route("/api/rfid-logs", methods=["GET"])
@jwt_required()
def rfid_logs():
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM rfid_log ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)


@app.route("/api/rfid", methods=["POST"])
@jwt_required()
def rfid():
    data = request.get_json()
    epc = data.get("epc")
    rssi = data.get("rssi")
    ip = data.get("ipaddress")
    client = data.get("client")

    try:
        conn = get_mysql_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rfid_log (epc, rssi, ipaddress, client) VALUES (%s, %s, %s, %s)",
            (epc, rssi, ip, client)
        )
        conn.commit()
        cursor.close()
        conn.close()
        socketio.emit("new_rfid", {
            "epc": epc,
            "rssi": rssi,
            "ipaddress": ip,
            "client": client
        })
        return jsonify({"msg": "Data received"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/login_page.html")
def login_page():
    return render_template("login_page.html")

    
@app.route("/swagger.json")
def swagger_spec():
    return send_file("swagger.json", mimetype="application/json")

if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=5000)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
