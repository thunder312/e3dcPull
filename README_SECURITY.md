# E3DC Solar Dashboard - Sicherheitsupdate

## Überblick

Ihre E3DC-Zugangsdaten werden jetzt **verschlüsselt** gespeichert und sind durch ein Master-Passwort geschützt.

## Neue Architektur

### Vorher
- Zugangsdaten im Klartext in `config.json`
- Direktes Python-Script (`e3dc_fetch.py`)
- Statisches HTML-Dashboard

### Nachher
- **Verschlüsselte Credentials** in `.credentials.enc` (Fernet-Verschlüsselung)
- **Flask-Webserver** mit Login-Seite
- **Master-Passwort** zum Schutz der Zugangsdaten

## Installation

### 1. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 2. Server starten

```bash
python web_server.py
```

Der Server startet auf `http://localhost:5000` und öffnet automatisch Ihren Browser.

## Erste Nutzung (Migration)

Beim ersten Start werden Ihre bestehenden Zugangsdaten aus `config.json` automatisch migriert:

1. **Browser öffnet** Login-Seite automatisch
2. **Setup-Modus** wird angezeigt mit vorausgefüllten Feldern
3. **Master-Passwort** erstellen (mindestens 8 Zeichen)
4. **Speichern** klicken
5. Ihre Zugangsdaten werden verschlüsselt und aus `config.json` entfernt

**Wichtig:** Merken Sie sich Ihr Master-Passwort! Ohne dieses können Ihre Zugangsdaten nicht wiederhergestellt werden.

## Tägliche Nutzung

1. **Server starten:** `python web_server.py`
2. **Master-Passwort eingeben** auf der Login-Seite
3. **Dashboard nutzen** wie gewohnt

## Dateien

### Neu erstellt
- `credential_manager.py` - Verschlüsselungs-Logik
- `web_server.py` - Flask-Webserver
- `login.html` - Login-Seite
- `static/css/login.css` - Login-Styling
- `.credentials.enc` - Verschlüsselte Zugangsdaten (wird beim ersten Login erstellt)

### Geändert
- `e3dc_fetch.py` - Verwendet jetzt Credentials als Parameter
- `config.json` - Enthält keine Zugangsdaten mehr (nach Migration)
- `.gitignore` - Schützt `.credentials.enc` vor Git-Commits

## Sicherheitsfeatures

### Verschlüsselung
- **Fernet** (AES 128-bit) Verschlüsselung
- **PBKDF2-HMAC-SHA256** Key-Derivation
- **100.000 Iterationen** für Brute-Force-Schutz
- **Zufälliges Salt** pro Speicherung

### Speicherung
- Verschlüsselte Datei: `.credentials.enc`
- Nur für Eigentümer lesbar (Unix-Systeme)
- Automatisch in `.gitignore`

### Session-Management
- Server-seitige Sessions (Flask)
- Credentials nur im Speicher während der Session
- Automatisches Logout bei Server-Neustart

## Credential-Verwaltung

### Zugangsdaten zurücksetzen

1. Auf der Login-Seite: Link "**Zugangsdaten zurücksetzen**" klicken
2. Bestätigen
3. Neue Zugangsdaten eingeben

### Manueller Reset

Falls Sie Ihr Master-Passwort vergessen haben:

```bash
# .credentials.enc löschen
rm .credentials.enc

# Server neu starten
python web_server.py
```

Sie müssen Ihre E3DC-Zugangsdaten dann neu eingeben.

## API-Endpoints

Der Webserver stellt folgende Endpoints bereit:

### Seiten
- `/` - Redirect zu Login oder Dashboard
- `/login` - Login-Seite
- `/dashboard` - Dashboard (authentifiziert)

### API
- `GET /api/credentials/status` - Prüft Credential-Status
- `POST /api/credentials/setup` - Erstmaliges Speichern
- `POST /api/credentials/unlock` - Entsperren mit Master-Passwort
- `POST /api/credentials/reset` - Credentials löschen
- `GET /api/data/live` - Live-Daten (authentifiziert)
- `GET /api/data/history` - Historische Daten (authentifiziert)
- `POST /api/logout` - Session beenden

## Konfiguration

In `config.json`:

```json
{
  "server": {
    "host": "localhost",
    "port": 5000,
    "auto_open_browser": true
  },
  "output": {
    "csv_folder": "data",
    "csv_filename": "e3dc_data.csv"
  }
}
```

## Troubleshooting

### Server startet nicht
```bash
# Port bereits belegt? Ändern Sie den Port in config.json
{
  "server": {
    "port": 5001
  }
}
```

### Falsches Master-Passwort
- **Keine Recovery möglich** - Sie müssen die Credentials zurücksetzen
- Löschen Sie `.credentials.enc` und richten Sie neu ein

### Dependencies fehlen
```bash
pip install -r requirements.txt
```

### Browser öffnet nicht automatisch
- URL manuell öffnen: `http://localhost:5000`
- `auto_open_browser` in `config.json` auf `false` setzen

## Backup

### Wichtig für Backups
- **Sichern Sie** `.credentials.enc` **UND** Ihr Master-Passwort
- `.credentials.enc` alleine ist nutzlos ohne Master-Passwort
- Speichern Sie das Master-Passwort in einem Passwort-Manager

### Backup erstellen
```bash
# Verschlüsselte Credentials sichern
cp .credentials.enc .credentials.enc.backup

# Bei Bedarf wiederherstellen
cp .credentials.enc.backup .credentials.enc
```

## Migration rückgängig machen

Falls Sie zum alten System zurückkehren möchten:

1. Backup wiederherstellen: `cp config.json.bak config.json`
2. `.credentials.enc` löschen
3. Altes Script nutzen: `python e3dc_fetch.py`

**Achtung:** Dies ist nicht empfohlen, da Ihre Zugangsdaten dann wieder im Klartext gespeichert sind!

## Support

Bei Fragen oder Problemen:
- Überprüfen Sie die Server-Logs in der Konsole
- Stellen Sie sicher, dass alle Dependencies installiert sind
- Prüfen Sie, ob Port 5000 verfügbar ist

## Changelog

### v2.0.0 - Sicherheitsupdate
- ✅ Verschlüsselte Credential-Speicherung
- ✅ Web-basierte Login-Oberfläche
- ✅ Flask-Webserver
- ✅ Master-Passwort-Schutz
- ✅ Automatische Migration
- ✅ Session-Management
- ✅ Verbesserte Sicherheit
