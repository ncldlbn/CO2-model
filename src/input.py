import sqlite3

def inserisci_allevatore(db_path, dati: dict):
    """
    Inserisce un nuovo allevatore nel database a partire da un dizionario.
    
    Parametri:
        db_path (str): percorso del database SQLite
        dati (dict): dizionario con chiavi:
            {
                "denominazione_sociale": <string>,
                "id_impianto_associato": <int>,
                "tipo_conferimento": <'mezzi' o 'tubazione'>,
                "frequenza_conferimento": <int>,
                "id_trasporto": <int>,
                "distanza_impianto": <float>,
                "uba_letame": <int>,
                "uba_liquame": <int>,
                "prod_letame": <float>,
                "prod_liquame": <float>,
                "deposito_max": <float>,
                "quota": <int opzionale>,
                "portata": <float, solo se tipo_conferimento='tubazione'>,
                "potenza": <float, solo se tipo_conferimento='tubazione'>,
                "ore": <int, solo se tipo_conferimento='tubazione'>
            }
    """
    tipo = dati.get('tipo_conferimento')
    if tipo not in ('mezzi', 'tubazione'):
        raise ValueError("tipo_conferimento deve essere 'mezzi' o 'tubazione'")

    # Se non è tubazione, forziamo portata, potenza e ore a None
    if tipo != 'tubazione':
        dati['portata'] = None
        dati['potenza'] = None
        dati['ore'] = None

    # Connessione al database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO allevatore (
            denominazione_sociale, id_impianto_associato, tipo_conferimento,
            frequenza_conferimento, id_trasporto, distanza_impianto,
            uba_letame, uba_liquame, prod_letame, prod_liquame,
            deposito_max, quota, portata, potenza, ore
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dati.get('denominazione_sociale'),
        dati.get('id_impianto_associato'),
        tipo,
        dati.get('frequenza_conferimento'),
        dati.get('id_trasporto'),
        dati.get('distanza_impianto'),
        dati.get('uba_letame'),
        dati.get('uba_liquame'),
        dati.get('prod_letame'),
        dati.get('prod_liquame'),
        dati.get('deposito_max'),
        dati.get('quota'),
        dati.get('portata'),
        dati.get('potenza'),
        dati.get('ore')
    ))

    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def inserisci_trasporto(db_path, dati: dict):
    """
    Inserisce un nuovo trasporto nel database a partire da un dizionario.
    
    Parametri:
        db_path (str): percorso del database SQLite
        dati (dict): dizionario con chiavi:
        {
            "tipo": <string>,           # es. 'camion', 'trattore', 'tubazione'
            "EF": <float>,              # fattore di emissione
            "capacita_max": <float opzionale>
        }
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO trasporti (
            tipo, EF, capacita_max
        ) VALUES (?, ?, ?)
    """, (
        dati.get('tipo'),
        dati.get('EF'),
        dati.get('capacita_max')
    ))

    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


import sqlite3

def inserisci_impianto(db_path, dati: dict):
    """
    Inserisce un impianto e tutte le informazioni correlate nel database.
    
    Parametri:
        db_path (str): percorso del database SQLite
        dati (dict): dizionario con chiavi:
        {
            "dati_generali": {
                "nome": <string>,
                "deposito_max": <float>,
                "Qout_liq": <float>,
                "Qout_let": <float>,
                "separazione": <bool>
            },
            "ricetta": [
                {"tipo": <string>, "quantita": <float>},  # lista di sottoprodotti/biomassa
            ],
            "bilancio_energetico": {
                "prodotta": {
                    "EE_BT": <float>,
                    "EE_MT": <float>,
                    "calore": <float>,
                    "biometano": <float>,
                    "bioLNG": <float>,
                    "CO2_biogenica": <float>
                },
                "autoconsumata": {
                    "EE": <float>,
                    "EE_trasporti_tubazioni": <float>,
                    "calore": <float>,
                    "biometano": <float>,
                    "bioLNG": <float>
                },
                "acquistata": {
                    "EE_BT": <float>,
                    "EE_MT": <float>,
                    "metano": <float>,
                    "LNG": <float>
                }
            },
            "ricettori": [
                {"id_ricettore": <int>, "id_trasporto": <int>, "tipo": <string>, "distanza": <float>}
            ]
        }
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1️⃣ Inserimento dati generali impianto
    generali = dati['dati_generali']
    cursor.execute("""
        INSERT INTO impianto (nome, deposito_max, Qout_liq, Qout_let, separazione)
        VALUES (?, ?, ?, ?, ?)
    """, (
        generali.get('nome'),
        generali.get('deposito_max'),
        generali.get('Qout_liq'),
        generali.get('Qout_let'),
        generali.get('separazione')
    ))
    id_impianto = cursor.lastrowid

    # 2️⃣ Inserimento ricetta_impianto
    for r in dati.get('ricetta', []):
        cursor.execute("""
            INSERT INTO ricetta_impianto (id_impianto, tipo, quantita)
            VALUES (?, ?, ?)
        """, (id_impianto, r['tipo'], r['quantita']))

    # 3️⃣ Inserimento bilancio_energetico
    for categoria, tipi in dati.get('bilancio_energetico', {}).items():
        for tipo, valore in tipi.items():
            cursor.execute("""
                INSERT INTO bilancio_energetico (id_impianto, categoria, tipo, valore, unita)
                VALUES (?, ?, ?, ?, 'kWh')
            """, (id_impianto, categoria, tipo, valore))

    # 4️⃣ Inserimento ricettori
    for rec in dati.get('ricettori', []):
        cursor.execute("""
            INSERT INTO ricettori (id_ricettore, id_impianto, id_trasporto, tipo, distanza)
            VALUES (?, ?, ?, ?, ?)
        """, (
            rec['id_ricettore'],
            id_impianto,
            rec['id_trasporto'],
            rec['tipo'],
            rec['distanza']
        ))

    conn.commit()
    conn.close()
    return id_impianto


