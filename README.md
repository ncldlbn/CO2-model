## Virtual environment

Aprire il terminale nella cartella del progetto e digitare
```
py -m venv venv
```

Attivare il venv
```
.\venv\Scripts\Activate.ps1
```

se powershell blocca l'esecuzione degli script .ps1 digitare: 
```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Installare le dipendenze nel venv
Una volta attivato il venv digitare nel terminale
```
pip install -r requirements.txt
```

## Eseguire il programma

Dalla directory principale del progetto aprire il terminale e digitare
```
streamlit run dashboard\Home.py
```

La dashboard si aprirà all'indirizzo `http://localhost:8501/`