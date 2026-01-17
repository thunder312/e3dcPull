# E3DC Solar Dashboard

Ein modernes Web-Dashboard zur Visualisierung von E3DC Solar-Energiedaten mit verschlüsselter Credential-Speicherung.

## Features

- 📊 **Live-Datenvisualisierung** - Echtzeit-Anzeige von PV-Leistung, Batteriestand, Netz und Verbrauch
- 📈 **Historische Daten** - Analyse vergangener Zeiträume mit interaktiven Charts
- 🔐 **Verschlüsselte Credentials** - Sichere Speicherung Ihrer E3DC-Zugangsdaten mit Master-Passwort
- 🌐 **Web-basiert** - Zugriff über Browser, keine Desktop-Installation nötig
- 📱 **Responsive Design** - Funktioniert auf Desktop, Tablet und Smartphone
- 🔄 **CSV Import/Export** - Daten importieren und exportieren

## Sicherheit

Ihre E3DC-Zugangsdaten werden:
- Mit **Fernet-Verschlüsselung** (AES-128) gespeichert
- Mit **PBKDF2-HMAC-SHA256** Key-Derivation geschützt
- Durch Ihr persönliches **Master-Passwort** gesichert
- Niemals im Klartext in Dateien gespeichert

## Installation

### Voraussetzungen

- Python 3.8 oder höher
- pip (Python Package Manager)

### Schritt 1: Repository klonen

```bash
git clone https://github.com/IHR-USERNAME/e3dcPull.git
cd e3dcPull
```

### Schritt 2: Dependencies installieren

```bash
pip install -r requirements.txt
```

Das installiert:
- Flask (Webserver)
- cryptography (Verschlüsselung)
- requests (E3DC API)

### Schritt 3: Konfiguration (Optional)

Die Standard-Konfiguration funktioniert bereits. Falls Sie Anpassungen vornehmen möchten:

```bash
# config.json.example kopieren
cp config.json.example config.json

# Dann config.json bearbeiten (Port, etc.)
```

**Wichtig:** Fügen Sie KEINE Zugangsdaten in `config.json` ein! Diese werden später über die Web-Oberfläche verschlüsselt gespeichert.

## Erste Nutzung

### Server starten

```bash
python web_server.py
```

Der Server:
- Startet auf `http://localhost:5000`
- Öffnet automatisch Ihren Browser
- Zeigt die Setup-Seite an

### Einrichtung (Setup)

Beim ersten Start sehen Sie die **Setup-Seite**:

1. **E3DC Benutzername** eingeben (Ihre E-Mail für my.e3dc.com)
2. **E3DC Passwort** eingeben
3. **Dashboard URL** eingeben (z.B. `https://my.e3dc.com/dashboard/overview/...`)
4. **Master-Passwort erstellen** (mindestens 8 Zeichen)
5. **Master-Passwort bestätigen**
6. Auf **"Einrichten und Speichern"** klicken

Fertig! Ihre Zugangsdaten sind jetzt verschlüsselt in `.credentials.enc` gespeichert.

### Dashboard URL finden

