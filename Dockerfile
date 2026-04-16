# Schlankes Python-Image als Basis
FROM python:3.13-slim

# Arbeitsverzeichnis im Container
WORKDIR /app

# Abh채ngigkeiten kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Den Code kopieren
COPY app.py .

# Port 5001 freigeben
EXPOSE 5001

# App starten
CMD ["python", "app.py"]
