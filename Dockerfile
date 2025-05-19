FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

# Comando per eseguire l'app Streamlit
CMD ["streamlit", "run", "app.py"]