1. Gehen Sie zu [my.e3dc.com](https://my.e3dc.com)
2. Loggen Sie sich ein
3. Öffnen Sie Ihr Dashboard
4. Kopieren Sie die URL aus der Adressleiste
   - Format: `https://my.e3dc.com/dashboard/overview/SYSTEM_ID/SERIAL`

## Tägliche Nutzung

### Server starten

```bash
python web_server.py
```

### Login

1. Browser öffnet automatisch
2. **Master-Passwort** eingeben
3. Auf **"Entsperren"** klicken
4. Dashboard wird geladen

### Logout

Klicken Sie oben rechts auf **"Abmelden"** um die Session zu beenden.

## Funktionen

### Zeitraum auswählen

1. **Von/Bis-Datum** auswählen
2. **"Daten laden"** klicken
3. Daten werden vom E3DC-Portal abgerufen

### CSV hochladen

1. Klicken Sie auf **"CSV/JSON Datei hochladen"**
2. Oder ziehen Sie eine Datei per Drag & Drop
3. Daten werden im Dashboard visualisiert

### Daten exportieren

Klicken Sie auf **"CSV speichern"** um die aktuellen Daten zu exportieren.

### Zeitraum-Filter

Nutzen Sie die Buttons:
- **1 Tag** - Letzte 24 Stunden
- **7 Tage** - Letzte Woche
- **30 Tage** - Letzter Monat
- **Alle** - Gesamter Zeitraum

### Zoom & Pan

- **Mausrad** - Zoomen in Charts
- **Ziehen** - Verschieben der Ansicht
- **Zoom zurücksetzen** - Originalansicht wiederherstellen

## Zugangsdaten zurücksetzen

### Über die Web-Oberfläche

1. Auf der Login-Seite: **"Zugangsdaten zurücksetzen"** klicken
2. Bestätigen
3. Neue Zugangsdaten + Master-Passwort eingeben

### Master-Passwort vergessen

Falls Sie Ihr Master-Passwort vergessen haben:

```bash
# Verschlüsselte Datei löschen
rm .credentials.enc

# Server neu starten
python web_server.py
```

Sie müssen dann Ihre E3DC-Zugangsdaten neu eingeben.

## Für Entwickler

### Projekt-Struktur

```
e3dcPull/
├── web_server.py           # Flask-Webserver
├── credential_manager.py   # Verschlüsselungs-Logik
├── e3dc_fetch.py          # E3DC API-Client
├── login.html             # Login-Seite
├── index.html             # Dashboard
├── js/
│   └── app.js            # Dashboard-Logik
├── css/
│   └── style.css         # Dashboard-Styling
├── static/
│   └── css/
│       └── login.css     # Login-Styling
├── data/                  # CSV-Daten (automatisch erstellt)
├── config.json           # Konfiguration (nicht in Git!)
├── config.json.example   # Template
├── .credentials.enc      # Verschlüsselte Credentials (nicht in Git!)
└── requirements.txt      # Python-Dependencies
```

### API-Endpoints

Der Webserver stellt folgende Endpoints bereit:

**Seiten:**
- `GET /` - Redirect zu Login oder Dashboard
- `GET /login` - Login-Seite
- `GET /dashboard` - Dashboard (authentifiziert)

**Credential-Management:**
- `GET /api/credentials/status` - Prüft ob Credentials existieren
- `POST /api/credentials/setup` - Erstmaliges Speichern von Credentials
- `POST /api/credentials/unlock` - Entsperren mit Master-Passwort
- `POST /api/credentials/reset` - Credentials löschen

**Daten:**
- `GET /api/data/live` - Aktuelle Live-Daten vom E3DC-Portal
- `GET /api/data/history?start_date=...&end_date=...&resolution=...` - Historische Daten
- `POST /api/logout` - Session beenden

### Konfiguration

In `config.json`:

```json
{
  "output": {
    "csv_folder": "data",
    "csv_filename": "e3dc_data.csv"
  },
  "server": {
    "host": "localhost",
    "port": 5000,
    "auto_open_browser": true
  }
}
```

## Troubleshooting

### Port bereits belegt

```bash
# In config.json den Port ändern
{
  "server": {
    "port": 5001
  }
}
```

### Dependencies fehlen

```bash
pip install -r requirements.txt
```

### Browser öffnet nicht automatisch

```bash
# In config.json deaktivieren
{
  "server": {
    "auto_open_browser": false
  }
}

# Dann manuell öffnen: http://localhost:5000
```

### Migration von alter Version

Falls Sie eine alte Version mit Credentials in `config.json` haben:

1. Server starten: `python web_server.py`
2. Setup-Seite zeigt vorausgefüllte Felder
3. Master-Passwort erstellen
4. Speichern
5. `config.json` wird automatisch bereinigt (Backup: `config.json.bak`)

## Sicherheitshinweise

### Was Sie in Git committen sollten

✅ **Committen:**
- `config.json.example`
- `requirements.txt`
- `*.py`, `*.html`, `*.js`, `*.css`
- `.gitignore`
- `README.md`

❌ **NICHT committen:**
- `config.json` (enthält ggf. noch alte Credentials)
- `.credentials.enc` (verschlüsselte Zugangsdaten)
- `data/` (CSV-Daten)
- `__pycache__/`

Die `.gitignore` ist bereits korrekt konfiguriert!

### Backup

Wenn Sie Ihre verschlüsselten Zugangsdaten sichern möchten:

```bash
# Backup erstellen
cp .credentials.enc .credentials.enc.backup

# Wiederherstellen
cp .credentials.enc.backup .credentials.enc
```

**Wichtig:** Das Backup ist nur mit Ihrem Master-Passwort nutzbar!

### Master-Passwort

- Mindestens 8 Zeichen
- Speichern Sie es in einem Passwort-Manager
- Keine Wiederherstellung möglich bei Verlust
- Wird niemals gespeichert oder übertragen

## Lizenz

MIT License - siehe LICENSE Datei

## Support

Bei Fragen oder Problemen:
- Überprüfen Sie die Server-Logs in der Konsole
- Prüfen Sie ob alle Dependencies installiert sind
- Stellen Sie sicher, dass Port 5000 verfügbar ist

## Changelog

### v2.0.0 - Sicherheitsupdate
- ✅ Verschlüsselte Credential-Speicherung
- ✅ Web-basierte Login-Oberfläche
- ✅ Flask-Webserver
- ✅ Master-Passwort-Schutz
- ✅ Automatische Migration
- ✅ Session-Management
- ✅ Logout-Funktion
- ✅ Modernes Dashboard-Design

### v1.0.0 - Initial Release
- ✅ Basis-Dashboard
- ✅ CSV Import/Export
- ✅ E3DC API-Integration
