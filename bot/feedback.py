import sqlite3
from typing import Dict, Any
from config import DATABASE_URL

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

