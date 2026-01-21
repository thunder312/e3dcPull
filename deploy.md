# Deployment auf Linux-Server

Diese Anleitung beschreibt verschiedene Optionen, um das E3DC Solar Dashboard auf einem Linux-Server zu deployen.

## Option 1: Systemd + Gunicorn (Empfohlen für Produktion)

Diese Methode bietet die beste Performance und Stabilität für den Dauerbetrieb.

### 1. Abhängigkeiten installieren

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx
```

### 2. Projekt kopieren und Virtual Environment erstellen

```bash
# Projekt in /opt kopieren
sudo mkdir -p /opt/e3dcPull
sudo cp -r . /opt/e3dcPull/
cd /opt/e3dcPull

# Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

### 3. WSGI-Entry-Point erstellen

Erstelle die Datei `/opt/e3dcPull/wsgi.py`:

```python
from web_server import app

if __name__ == "__main__":
    app.run()
```

### 4. Systemd-Service erstellen

Erstelle `/etc/systemd/system/e3dc.service`:

```ini
[Unit]
Description=E3DC Solar Dashboard
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/e3dcPull
Environment="PATH=/opt/e3dcPull/venv/bin"
Environment="FLASK_SECRET_KEY=DEIN_SICHERER_KEY_HIER"
ExecStart=/opt/e3dcPull/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Wichtig:** Ersetze `DEIN_SICHERER_KEY_HIER` durch einen sicheren, zufälligen String:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Berechtigungen setzen

```bash
sudo chown -R www-data:www-data /opt/e3dcPull
sudo chmod -R 755 /opt/e3dcPull
```

### 6. Nginx als Reverse-Proxy konfigurieren

Erstelle `/etc/nginx/sites-available/e3dc`:

```nginx
server {
    listen 80;
    server_name deine-domain.de;  # oder Server-IP

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Statische Dateien direkt ausliefern (optional, verbessert Performance)
    location /static/ {
        alias /opt/e3dcPull/static/;
        expires 1d;
    }
}
```

### 7. Aktivieren und starten

```bash
# Nginx-Site aktivieren
sudo ln -s /etc/nginx/sites-available/e3dc /etc/nginx/sites-enabled/
sudo nginx -t  # Konfiguration testen
sudo systemctl restart nginx

# Systemd-Service aktivieren und starten
sudo systemctl daemon-reload
sudo systemctl enable e3dc
sudo systemctl start e3dc

# Status prüfen
sudo systemctl status e3dc
```

### 8. HTTPS mit Let's Encrypt (empfohlen)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d deine-domain.de
```

---

## Option 2: Docker

Ideal für isolierte Umgebungen und einfache Portabilität.

### Dockerfile erstellen

Erstelle `Dockerfile` im Projektverzeichnis:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Anwendung kopieren
COPY . .

# Umgebungsvariablen
ENV FLASK_SECRET_KEY=change-me-in-production

# Port freigeben
EXPOSE 5000

# Gunicorn starten
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "web_server:app"]
```

### Docker Compose (optional)

Erstelle `docker-compose.yml`:

```yaml
version: '3.8'

services:
  e3dc:
    build: .
    container_name: e3dc-dashboard
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
      - ./config.json:/app/config.json:ro
      - ./.credentials.enc:/app/.credentials.enc
    environment:
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
```

### Container bauen und starten

```bash
# Mit Docker
docker build -t e3dc-dashboard .
docker run -d \
  --name e3dc \
  --restart unless-stopped \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.credentials.enc:/app/.credentials.enc \
  -e FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))") \
  e3dc-dashboard

# Mit Docker Compose
export FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
docker-compose up -d
```

---

## Option 3: Einfacher Betrieb (nur für Tests/Entwicklung)

Nicht für Produktion empfohlen, aber schnell eingerichtet.

```bash
# Projekt klonen
git clone <repo-url> /opt/e3dcPull
cd /opt/e3dcPull

# Dependencies installieren
pip3 install -r requirements.txt

# config.json anpassen
cat > config.json << 'EOF'
{
  "output": {
    "csv_folder": "data",
    "csv_filename": "e3dc_data.csv"
  },
  "server": {
    "host": "0.0.0.0",
    "port": 5000,
    "auto_open_browser": false
  }
}
EOF

# Mit nohup im Hintergrund starten
nohup python3 web_server.py > e3dc.log 2>&1 &
```

---

## Wichtige Konfigurationsanpassungen

### config.json für Server-Betrieb

```json
{
  "output": {
    "csv_folder": "data",
    "csv_filename": "e3dc_data.csv"
  },
  "server": {
    "host": "0.0.0.0",
    "port": 5000,
    "auto_open_browser": false
  }
}
```

| Einstellung | Lokal | Server |
|-------------|-------|--------|
| `host` | `localhost` | `0.0.0.0` |
| `auto_open_browser` | `true` | `false` |

### Sicherheitsempfehlungen

1. **FLASK_SECRET_KEY**: Immer als Umgebungsvariable setzen, nie im Code
2. **HTTPS**: Immer SSL/TLS verwenden (Let's Encrypt ist kostenlos)
3. **Firewall**: Nur benötigte Ports öffnen (80, 443)
4. **Updates**: System und Dependencies regelmässig aktualisieren

### Firewall-Regeln (ufw)

```bash
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

---

## Troubleshooting

### Service startet nicht

```bash
# Logs anzeigen
sudo journalctl -u e3dc -f

# Manuell testen
cd /opt/e3dcPull
source venv/bin/activate
gunicorn --bind 127.0.0.1:5000 wsgi:app
```

### Berechtigungsprobleme

```bash
sudo chown -R www-data:www-data /opt/e3dcPull
sudo chmod 600 /opt/e3dcPull/.credentials.enc
```

### Port bereits belegt

```bash
# Prozess finden
sudo lsof -i :5000

# In config.json anderen Port verwenden
```

### Nginx-Fehler

```bash
# Konfiguration testen
sudo nginx -t

# Logs prüfen
sudo tail -f /var/log/nginx/error.log
```

---

## Backup

### Wichtige Dateien sichern

```bash
# Credentials und Daten
cp /opt/e3dcPull/.credentials.enc ~/backup/
cp /opt/e3dcPull/config.json ~/backup/
cp -r /opt/e3dcPull/data/ ~/backup/
```

### Wiederherstellen

```bash
cp ~/backup/.credentials.enc /opt/e3dcPull/
cp ~/backup/config.json /opt/e3dcPull/
cp -r ~/backup/data/ /opt/e3dcPull/
sudo chown -R www-data:www-data /opt/e3dcPull
sudo systemctl restart e3dc
```