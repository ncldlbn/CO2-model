import sqlite3

def get_connection():
    return sqlite3.connect("../data.db", check_same_thread=False)

def create_tables():
    conn = get_connection()
    c = conn.cursor()
    
    # =====================================
    # TABELLA IMPIANTO
    # =====================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS impianto (
            id_impianto INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            deposito_max REAL,
            Qout_liq REAL,
            Qout_let REAL,
            separazione BOOLEAN
        )
    ''')
    
    # =====================================
    # TABELLA TRASPORTI
    # =====================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS trasporti (
            id_trasporto INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            EF REAL NOT NULL,
            capacita_max REAL
        )
    ''')
    
    # =====================================
    # TABELLA ALLEVATORE
    # =====================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS allevatore (
            id_allevatore INTEGER PRIMARY KEY AUTOINCREMENT,
            denominazione_sociale TEXT NOT NULL,
            id_impianto_associato INTEGER NOT NULL,
            tipo_conferimento TEXT NOT NULL CHECK (tipo_conferimento IN ('mezzi', 'tubazione')),
            frequenza_conferimento INTEGER NOT NULL,
            id_trasporto INTEGER NOT NULL,
            distanza_impianto REAL NOT NULL,
            uba_letame INTEGER NOT NULL,
            uba_liquame INTEGER NOT NULL,
            prod_letame REAL NOT NULL,
            prod_liquame REAL NOT NULL,
            deposito_max REAL NOT NULL,
            quota INTEGER,
            portata REAL,
            potenza REAL,
            ore INTEGER,
            FOREIGN KEY(id_impianto_associato) REFERENCES impianto(id_impianto),
            FOREIGN KEY(id_trasporto) REFERENCES trasporti(id_trasporto),
            CHECK (
                (tipo_conferimento = 'tubazione' AND portata IS NOT NULL AND potenza IS NOT NULL AND ore IS NOT NULL)
                OR (tipo_conferimento <> 'tubazione' AND portata IS NULL AND potenza IS NULL AND ore IS NULL)
            )
        )
    ''')
    
    # =====================================
    # TABELLA FATTORI EMISSIONE
    # =====================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS fattori_emissione (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL,
            nome TEXT NOT NULL,
            valore REAL NOT NULL,
            unita TEXT NOT NULL
        )
    ''')
    
    # =====================================
    # TABELLA RICETTA IMPIANTO
    # =====================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS ricetta_impianto (
            id_ricetta INTEGER PRIMARY KEY AUTOINCREMENT,
            id_impianto INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            quantita REAL,
            FOREIGN KEY (id_impianto) REFERENCES impianto(id_impianto)
        )
    ''')
    
    # =====================================
    # TABELLA BILANCIO ENERGETICO
    # =====================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS bilancio_energetico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_impianto INTEGER NOT NULL,
            categoria TEXT NOT NULL CHECK (categoria IN ('prodotta', 'autoconsumata', 'acquistata')),
            tipo TEXT NOT NULL,
            valore REAL NOT NULL,
            unita TEXT NOT NULL,
            FOREIGN KEY (id_impianto) REFERENCES impianto(id_impianto),
            CHECK (
                (categoria = 'prodotta' AND tipo IN ('EE_BT','EE_MT','calore','biometano','bioLNG','CO2_biogenica'))
                OR (categoria = 'autoconsumata' AND tipo IN ('EE','EE_trasporti_tubazioni','calore','biometano','bioLNG'))
                OR (categoria = 'acquistata' AND tipo IN ('EE_BT','EE_MT','metano','LNG'))
            )
        )
    ''')
    
    # =====================================
    # TABELLA RICETTORI
    # =====================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS ricettori (
            id_ricettore INTEGER PRIMARY KEY AUTOINCREMENT,
            id_impianto INTEGER NOT NULL,
            id_trasporto INTEGER NOT NULL,
            tipo TEXT,
            distanza REAL NOT NULL,
            FOREIGN KEY(id_impianto) REFERENCES impianto(id_impianto),
            FOREIGN KEY(id_trasporto) REFERENCES trasporti(id_trasporto)
        )
    ''')
    
    # =====================================
    # TABELLA COSTANTI IMPIANTO
    # =====================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS costanti_impianto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            classe_potenza TEXT NOT NULL,
            valore REAL NOT NULL,
            unita TEXT NOT NULL
        )
    ''')
    
    # =====================================
    # INSERIMENTO DATI INIZIALI
    # =====================================
    
    # Inserimento dati trasporti
    c.execute('''
        INSERT OR IGNORE INTO trasporti (id_trasporto, tipo, EF, capacita_max) VALUES
        (0, 'tubazione', 0, NULL),
        (1, 'camion_generico', 0.1487, 25),
        (2, 'trattore', 0.3855, NULL)
    ''')
    
    # Inserimento fattori emissione
    c.execute('''
        INSERT OR IGNORE INTO fattori_emissione (categoria, nome, valore, unita) VALUES
        ('energia', 'EE_BT', 680.6468, 'kg CO2eq/kWh'),
        ('energia', 'EE_MT', 0.6411, 'kg CO2eq/kWh'),
        ('energia', 'calore', 0.2919, 'kg CO2eq/kWh'),
        ('energia', 'metano', 0.2979, 'kg CO2eq/kWh'),
        ('energia', 'LNG', 0.3731, 'kg CO2eq/kWh'),
        ('energia', 'cogen_EE_BT', 0.0105, 'kg CO2eq/kWh'),
        ('energia', 'cogen_EE_MT', 0.0103, 'kg CO2eq/kWh'),
        ('impianto', 'olio_lubrificante', 1.7778, 'kg CO2eq/kg'),
        ('impianto', 'rifiuti_pericolosi', 0, 'kg CO2eq/kg'),
        ('impianto', 'acqua', 0.3021, 'kg CO2eq/mc'),
        ('impianto', 'scarichi', 0.3193, 'kg CO2eq/mc'),
        ('altro', 'CO2_biogenica', 0.7374, 'kg CO2eq/unit'),
        ('altro', 'digestato', 16.71, 'kg CO2eq/tonSS'),
        ('altro', 'pollina', 3.5230, 'kg CO2eq/ton')
    ''')
    
    # Inserimento costanti impianto
    c.execute('''
        INSERT OR IGNORE INTO costanti_impianto (nome, classe_potenza, valore, unita) VALUES
        ('olio_lubrificante', 'P<500kW', 500, 'kg'),
        ('olio_lubrificante', 'P<1000kW', 1000, 'kg'),
        ('olio_lubrificante', 'P>1000kW', 2000, 'kg'),
        ('rifiuti_pericolosi', 'P<500kW', 500, 'kg'),
        ('rifiuti_pericolosi', 'P<1000kW', 1000, 'kg'),
        ('rifiuti_pericolosi', 'P>1000kW', 2000, 'kg'),
        ('acqua', 'P<500kW', 500, 'mc'),
        ('acqua', 'P<1000kW', 1500, 'mc'),
        ('acqua', 'P>1000kW', 2000, 'mc'),
        ('scarichi', 'P<500kW', 500, 'mc'),
        ('scarichi', 'P<1000kW', 1500, 'mc'),
        ('scarichi', 'P>1000kW', 2000, 'mc')
    ''')
    
    conn.commit()
    conn.close()