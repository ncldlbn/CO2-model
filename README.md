# CO2-model

Dashboard [Streamlit](https://streamlit.io/) per il calcolo del **bilancio di
CO₂ equivalente** di un impianto di biogas/biometano alimentato a biomasse
agricole e zootecniche.

L'applicazione permette di:

- gestire l'anagrafica di **impianti**, **allevatori/conferitori**,
  **ricettori** e **mezzi di trasporto**;
- configurare i **fattori di emissione** usati nei calcoli;
- eseguire una **simulazione** che produce il bilancio di CO₂eq (emissioni
  evitate da biomasse, emissioni di impianto, digestato e trasporti) con
  esportazione dei risultati in **PDF** ed **Excel**.

---

## Struttura del progetto

```
co2-model/
├── dashboard/
│   ├── Home.py                     # pagina iniziale dell'app
│   ├── db.py                       # connessione al database SQLite
│   └── pages/                      # pagine della dashboard (multi-page Streamlit)
│       ├── 1_📊_Simulazione_CO2.py
│       ├── 2_♻️_Impianti.py
│       ├── 3_🚛_Mezzi_di_Trasporto.py
│       ├── 4_🐄_Allevamenti.py
│       └── 5_⚙️_Fattori_di_Emissione.py
├── src/
│   ├── config.py                   # costanti e parametri del modello
│   ├── objects.py                  # classi di dominio (Allevatore, Impianto, ...)
│   └── model.py                    # funzioni di calcolo della CO₂eq
├── setup/
│   └── dbinit.sql                  # schema + dati iniziali del database
├── data.db                         # database SQLite (creato/popolato dai dati)
├── requirements.txt
└── README.md
```

I parametri numerici del modello (GWP, parametri empirici delle emissioni da
deposito, parametri di processo del digestato, mezzi di default) sono
centralizzati in [`src/config.py`](src/config.py).

---

## Prerequisiti

- **Python 3.10+**
- `pip`
- Facoltativo: `sqlite3` da riga di comando, per (ri)creare il database da zero.

---

## Installazione

Aprire un terminale nella cartella del progetto.

### 1. Creare l'ambiente virtuale

**Windows (PowerShell)**

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

> Se PowerShell blocca l'esecuzione degli script `.ps1`, sbloccarla per la
> sessione corrente:
>
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

**Windows (Prompt dei comandi `cmd`)**

```bat
py -m venv venv
venv\Scripts\activate.bat
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Installare le dipendenze

Con l'ambiente virtuale attivo:

```bash
pip install -r requirements.txt
```

---

## Database

Il repository include già un file `data.db` pronto all'uso, quindi normalmente
**non è necessario alcun passaggio**.

Per ricreare un database vuoto e popolato con i dati di base (mezzi di trasporto
e fattori di emissione), usare lo schema in [`setup/dbinit.sql`](setup/dbinit.sql),
che è l'unica fonte di verità dello schema:

**Windows (PowerShell)**

```powershell
Get-Content setup\dbinit.sql | sqlite3 data.db
```

**Linux / macOS**

```bash
sqlite3 data.db < setup/dbinit.sql
```

---

## Esecuzione

Dalla cartella principale del progetto, con l'ambiente virtuale attivo:

**Windows**

```powershell
streamlit run dashboard/Home.py
```

**Linux / macOS**

```bash
streamlit run dashboard/Home.py
```

La dashboard si aprirà automaticamente nel browser all'indirizzo
`http://localhost:8501/`.

> Nota: il percorso `dashboard/Home.py` con la barra `/` funziona sia su Windows
> sia su Linux/macOS.

---

## Utilizzo

1. **⚙️ Fattori di Emissione** — verificare/aggiornare i fattori di emissione
   usati nei calcoli.
2. **🚛 Mezzi di Trasporto** — controllare i fattori di emissione dei mezzi.
3. **♻️ Impianti** — creare un impianto, definire bilancio energetico,
   conferitori e ricettori.
4. **🐄 Allevamenti** — registrare gli allevatori/conferitori e associarli a un
   impianto.
5. **📊 Simulazione CO2** — selezionare un impianto ed eseguire la simulazione;
   i risultati sono scaricabili in PDF ed Excel.

---

## Note sulle unità di misura

- Le **biomasse** e il **digestato** sono espressi in `ton/anno`.
- I **fattori di emissione** dei trasporti sono in `kg CO₂eq/tkm`.
- Le funzioni di calcolo restituiscono la CO₂ in `kg CO₂eq`; nella
  visualizzazione finale i valori sono convertiti in `ton CO₂eq/anno`.
- Convenzione di segno: i valori **positivi** rappresentano emissioni, i valori
  **negativi** rappresentano emissioni evitate o rimozioni.
