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
from ping3 import ping
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

ALL_CLIENTS = [
    {"client": "raspberrypi01", "ipaddress": "192.168.1.1"},
    {"client": "raspberrypi02", "ipaddress": "172.31.16.17"},
    {"client": "raspberrypi03", "ipaddress": "172.31.16.19"},
    {"client": "raspberrypi04", "ipaddress": "192.168.1.128"},
    {"client": "raspberrypi05", "ipaddress": "172.31.16.23"},
    {"client": "raspberrypi06", "ipaddress": "172.31.16.3"},
    {"client": "raspberrypi07", "ipaddress": "172.31.16.21"},
    {"client": "raspberrypi08", "ipaddress": "172.31.16.25"},
    {"client": "raspberrypi09", "ipaddress": "172.31.16.4"},
    {"client": "rpitest", "ipaddress": "192.168.1.138"},
]


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

        cursor.execute("""
            INSERT INTO rfid_log (epc, rssi, ipaddress, client)
            VALUES (%s, %s, %s, %s)
        """, (epc, rssi, ip, client))

        cursor.execute("""
            INSERT INTO client_status (client_name, ipaddress, last_seen)
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE last_seen = NOW(), ipaddress = VALUES(ipaddress)
        """, (client, ip))

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



@app.route("/login")
def login_page():
    return render_template("login_page.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/users", methods=["GET"])
@jwt_required()
def list_users():
    conn = get_sqlite_conn()
    rows = conn.execute("SELECT id, username FROM users").fetchall()
    conn.close()
    users = [dict(row) for row in rows]
    return jsonify(users)

@app.route("/api/users", methods=["POST"])
@jwt_required()
def add_user():
    identity = get_jwt_identity()
    if identity != "admin":
        return jsonify({"msg": "Not authorized"}), 403
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    conn = get_sqlite_conn()
    conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()

    return jsonify({"msg": "User created"})

@app.route("/api/users/<username>", methods=["PUT"])
@jwt_required()
def update_password(username):
    identity = get_jwt_identity()
    if identity != "admin":
        return jsonify({"msg": "Not authorized"}), 403
    data = request.get_json()
    new_password = data.get("password")

    conn = get_sqlite_conn()
    conn.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
    conn.commit()
    conn.close()

    return jsonify({"msg": "Password updated"})


@app.route("/api/users/<username>", methods=["DELETE"])
@jwt_required()
def delete_user(username):
    identity = get_jwt_identity()
    if identity != "admin":
        return jsonify({"msg": "Not authorized"}), 403
    conn = get_sqlite_conn()
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()

    return jsonify({"msg": "User deleted"})

@app.route("/users.html")
#@jwt_required()
def users_page():
 #   identity = get_jwt_identity()
 #   if identity != "admin":
 #       return jsonify({"msg": "Not authorized"}), 403
    return render_template("users.html")


@app.route("/swagger.json")
def swagger_spec():
    return send_file("swagger.json", mimetype="application/json")



def ping_host(ip):
    try:
        result = ping(ip, timeout=1)
        return result is not None
    except Exception:
        return False

@app.route("/api/clients_status", methods=["GET"])
@jwt_required()
def clients_status():
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT client_name AS client, ipaddress, last_seen
            FROM client_status
        """)
        db_rows = cursor.fetchall()
        cursor.close()
        conn.close()

        db_map = { row["client"]: row for row in db_rows }

        result = []
        for client in ALL_CLIENTS:
            c_name = client["client"]
            ip = client["ipaddress"]

            # ตรวจ ICMP
            network_ok = ping_host(ip)

            row = db_map.get(c_name)

            last_seen_str = "Never"
            if row and row["last_seen"]:
                last_seen_str = row["last_seen"].strftime("%Y-%m-%d %H:%M:%S")

            result.append({
                "client": c_name,
                "ipaddress": ip,
                "last_seen": last_seen_str,
                "network_online": network_ok
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/clients_status.html")
#@jwt_required()
def clients_status_page():
    return render_template("clients_status.html")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

