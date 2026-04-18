# Schlankes Python-Image als Basis
FROM python:3.13-slim

# Arbeitsverzeichnis im Container
WORKDIR /app

# Abhängigkeiten kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Den Code kopieren
COPY app.py .

# Datenverzeichnis erstellen
RUN mkdir -p /data

# Port 5001 freigeben
EXPOSE 5001

# Sicherheit: nicht als root laufen
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app /data
USER appuser

# App starten
CMD ["python", "app.py"]
