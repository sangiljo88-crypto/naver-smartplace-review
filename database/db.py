import sqlite3
from contextlib import contextmanager
from pathlib import Path
import os

# 데이터베이스 경로
DATABASE_PATH = Path(__file__).parent / "reviews.db"

def init_db():
    """데이터베이스 초기화"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Users 테이블 (설정 저장용)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Reply History 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reply_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id TEXT,
            business_name TEXT,
            review_id TEXT,
            review_author TEXT,
            review_content TEXT,
            review_rating INTEGER,
            reply_content TEXT,
            ai_generated BOOLEAN DEFAULT 0,
            status TEXT DEFAULT 'posted',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Reply Templates 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reply_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            content TEXT,
            tone TEXT,
            for_rating INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    """데이터베이스 연결 컨텍스트 매니저"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def save_setting(key: str, value: str):
    """설정 저장"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO settings (key, value, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value=?, updated_at=CURRENT_TIMESTAMP
        ''', (key, value, value))
        conn.commit()

def get_setting(key: str, default: str = None) -> str:
    """설정 조회"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        return row['value'] if row else default

def save_reply_history(business_id: str, business_name: str, review_id: str, 
                       review_author: str, review_content: str, review_rating: int,
                       reply_content: str, ai_generated: bool = False):
    """답글 히스토리 저장"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reply_history 
            (business_id, business_name, review_id, review_author, review_content, 
             review_rating, reply_content, ai_generated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (business_id, business_name, review_id, review_author, review_content,
              review_rating, reply_content, ai_generated))
        conn.commit()

def get_reply_history(limit: int = 50) -> list:
    """답글 히스토리 조회"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM reply_history 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
