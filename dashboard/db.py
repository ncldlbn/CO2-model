import sqlite3
import os


def get_connection():
    # Calcola il percorso assoluto del database
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, '../data.db')

    return sqlite3.connect(db_path, check_same_thread=False)
