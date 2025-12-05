import sqlite3
import os

def get_connection():
    # Calcola il percorso assoluto del database
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, '../data.db')
       
    return sqlite3.connect(db_path, check_same_thread=False)

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
            separazione BOOLEAN,
            olio_lubrificante REAL,
            rifiuti REAL,
            acqua REAL,
            scarichi REAL
        )
    ''')
    
    # =====================================
    # TABELLA TRASPORTI
    # =====================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS trasporti (
            id_trasporto INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
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
            frequenza_conferimento_let INTEGER NOT NULL,
            frequenza_conferimento_liq INTEGER NOT NULL,
            id_trasporto INTEGER NOT NULL,
            distanza_impianto REAL NOT NULL,
            uba_letame INTEGER,
            uba_liquame INTEGER,
            prod_letame REAL,
            prod_liquame REAL,
            pollina REAL,
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
            unita TEXT,
            CO2_fossile REAL,
            CO2_biogenica REAL,
            CO2_dLUC REAL,
            CO2_TOT REAL
        );
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
            carico INTEGER,
            FOREIGN KEY(id_impianto) REFERENCES impianto(id_impianto),
            FOREIGN KEY(id_trasporto) REFERENCES trasporti(id_trasporto)
        )
    ''')
    
    # =====================================
    # INSERIMENTO DATI INIZIALI
    # =====================================
    
    # Inserimento dati trasporti
    c.execute('''
        INSERT OR IGNORE INTO trasporti (id_trasporto, tipo, capacita_max) VALUES
        (0, 'tubazione', NULL),
        (1, 'camion_generico', 25),
        (2, 'trattore', NULL)
    ''')
    
    # Inserimento fattori emissione
    c.execute('''
        INSERT OR IGNORE INTO fattori_emissione 
        (id, categoria, nome, unita,  CO2_fossile, CO2_biogenica, CO2_dluc, CO2_TOT) VALUES
        -- TRASPORTI
        (1, 'trasporti', 'camion_generico', 'kg CO2eq/tkm', 0.149, 0.0000446, 0.0000726, 0.14870955661),
        (2, 'trasporti', 'trattore', 'kg CO2eq/tkm', 0.385, 0.000328, 0.000661, 0.38554700566),

        -- ENERGIA
        (3, 'energia', 'EE_BT', 'kg CO2eq/kWh', 0.62, 0.000437, 0.000068002629, 0.62056556662),
        (4, 'energia', 'EE_MT', 'kg CO2eq/kWh', 0.641, 0.000430, 0.000052093137, 0.64110542286),
        (5, 'energia', 'calore', 'kg CO2eq/kWh', 0.29183644, 0.000054349638, 0.000035925617, 0.29192671526),
        (6, 'energia', 'metano', 'kg CO2eq/kWh', 0.29780778, 0.00003139685, 0.000034164567, 0.29787334142),
        (7, 'energia', 'LNG', 'kg CO2eq/kWh', 0.37301856, 0.0000213559649, 0.000024002979, 0.37306391894),
        (8, 'energia', 'cogen_EE_BT', 'kg CO2eq/kWh', 0.00550425301323034, 0.00500826530389773, 0, 0.01051251832),
        (9, 'energia', 'cogen_EE_MT', 'kg CO2eq/kWh', 0.005370896117, 0.004886925185, 0, 0.01025782130),

        -- IMPIANTO
        (10, 'impianto', 'olio_lubrificante', 'kg CO2eq/kg', 1.7753987, 0.0013156124, 0.0011052098, 1.77781952220),
        (11, 'impianto', 'rifiuti_recupero', 'kg CO2eq/kg', 0, 0, 0, 0.00000000000),
        (12, 'impianto', 'acqua', 'kg CO2eq/mc', 0.3009549, 0.00057622011, 0.00057831189, 0.30210943200),
        (13, 'impianto', 'scarichi', 'kg CO2eq/mc', 0.25789571, 0.061163242, 0.00028924199, 0.31934819399),

        -- ALTRO
        (14, 'altro', 'CO2_biogenica', 'kg CO2eq/unit', 0.7358888, 0.0010055334, 0.00049190182, 0.73738623522),
        (15, 'altro', 'digestato', 'kg CO2eq/tonSS', 0, 16.71, 0, 16.71),
        (16, 'altro', 'pollina', 'kg CO2eq/ton', 3.5121335, 0.00069309774, 0.01019444, 3.52302103774);
    ''')

    conn.commit()
    conn.close()