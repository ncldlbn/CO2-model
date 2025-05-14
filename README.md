Build the image
```
docker build -t co2-streamlit-app .
```

Run
```
docker run -p 8501:8501 co2-streamlit-app
```

App is accessible in your browser
```
http://localhost:8501
```