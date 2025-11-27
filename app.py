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

        # Face templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faceTemplates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userId INTEGER NOT NULL,
                userName TEXT NOT NULL,
                faceTemplate TEXT,
                photoData TEXT,
                enrollmentDate TEXT NOT NULL,
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
    
    def addFaceTemplate():
        # Add face template for a user
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            # Validate required fields
            requiredFields = ['userId', 'userName']
            for field in requiredFields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400
            
            userId = data['userId']
            userName = data['userName']
            faceTemplates = data.get('faceTemplates', [])
            photos = data.get('photos', [])
            
            # Check if user exists
            userInfo = system.getUserInfo(int(userId))
            if not userInfo:
                return jsonify({"error": f"User with ID {userId} not found"}), 404
            
            # Validate limits
            if len(faceTemplates) > 20:
                return jsonify({"error": "Maximum 20 face templates allowed"}), 400
            
            if len(photos) > 5:
                return jsonify({"error": "Maximum 5 photos allowed"}), 400
            
            # Store in database
            enrollmentDate = datetime.datetime.now().isoformat()
            conn = sqlite3.connect(system.dbPath)
            cursor = conn.cursor()
            
            templatesStored = 0
            for i, faceTemplate in enumerate(faceTemplates):
                photoToStore = photos[i] if i < len(photos) else ""
                
                cursor.execute('''
                    INSERT INTO faceTemplates (userId, userName, faceTemplate, photoData, enrollmentDate)
                    VALUES (?, ?, ?, ?, ?)
                ''', (userId, userName, faceTemplate, photoToStore, enrollmentDate))
                templatesStored += 1
            
            conn.commit()
            conn.close()
            
            print(f"Face enrollment stored - UserID: {userId}, Name: {userName}")
            print(f"Templates stored: {templatesStored}, Photos stored: {len(photos)}")
            
            return jsonify({
                "message": "Face template enrolled and stored successfully",
                "userId": userId,
                "userName": userName,
                "templatesCount": templatesStored,
                "photosCount": len(photos),
                "enrollmentDate": enrollmentDate
            })
            
        except ValueError:
            return jsonify({"error": "Invalid userId format"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
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

# Initialize Flask app and system
app = Flask(__name__)
system = AccessSystem()

# API ROUTES

@app.route('/')
def home():
    # Home endpoint with API information
    return jsonify({
        "message": "Access System API",
        "version": "1.0",
        "endpoints": {
            "user_management": {
                "register_user": "POST /api/users/register",
                "get_users": "GET /api/users (use User-Id header for specific user)",
                "get_user_by_card": "GET /api/users/card/<card_number>"
            },
            "access_logs": {
                "submit_face_access": "POST /api/access/face", 
                "submit_card_access": "POST /api/access/card",
                "get_access_logs": "GET /api/access/logs",
                "get_offline_records_json": "GET /api/access/offline-records"
            },
            "face_management": {
                "enroll_face_json": "POST /api/face/enroll",
                "get_face_templates": "GET /api/face/templates/<user_id>",
                "enroll_face_dahua": "POST /cgi-bin/FaceInfoManager.cgi?action=add"
            },
            "dahua_compatible": {
                "get_offline_records": "GET /cgi-bin/recordFinder.cgi?action=find&name=AccessControlCardRec&[params]",
                "enroll_face": "POST /cgi-bin/FaceInfoManager.cgi?action=add"
            }
        }
    })

# USER MANAGEMENT API

# ENROLL USER API
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

# FIND USER API
@app.route('/api/users', methods=['GET'])
def get_users():
    # Get all users or specific user by ID from header
    try:
        # Check if user ID is provided in header
        userIdHeader = request.headers.get('User-Id')
        
        if userIdHeader and userIdHeader != "":
            try:
                # Get specific user
                userId = int(userIdHeader)
                user = system.getUserInfo(userId)
                if user:
                    return jsonify({
                        "message": "User found",
                        "user": user
                    })
                else:
                    return jsonify({
                        "error": "User not found",
                        "userId": userId
                    }), 404
                    
            except ValueError:
                return jsonify({
                    "error": "Invalid user ID format. Must be a number.",
                    "providedId": userIdHeader
                }), 400
        
        # If no user ID header, return all users
        users = system.getAllUsers()
        return jsonify({
            "users": users,
            "count": len(users)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# FIND USER BY CARD API
@app.route('/api/users/card/<string:cardNumber>', methods=['GET'])
def get_user_by_card(cardNumber):
    # Get user information by card number
    try:
        user = system.getUserByCard(cardNumber)
        if user:
            return jsonify(user)
        else:
            return jsonify({"error": "User not found for this card"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ENROLL FACE TEMPLATE API
@app.route('/cgi-bin/FaceInfoManager.cgi', methods=['POST'])
def manageFaceInfo():
    # Manage face templates (Dahua API compatible)
    try:
        # Get action parameter from query string
        action = request.args.get('action')
        
        if action == 'add':
            return system.addFaceTemplate()
        else:
            return "error=Unsupported action", 400
    except Exception as e:
        return f"error={str(e)}", 500

@app.route('/api/face/enroll', methods=['POST'])
def enrollFaceJson():
    #Enroll face template (JSON version - no storage)
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Validate required fields
        requiredFields = ['userId', 'userName']
        for field in requiredFields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        userId = data['userId']
        userName = data['userName']
        faceTemplates = data.get('faceTemplates', [])
        photos = data.get('photos', [])
        
        # Check if user exists
        userInfo = system.getUserInfo(int(userId))
        if not userInfo:
            return jsonify({"error": f"User with ID {userId} not found"}), 404
        
        # Validate limits
        if len(faceTemplates) > 20:
            return jsonify({"error": "Maximum 20 face templates allowed"}), 400
        
        if len(photos) > 5:
            return jsonify({"error": "Maximum 5 photos allowed"}), 400
        
        # Log the enrollment (no database storage)
        print(f"✓ Face enrollment received - UserID: {userId}, Name: {userName}")
        print(f"  Templates: {len(faceTemplates)}, Photos: {len(photos)}")
        print(f"  Note: Data not persisted in mock database")
        
        return jsonify({
            "message": "Face template enrollment received successfully",
            "note": "Face data not stored in mock database",
            "userId": userId,
            "userName": userName,
            "templatesCount": len(faceTemplates),
            "photosCount": len(photos)
        })
        
    except ValueError:
        return jsonify({"error": "Invalid userId format"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# LOG FR ACCESS API
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

# LOG CARD ACCESS API
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

# ACCESS LOGS API

# GET ACCESS LOGS API
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

# OFFLINE ACCESS RECORDS API
@app.route('/cgi-bin/recordFinder.cgi', methods=['GET'])
def getOfflineAccessRecords():
    # Get offline access records from device (Dahua API compatible)
    try:
        # Get query parameters
        action = request.args.get('action')
        name = request.args.get('name')
        
        # Validate required parameters
        if action != 'find':
            return "action=find", 400
        
        if name != 'AccessControlCardRec':
            return "name=AccessControlCardRec", 400
        
        # Get optional parameters
        count = request.args.get('count', 1024, type=int)
        startTime = request.args.get('StartTime')
        endTime = request.args.get('EndTime')
        cardNo = request.args.get('condition.CardNo')
        
        # Build query conditions based on parameters
        queryConditions = []
        params = []
        
        if startTime and endTime:
            queryConditions.append("timestamp BETWEEN ? AND ?")
            params.extend([startTime, endTime])
        elif startTime:
            queryConditions.append("timestamp >= ?")
            params.append(startTime)
        elif endTime:
            queryConditions.append("timestamp <= ?")
            params.append(endTime)
            
        # Build the SQL query
        whereClause = " AND ".join(queryConditions) if queryConditions else "1=1"
        
        # Modified query to match Dahua record structure
        conn = sqlite3.connect(system.dbPath)
        cursor = conn.cursor()
        
        # This query transforms our access logs into Dahua-compatible format
        cursor.execute(f'''
            SELECT 
                al.id as RecNo,
                CAST(strftime('%s', al.timestamp) as INTEGER) as CreateTime,
                u.cardNumber as CardNo,
                u.name as CardName,
                u.name as UserID,
                CASE 
                    WHEN al.accessMethod = 'face' THEN 'Entry'
                    ELSE 'Entry'
                END as Type,
                CASE 
                    WHEN al.result = 'granted' THEN 1
                    ELSE 0
                END as Status,
                CASE 
                    WHEN al.accessMethod = 'face' THEN 15
                    WHEN al.accessMethod = 'card' THEN 1
                    ELSE 1
                END as Method,
                1 as Door,
                al.deviceId as ReaderID,
                al.timestamp as originalTimestamp
            FROM accessLogs al
            LEFT JOIN users u ON al.userId = u.id
            WHERE {whereClause}
            ORDER BY al.timestamp DESC
            LIMIT ?
        ''', params + [count])
        
        records = cursor.fetchall()
        conn.close()
        
        # Convert to Dahua response format
        formattedRecords = []
        for record in records:
            (recNo, createTime, cardNo, cardName, userId, 
             recordType, status, method, door, readerId, originalTimestamp) = record
            
            formattedRecord = {
                "RecNo": recNo,
                "CreateTime": createTime,
                "CardNo": cardNo if cardNo else "",
                "CardName": cardName if cardName else "Unknown",
                "CardType": 0,  # Ordinary card
                "UserID": userId if userId else "Unknown",
                "Type": recordType,
                "Status": status,
                "Method": method,
                "Door": door,
                "ReaderID": readerId,
                "ErrorCode": 0 if status == 1 else 1,
                "URL": "",
                "RecordURL": "",
                "IsOverTemperature": False,
                "TemperatureUnit": 0,
                "CurrentTemperature": 36.5,
                "CitizenIDResult": False
            }
            formattedRecords.append(formattedRecord)
        
        # Prepare response in key=value format
        responseLines = [
            f"totalCount={len(formattedRecords)}",
            f"found={len(formattedRecords)}"
        ]
        
        # Add each record
        for i, record in enumerate(formattedRecords):
            for key, value in record.items():
                if value is not None:
                    if isinstance(value, bool):
                        value = str(value).lower()
                    elif isinstance(value, (int, float)):
                        value = str(value)
                    responseLines.append(f"records[{i}].{key}={value}")
        
        # Return as plain text with key=value format
        return "\n".join(responseLines), 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        return f"error={str(e)}", 500

@app.route('/api/access/offline-records', methods=['GET'])
def getOfflineAccessRecordsJson():
    # Get offline access records in JSON format
    try:
        # Get query parameters
        count = request.args.get('Count', 1024, type=int)
        startTime = request.args.get('StartTime')
        endTime = request.args.get('EndTime')
        cardNo = request.args.get('CardNo')
        
        # Build query conditions
        query_conditions = []
        params = []
        
        if startTime and endTime:
            query_conditions.append("timestamp BETWEEN ? AND ?")
            params.extend([startTime, endTime])
        
        where_clause = " AND ".join(query_conditions) if query_conditions else "1=1"
        
        # Query the database
        conn = sqlite3.connect(system.dbPath)
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT 
                al.id as RecNo,
                CAST(strftime('%s', al.timestamp) as INTEGER) as CreateTime,
                u.cardNumber as CardNo,
                u.name as CardName,
                u.name as UserID,
                CASE 
                    WHEN al.accessMethod = 'face' THEN 'Entry'
                    ELSE 'Entry'
                END as Type,
                CASE 
                    WHEN al.result = 'granted' THEN 1
                    ELSE 0
                END as Status,
                CASE 
                    WHEN al.accessMethod = 'face' THEN 15
                    WHEN al.accessMethod = 'card' THEN 1
                    ELSE 1
                END as Method,
                1 as Door,
                al.deviceId as ReaderID
            FROM accessLogs al
            LEFT JOIN users u ON al.userId = u.id
            WHERE {where_clause}
            ORDER BY al.timestamp DESC
            LIMIT ?
        ''', params + [count])
        
        records = cursor.fetchall()
        conn.close()
        
        # Convert to desired format
        formatted_records = []
        for record in records:
            (rec_no, create_time, cardNo, card_name, userId, 
             record_type, status, method, door, reader_id) = record
            
            formatted_records.append({
                "RecNo": rec_no,
                "CreateTime": create_time,
                "CardNo": cardNo if cardNo else "",
                "CardName": card_name if card_name else "Unknown",
                "CardType": 0,
                "UserID": userId if userId else "Unknown",
                "Type": record_type,
                "Status": status,
                "Method": method,
                "Door": door,
                "ReaderID": reader_id,
                "ErrorCode": 0 if status == 1 else 1,
                "URL": "",
                "RecordURL": "",
                "IsOverTemperature": False,
                "TemperatureUnit": 0,
                "CurrentTemperature": 36.5,
                "CitizenIDResult": False
            })
        
        return jsonify({
            "totalCount": len(formatted_records),
            "found": len(formatted_records),
            "records": formatted_records
        })
        
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
