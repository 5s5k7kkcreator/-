import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_FILE = "playlists.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id TEXT UNIQUE NOT NULL,
            playlist_title TEXT,
            user_id INTEGER NOT NULL,
            check_interval INTEGER DEFAULT 300,
            is_active INTEGER DEFAULT 1,
            last_check TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            playlist_id TEXT NOT NULL,
            title TEXT,
            channel_name TEXT,
            position INTEGER,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(video_id, playlist_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notified_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            playlist_id TEXT NOT NULL,
            change_type TEXT NOT NULL,
            notified_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(video_id, playlist_id, change_type)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_playlist(playlist_id: str, playlist_title: str, user_id: int, check_interval: int = 300) -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO playlists (playlist_id, playlist_title, user_id, check_interval, is_active)
            VALUES (?, ?, ?, ?, 1)
        ''', (playlist_id, playlist_title, user_id, check_interval))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding playlist: {e}")
        return False

def remove_playlist(playlist_id: str, user_id: int) -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM videos WHERE playlist_id = ?', (playlist_id,))
        cursor.execute('DELETE FROM notified_changes WHERE playlist_id = ?', (playlist_id,))
        cursor.execute('DELETE FROM playlists WHERE playlist_id = ? AND user_id = ?', (playlist_id, user_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0
    except Exception as e:
        print(f"Error removing playlist: {e}")
        return False

def get_user_playlists(user_id: int) -> List[Dict]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT playlist_id, playlist_title, check_interval, is_active, last_check
        FROM playlists WHERE user_id = ?
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'playlist_id': row[0],
            'title': row[1],
            'check_interval': row[2],
            'is_active': row[3],
            'last_check': row[4]
        }
        for row in rows
    ]

def get_all_active_playlists() -> List[Dict]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT playlist_id, playlist_title, user_id, check_interval, last_check
        FROM playlists WHERE is_active = 1
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'playlist_id': row[0],
            'title': row[1],
            'user_id': row[2],
            'check_interval': row[3],
            'last_check': row[4]
        }
        for row in rows
    ]

def set_playlist_active(playlist_id: str, user_id: int, active: bool) -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE playlists SET is_active = ? WHERE playlist_id = ? AND user_id = ?
        ''', (1 if active else 0, playlist_id, user_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0
    except Exception as e:
        print(f"Error updating playlist: {e}")
        return False

def get_playlist_videos(playlist_id: str) -> List[Dict]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT video_id, title, channel_name, position
        FROM videos WHERE playlist_id = ?
    ''', (playlist_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'video_id': row[0],
            'title': row[1],
            'channel_name': row[2],
            'position': row[3]
        }
        for row in rows
    ]

def save_playlist_videos(playlist_id: str, videos: List[Dict]):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM videos WHERE playlist_id = ?', (playlist_id,))
    
    for video in videos:
        cursor.execute('''
            INSERT INTO videos (video_id, playlist_id, title, channel_name, position)
            VALUES (?, ?, ?, ?, ?)
        ''', (video['video_id'], playlist_id, video['title'], video['channel_name'], video['position']))
    
    cursor.execute('''
        UPDATE playlists SET last_check = ? WHERE playlist_id = ?
    ''', (datetime.now().isoformat(), playlist_id))
    
    conn.commit()
    conn.close()

def is_change_notified(video_id: str, playlist_id: str, change_type: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM notified_changes 
        WHERE video_id = ? AND playlist_id = ? AND change_type = ?
    ''', (video_id, playlist_id, change_type))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_change_notified(video_id: str, playlist_id: str, change_type: str):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO notified_changes (video_id, playlist_id, change_type)
            VALUES (?, ?, ?)
        ''', (video_id, playlist_id, change_type))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error marking change: {e}")

def update_check_interval(playlist_id: str, user_id: int, interval: int) -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE playlists SET check_interval = ? WHERE playlist_id = ? AND user_id = ?
        ''', (interval, playlist_id, user_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0
    except Exception as e:
        print(f"Error updating interval: {e}")
        return False
