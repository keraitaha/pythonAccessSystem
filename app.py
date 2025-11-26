from flask import Flask, request, jsonify
import sqlite3
import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import os

# Enums for better code readability
class AccessMethod(Enum):
    FACE = "face"
    CARD = "card"

class AccessResult(Enum):
    GRANTED = "granted"
    DENIED = "denied"

@dataclass
class User:
    id: int
    name: str
    role: str
    photoPath: str
    cardNumber: Optional[str] = None
    registrationDate: str = None

@dataclass
class AccessLog:
    id: int
    userId: int
    accessMethod: AccessMethod
    result: AccessResult
    timestamp: str
    deviceId: str

class AccessSystem:
    def __init__(self, dbPath: str = "mock.db"):
        self.dbPath = dbPath
        self.initDatabase()
    
    def initDatabase(self):
        # Initialize the SQLite database with required tables
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                photoPath TEXT NOT NULL,
                cardNumber TEXT,
                registrationDate TEXT NOT NULL
            )
        ''')
        
        # Photo tables (year-based as per requirements)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employeePhotos2023 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userId INTEGER NOT NULL,
                photoPath TEXT NOT NULL,
                FOREIGN KEY (userId) REFERENCES users (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS studentPhotos2023 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userId INTEGER NOT NULL,
                photoPath TEXT NOT NULL,
                FOREIGN KEY (userId) REFERENCES users (id)
            )
        ''')
        
        # Access log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accessLogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userId INTEGER,
                accessMethod TEXT NOT NULL,
                result TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                deviceId TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def registerUser(self, name: str, role: str, photoPath: str, cardNumber: Optional[str] = None) -> int:
        # Register a new user in the system
        registrationDate = datetime.datetime.now().isoformat()
        
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (name, role, photoPath, cardNumber, registrationDate)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, role, photoPath, cardNumber, registrationDate))
        
        userId = cursor.lastrowid
        
        # Store photo in appropriate year-based table
        if role.lower() == "employee":
            cursor.execute('''
                INSERT INTO employeePhotos2023 (userId, photoPath)
                VALUES (?, ?)
            ''', (userId, photoPath))
        elif role.lower() == "student":
            cursor.execute('''
                INSERT INTO studentPhotos2023 (userId, photoPath)
                VALUES (?, ?)
            ''', (userId, photoPath))
        
        conn.commit()
        conn.close()
        
        return userId
    
    def receiveFaceAccessResult(self, userId: int, accessGranted: bool, deviceId: str = "faceScanner01") -> Dict:
        # Receive processed face access result from facial scanner
        result = AccessResult.GRANTED if accessGranted else AccessResult.DENIED
        userInfo = self.getUserInfo(userId)
        userName = userInfo["name"] if userInfo else "Unknown User"
        
        # Log the access attempt
        self.logAccessAttempt(userId, AccessMethod.FACE, result, deviceId)
        
        return {
            "userId": userId,
            "userName": userName,
            "accessMethod": AccessMethod.FACE.value,
            "result": result.value,
            "timestamp": datetime.datetime.now().isoformat(),
            "deviceId": deviceId
        }
    
    def receiveCardAccessResult(self, cardNumber: str, accessGranted: bool, deviceId: str = "cardReader01") -> Dict:
        # Receive processed card access result from card scanner
        result = AccessResult.GRANTED if accessGranted else AccessResult.DENIED
        userInfo = self.getUserByCard(cardNumber)
        userId = userInfo["id"] if userInfo else None
        userName = userInfo["name"] if userInfo else "Unknown User"
        
        # Log the access attempt
        self.logAccessAttempt(userId, AccessMethod.CARD, result, deviceId)
        
        return {
            "userId": userId,
            "userName": userName,
            "cardNumber": cardNumber,
            "accessMethod": AccessMethod.CARD.value,
            "result": result.value,
            "timestamp": datetime.datetime.now().isoformat(),
            "deviceId": deviceId
        }
    
    def logAccessAttempt(self, userId: Optional[int], accessMethod: AccessMethod, result: AccessResult, deviceId: str):
        # Log access attempt to database (internal method)
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        timestamp = datetime.datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO accessLogs (userId, accessMethod, result, timestamp, deviceId)
            VALUES (?, ?, ?, ?, ?)
        ''', (userId, accessMethod.value, result.value, timestamp, deviceId))
        
        conn.commit()
        conn.close()
    
    def getUserInfo(self, userId: int) -> Optional[Dict]:
        # Get user information by ID
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, role, photoPath, cardNumber, registrationDate
            FROM users WHERE id = ?
        ''', (userId,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "role": row[2],
                "photoPath": row[3],
                "cardNumber": row[4],
                "registrationDate": row[5]
            }
        return None
    
    def getUserByCard(self, cardNumber: str) -> Optional[Dict]:
        # Get user information by card number
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, role, photoPath, cardNumber, registrationDate
            FROM users WHERE cardNumber = ?
        ''', (cardNumber,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "role": row[2],
                "photoPath": row[3],
                "cardNumber": row[4],
                "registrationDate": row[5]
            }
        return None
    
    def getAccessLogs(self, limit: int = 100) -> List[Dict]:
        # Retrieve access logs from database
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT al.id, al.userId, al.accessMethod, al.result, al.timestamp, al.deviceId, u.name
            FROM accessLogs al
            LEFT JOIN users u ON al.userId = u.id
            ORDER BY al.timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        logs = []
        for row in cursor.fetchall():
            logId, userId, accessMethod, result, timestamp, deviceId, name = row
            logs.append({
                "id": logId,
                "userId": userId,
                "userName": name,
                "accessMethod": accessMethod,
                "result": result,
                "timestamp": timestamp,
                "deviceId": deviceId
            })
        
        conn.close()
        return logs
    
    def getAllUsers(self) -> List[Dict]:
        # Get all registered users
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, role, photoPath, cardNumber, registrationDate
            FROM users
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                "id": row[0],
                "name": row[1],
                "role": row[2],
                "photoPath": row[3],
                "cardNumber": row[4],
                "registrationDate": row[5]
            })
        
        conn.close()
        return users
    
    def getAccessStats(self) -> Dict:
        # Get access statistics
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        # Total access attempts
        cursor.execute('SELECT COUNT(*) FROM accessLogs')
        totalAttempts = cursor.fetchone()[0]
        
        # Granted access attempts
        cursor.execute('SELECT COUNT(*) FROM accessLogs WHERE result = ?', (AccessResult.GRANTED.value,))
        grantedAttempts = cursor.fetchone()[0]
        
        # Denied access attempts
        cursor.execute('SELECT COUNT(*) FROM accessLogs WHERE result = ?', (AccessResult.DENIED.value,))
        deniedAttempts = cursor.fetchone()[0]
        
        # Access by method
        cursor.execute('SELECT accessMethod, COUNT(*) FROM accessLogs GROUP BY accessMethod')
        methodStats = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "totalAttempts": totalAttempts,
            "grantedAttempts": grantedAttempts,
            "deniedAttempts": deniedAttempts,
            "successRate": (grantedAttempts / totalAttempts * 100) if totalAttempts > 0 else 0,
            "methodStats": methodStats
        }

# Initialize Flask app and system
app = Flask(__name__)
system = AccessSystem()

# API ROUTES

@app.route('/')
def home():
    # Home endpoint with API information
    return jsonify({
        "message": "Dahua Access System API",
        "version": "1.0",
        "endpoints": {
            "user_management": {
                "register_user": "POST /api/users/register",
                "get_all_users": "GET /api/users",
                "get_user_by_id": "GET /api/users/<int:user_id>",
                "get_user_by_card": "GET /api/users/card/<string:card_number>"
            },
            "access_logs": {
                "submit_face_access": "POST /api/access/face",
                "submit_card_access": "POST /api/access/card",
                "get_access_logs": "GET /api/access/logs",
                "get_access_stats": "GET /api/access/stats"
            }
        }
    })

# USER MANAGEMENT API

@app.route('/api/users/register', methods=['POST'])
def register_user():
    # Register a new user
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        required_fields = ['name', 'role', 'photoPath']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        userId = system.registerUser(
            name=data['name'],
            role=data['role'],
            photoPath=data['photoPath'],
            cardNumber=data.get('cardNumber')
        )
        
        return jsonify({
            "message": "User registered successfully",
            "userId": userId
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    # Get all users or specific user by ID from header
    try:
        # Check if user ID is provided in header
        user_id_header = request.headers.get('User-Id')
        
        if user_id_header and user_id_header != "":
            try:
                # Get specific user
                user_id = int(user_id_header)
                user = system.getUserInfo(user_id)
                if user:
                    return jsonify({
                        "message": "User found",
                        "user": user
                    })
                else:
                    return jsonify({
                        "error": "User not found",
                        "userId": user_id
                    }), 404
                    
            except ValueError:
                return jsonify({
                    "error": "Invalid user ID format. Must be a number.",
                    "providedId": user_id_header
                }), 400
        
        # If no user ID header, return all users
        users = system.getAllUsers()
        return jsonify({
            "users": users,
            "count": len(users)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/card/<string:card_number>', methods=['GET'])
def get_user_by_card(card_number):
    # Get user information by card number
    try:
        user = system.getUserByCard(card_number)
        if user:
            return jsonify(user)
        else:
            return jsonify({"error": "User not found for this card"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ACCESS LOGS API

@app.route('/api/access/face', methods=['POST'])
def submit_face_access():
    # Submit face access result
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        if 'userId' not in data or 'accessGranted' not in data:
            return jsonify({"error": "Missing required fields: userId and accessGranted"}), 400
        
        result = system.receiveFaceAccessResult(
            userId=data['userId'],
            accessGranted=data['accessGranted'],
            deviceId=data.get('deviceId', 'faceScanner01')
        )
        
        return jsonify({
            "message": "Face access result logged successfully",
            "data": result
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/access/card', methods=['POST'])
def submit_card_access():
    # Submit card access result
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        if 'cardNumber' not in data or 'accessGranted' not in data:
            return jsonify({"error": "Missing required fields: cardNumber and accessGranted"}), 400
        
        result = system.receiveCardAccessResult(
            cardNumber=data['cardNumber'],
            accessGranted=data['accessGranted'],
            deviceId=data.get('deviceId', 'cardReader01')
        )
        
        return jsonify({
            "message": "Card access result logged successfully",
            "data": result
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/access/logs', methods=['GET'])
def get_access_logs():
    # Get access logs
    try:
        limit = request.args.get('limit', 100, type=int)
        logs = system.getAccessLogs(limit)
        return jsonify({
            "logs": logs,
            "count": len(logs)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/access/stats', methods=['GET'])
def get_access_stats():
    # Get access statistics
    try:
        stats = system.getAccessStats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ERROR HANDLERS

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
