from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# Database setup and connection
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Create tables for schedule and history
with get_db_connection() as conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS schedule (id INTEGER PRIMARY KEY, device_id TEXT, time TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, device_id TEXT, taken_time TEXT)''')

@app.route('/')
def index():
    return "Welcome to the Pill Dispenser API!"

@app.route('/nurse/<deviceId>', methods=['GET'])
def nurse(deviceId):
    return jsonify({'message': f'Nurse view for device {deviceId}'})

@app.route('/patient/<deviceId>', methods=['GET'])
def patient(deviceId):
    return jsonify({'message': f'Patient view for device {deviceId}'})

@app.route('/api/schedule/<deviceId>', methods=['GET', 'POST'])
def schedule(deviceId):
    if request.method == 'POST':
        record_time = request.json['time']
        with get_db_connection() as conn:
            conn.execute('INSERT INTO schedule (device_id, time) VALUES (?, ?)', (deviceId, record_time))
        return jsonify({'message': 'Schedule updated.'}), 201
    else:
        with get_db_connection() as conn:
            schedule_items = conn.execute('SELECT * FROM schedule WHERE device_id = ?', (deviceId,)).fetchall()
        return jsonify([dict(row) for row in schedule_items])

@app.route('/api/taken', methods=['POST'])
def taken():
    deviceId = request.json['device_id']
    taken_time = request.json['taken_time']
    with get_db_connection() as conn:
        conn.execute('INSERT INTO history (device_id, taken_time) VALUES (?, ?)', (deviceId, taken_time))
    return jsonify({'message': 'Logged taken time.'}), 201

if __name__ == '__main__':
    app.run(debug=True)