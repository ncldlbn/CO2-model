
import sqlite3
from collections import defaultdict
from math import ceil, exp, log
import pandas as pd

class Allevatore:
    def __init__(
        self,
        id_allevatore: int,
        denominazione_sociale: str,
        id_impianto_associato: int,
        tipo_conferimento: str,
        frequenza_conferimento_let: int,
        frequenza_conferimento_liq: int,
        id_trasporto: int,
        distanza_impianto: float,
        uba_letame: int,
        uba_liquame: int,
        prod_letame: float,
        prod_liquame: float,
        pollina: float, 
        quota: int = None,
        portata: float = None,
        potenza: float = None,
        ore: int = None
    ):
        # Assegno attributi
        self.id_allevatore = id_allevatore
        self.denominazione_sociale = denominazione_sociale
        self.id_impianto_associato = id_impianto_associato

        if tipo_conferimento not in ('mezzi', 'tubazione'):
            raise ValueError("tipo_conferimento deve essere 'mezzi' o 'tubazione'")
        self.tipo_conferimento = tipo_conferimento

        self.frequenza_conferimento_let = frequenza_conferimento_let
        self.frequenza_conferimento_liq = frequenza_conferimento_liq
        self.id_trasporto = id_trasporto
        self.distanza_impianto = distanza_impianto
        self.uba_letame = uba_letame
        self.uba_liquame = uba_liquame
        self.prod_letame = prod_letame # mc/UBA/anno
        self.prod_liquame = prod_liquame # mc/UBA/anno
        self.pollina = pollina  # ton/anno
        self.quota = quota

        if tipo_conferimento != 'tubazione':
            self.portata = None
            self.potenza = None
            self.ore = None
        else:
            self.portata = portata
            self.potenza = potenza
            self.ore = ore

        # Altri attributi per il calcolo della CO2
        self.produzione_giornaliera_letame = self.uba_letame * self.prod_letame
        self.produzione_giornaliera_liquame = self.uba_liquame * self.prod_liquame
        self.deposito_let = {}
        self.deposito_liq = {}
        self.deposito = {}
        self.tot_co2eq_let = 0
        self.tot_co2eq_liq = 0
        self.GWP_CH4 = 28
        self.GWP_N2O = 265

    def __repr__(self):
        return (
            f"Allevatore id={self.id_allevatore}, nome={self.denominazione_sociale}, "
            f"tipo_conferimento={self.tipo_conferimento}, impianto_associato={self.id_impianto_associato}, "
            f"freq_conf_let={self.frequenza_conferimento_let}, freq_conf_liq={self.frequenza_conferimento_liq}, "
            f"pollina={self.pollina}"
        )

    @classmethod
    def from_db(cls, db_path, id_allevatore):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id_allevatore, denominazione_sociale, id_impianto_associato,
                   tipo_conferimento, frequenza_conferimento_letame, frequenza_conferimento_liquame, id_trasporto,
                   distanza_impianto, uba_letame, uba_liquame, prod_letame, prod_liquame, pollina,
                   quota, portata, potenza, ore
            FROM allevatore
            WHERE id_allevatore = ?
        """, (id_allevatore,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise ValueError(f"Allevatore con id {id_allevatore} non trovato")

        return cls(*row)

class Impianto:
    def __init__(self, id_impianto, nome, separazione, olio_lubrificante, rifiuti, acqua, scarichi):
        self.id_impianto = id_impianto
        self.nome = nome
        self.separazione = separazione
        self.olio_lubrificante = olio_lubrificante
        self.rifiuti = rifiuti
        self.acqua = acqua
        self.scarichi = scarichi

        # Strutture dati per informazioni aggiuntive
        self.ricetta = []           # lista di dict {tipo, quantita}
        self.energia = defaultdict(dict)  # {categoria: {tipo: valore}}
        self.ricettori = []         # lista di dict {id_ricettore, id_trasporto, tipo, distanza}

    def __repr__(self):
        return f"Impianto id={self.id_impianto}, nome='{self.nome}'"

    @classmethod
    def from_db(cls, db_path, id_impianto):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # --- Tabella impianto ---
        cursor.execute("""
            SELECT id_impianto, nome, separazione, olio_lubrificante, rifiuti, acqua, scarichi
            FROM impianto
            WHERE id_impianto = ?
        """, (id_impianto,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Impianto con id {id_impianto} non trovato")

        imp = cls(*row)

        # --- Tabella ricetta_impianto ---
        cursor.execute("""
            SELECT tipo, quantita
            FROM ricetta_impianto
            WHERE id_impianto = ?
        """, (id_impianto,))
        for tipo, quantita in cursor.fetchall():
            imp.ricetta.append({'tipo': tipo, 'quantita': quantita})

        # --- Tabella bilancio_energetico ---
        cursor.execute("""
            SELECT categoria, tipo, valore
            FROM bilancio_energetico
            WHERE id_impianto = ?
        """, (id_impianto,))
        for categoria, tipo, valore in cursor.fetchall():
            imp.energia[categoria][tipo] = valore

        # --- Tabella ricettori ---
        cursor.execute("""
            SELECT id_ricettore, id_trasporto, tipo, distanza
            FROM ricettori
            WHERE id_impianto = ?
        """, (id_impianto,))
        for id_ricettore, id_trasporto, tipo, distanza in cursor.fetchall():
            imp.ricettori.append({
                'id_ricettore': id_ricettore,
                'id_trasporto': id_trasporto,
                'tipo': tipo,
                'distanza': distanza
            })

        conn.close()
        return imp

class Trasporto:
    def __init__(
        self,
        id_trasporto: int,
        tipo: str,
        db_path: str,
        capacita_max: float = None
    ):
        self.id_trasporto = id_trasporto
        self.tipo = tipo
        self.db_path = db_path
        self.capacita_max = capacita_max
        self.tot_co2 = 0
        self.EF = self._assegna_ef_da_db()

    def _assegna_ef_da_db(self):
        """Recupera il fattore di emissione dalla tabella fattori_emissione"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT CO2_TOT 
            FROM fattori_emissione 
            WHERE categoria = 'trasporti' AND nome = ?
        """, (self.tipo,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise ValueError(
                f"Fattore di emissione non trovato per categoria 'trasporti' e tipo '{self.tipo}'"
            )

        return row[0]

    def __repr__(self):
        return (
            f"Trasporto id={self.id_trasporto}, tipo={self.tipo}, EF={self.EF}, "
            f"capacita_max={self.capacita_max}"
        )

    @classmethod
    def from_db(cls, db_path, id_trasporto):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id_trasporto, tipo, capacita_max
            FROM trasporti
            WHERE id_trasporto = ?
        """, (id_trasporto,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise ValueError(f"Trasporto con id {id_trasporto} non trovato")

        return cls(
            id_trasporto=row[0],
            tipo=row[1],
            db_path=db_path,
            capacita_max=row[2]
        )


class FattoriEmissione:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._carica_fattori()

    def _carica_fattori(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT nome, CO2_TOT
            FROM fattori_emissione
        """)

        # Assegna direttamente i valori float come attributi
        for nome, totale in cursor.fetchall():
            setattr(self, nome, totale)

        conn.close()

    def __repr__(self):
        return f"FattoriEmissione(db_path='{self.db_path}')"

    def __getitem__(self, nome):
        """Permette l'accesso come dizionario: fattori['camion_generico']"""
        return getattr(self, nome, None)

    def get(self, nome, default=None):
        """Metodo get simile ai dizionari"""
        return getattr(self, nome, default)

