import sqlite3

def get_connection():
    return sqlite3.connect("../data/data.db", check_same_thread=False)

def create_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Impianto (
        id_impianto         	INTEGER UNIQUE,
        nome	                TEXT,
        deposito_max	        INTEGER,
        deposito_0	            INTEGER,
        PRIMARY KEY("id_impianto")
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS Contadino (
        id_contadino	        INTEGER UNIQUE,
        nome	                TEXT,
        id_impianto	            INTEGER,
        distanza_impianto	    REAL,
        tipo_biomassa	        TEXT,
        uba	                    INTEGER,
        biomassa_uba_giorno 	REAL,
        modalita_svuotamento	TEXT,
        deposito_max	        REAL,
        deposito_0 	            REAL,
        quota	                INTEGER,
        alfa	                REAL,
        beta	                REAL,
        PRIMARY KEY("id_contadino")
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS Trasporto (
        id_trasporto	        INTEGER UNIQUE,
        nome	                TEXT,
        EF	                    TEXT,
        capacita_max	        TEXT,
        PRIMARY KEY("id_trasporto")
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS Clima (
        id_impianto	            INTEGER,
        mese	                INTEGER,
        temperatura	            REAL
    )''')
    conn.commit()
    conn.close()