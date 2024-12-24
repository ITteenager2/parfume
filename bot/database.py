import sqlite3
from typing import Dict, Any, List
from config import DATABASE_URL

def init_db():
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id TEXT PRIMARY KEY, first_name TEXT, last_name TEXT, 
                  age TEXT, gender TEXT, preferred_fragrances TEXT, location TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS feedback
                 (user_id TEXT, score INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY, user_id TEXT, product TEXT, timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS support_requests
                 (id INTEGER PRIMARY KEY, user_id TEXT, message TEXT, photo_id TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS recommendations
                 (id INTEGER PRIMARY KEY, user_id TEXT, recommendation TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def add_user(user_id: str, first_name: str, last_name: str):
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (id, first_name, last_name) VALUES (?, ?, ?)",
              (user_id, first_name, last_name))
    conn.commit()
    conn.close()

def update_user(user_id: str, field: str, value: Any):
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id))
    conn.commit()
    conn.close()

def get_user(user_id: str) -> Dict[str, Any]:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return {
            'id': user[0],
            'first_name': user[1],
            'last_name': user[2],
            'age': user[3],
            'gender': user[4],
            'preferred_fragrances': user[5],
            'location': user[6]
        }
    return {}

def get_all_users() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return [{'id': user[0], 'first_name': user[1], 'last_name': user[2], 'age': user[3],
             'gender': user[4], 'preferred_fragrances': user[5], 'location': user[6]} for user in users]

def add_order(user_id: str, product: str):
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("INSERT INTO orders (user_id, product) VALUES (?, ?)", (user_id, product))
    conn.commit()
    conn.close()

def get_user_orders(user_id: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE user_id = ?", (user_id,))
    orders = c.fetchall()
    conn.close()
    return [{'id': order[0], 'product': order[2], 'timestamp': order[3]} for order in orders]

def save_feedback(user_id: str, score: int):
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("INSERT INTO feedback (user_id, score) VALUES (?, ?)", (user_id, score))
    conn.commit()
    conn.close()

def get_feedback_stats() -> Dict[str, Any]:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT AVG(score) as avg_score, COUNT(*) as total_feedback FROM feedback")
    result = c.fetchone()
    conn.close()
    return {
        'average_score': result[0],
        'total_feedback': result[1]
    }

def save_support_request(user_id: str, message: str, photo_id: str = None):
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("INSERT INTO support_requests (user_id, message, photo_id) VALUES (?, ?, ?)",
              (user_id, message, photo_id))
    conn.commit()
    conn.close()

def get_support_requests() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT * FROM support_requests ORDER BY timestamp DESC")
    requests = c.fetchall()
    conn.close()
    return [{'id': req[0], 'user_id': req[1], 'message': req[2], 'photo_id': req[3], 'timestamp': req[4]} for req in requests]

def get_support_request_count() -> int:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM support_requests")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_recommendation_count() -> int:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM recommendations")
    count = c.fetchone()[0]
    conn.close()
    return count

