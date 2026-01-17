# Git Setup - Projekt veröffentlichen

Diese Anleitung zeigt, wie Sie das E3DC Solar Dashboard sicher auf Git hochladen.

## Schritt 1: Credentials aus config.json entfernen

**Wichtig:** Ihre `config.json` enthält möglicherweise noch Zugangsdaten im Klartext (für Migration).

### Prüfen Sie Ihre config.json

Öffnen Sie `config.json` und prüfen Sie, ob ein `"e3dc"`-Bereich vorhanden ist:

```json
{
  "e3dc": {
    "username": "ihre.email@example.com",
    "password": "IhrPasswort",
    "dashboard_url": "..."
  },
  ...
}
```

### Falls vorhanden: Bereinigen

**Option 1: Automatische Bereinigung (Empfohlen)**

1. Server starten: `python web_server.py`
2. Login-Seite öffnet sich
3. Master-Passwort eingeben oder neu erstellen
4. Die `config.json` wird automatisch bereinigt
5. Ein Backup wird erstellt: `config.json.bak`

**Option 2: Manuelle Bereinigung**

Ersetzen Sie den Inhalt von `config.json` mit:

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

## Schritt 2: .gitignore prüfen

Die `.gitignore` sollte folgende Einträge enthalten (bereits vorhanden):

```gitignore
# E3DC Credentials - NIEMALS commiten!
config.json
config.json.bak

# Encrypted credentials
.credentials.enc
.credentials.enc.backup

# Downloaded data
data/

# Python
__pycache__/
*.pyc
.venv/
venv/
```

## Schritt 3: Git initialisieren (falls noch nicht geschehen)

```bash
# Git-Repository initialisieren
git init

# Alle Dateien zum Staging hinzufügen
git add .

# Ersten Commit erstellen
git commit -m "Initial commit: E3DC Solar Dashboard v2.0"
```

## Schritt 4: Prüfen, was committet wird

**Wichtig:** Prüfen Sie, ob keine sensiblen Daten committet werden!

```bash
# Zeigt alle Dateien, die committet werden
git status

# Prüfen Sie speziell diese Dateien:
git status | grep config.json           # sollte NICHT erscheinen
git status | grep .credentials.enc      # sollte NICHT erscheinen
git status | grep data/                 # sollte NICHT erscheinen
```

## Schritt 5: Remote Repository verbinden

### Auf GitHub/GitLab/etc.

1. Erstellen Sie ein neues Repository auf GitHub/GitLab
2. Kopieren Sie die Repository-URL

### Lokal verbinden

```bash
# Remote hinzufügen
git remote add origin https://github.com/IHR-USERNAME/e3dcPull.git

# Pushen
git push -u origin main
```

## Schritt 6: README aktualisieren

Bearbeiten Sie `README.md` und passen Sie an:

- Ersetzen Sie `https://github.com/IHR-USERNAME/e3dcPull.git` mit Ihrer echten URL
- Fügen Sie ggf. Screenshots hinzu
- Passen Sie die Lizenz an

## Checkliste vor dem Push

- [ ] `config.json` enthält KEINE Credentials
- [ ] `.credentials.enc` ist in `.gitignore`
- [ ] `data/` Ordner ist in `.gitignore`
- [ ] `config.json.example` existiert
- [ ] `README.md` ist aktuell
- [ ] Dependencies in `requirements.txt` sind korrekt
- [ ] `.gitignore` ist vollständig

## Für neue Benutzer

Wenn andere Personen Ihr Projekt klonen:

### Setup für neue Benutzer

```bash
# 1. Repository klonen
git clone https://github.com/IHR-USERNAME/e3dcPull.git
cd e3dcPull

# 2. Dependencies installieren
pip install -r requirements.txt

# 3. Server starten
python web_server.py

# 4. Browser öffnet automatisch mit Setup-Seite
# 5. Eigene E3DC-Zugangsdaten + Master-Passwort eingeben
# 6. Fertig!
```

**Das war's!** Neue Benutzer müssen:
- Keine Konfigurationsdateien bearbeiten
- Keine config.json erstellen
- Einfach nur den Server starten
- Ihre Zugangsdaten im Browser eingeben

## Wichtige Hinweise

### config.json vs config.json.example

- **config.json** - Wird NICHT in Git eingecheckt (enthält ggf. alte Credentials)
- **config.json.example** - Template für neue Benutzer (WIRD eingecheckt)

Neue Benutzer brauchen `config.json` NICHT zu erstellen. Der Server funktioniert auch ohne und verwendet Standard-Werte.

### Migration für neue Benutzer

Neue Benutzer haben KEINE alte `config.json` mit Credentials:
1. Sie starten den Server: `python web_server.py`
2. Die Setup-Seite erscheint (leer, keine vorausgefüllten Felder)
3. Sie geben ihre E3DC-Zugangsdaten ein
4. Sie erstellen ein Master-Passwort
5. Fertig!

## Sicherheit

### Was passiert mit Zugangsdaten?

Neue Benutzer geben ihre Zugangsdaten über die **Web-Oberfläche** ein:
- Werden sofort verschlüsselt
- Gespeichert in `.credentials.enc` (lokal, nicht in Git)
- Niemals im Klartext in Dateien
- Geschützt durch ihr persönliches Master-Passwort

### Jeder Benutzer hat eigene Credentials

- Jeder erstellt seine eigene `.credentials.enc`
- Jeder wählt sein eigenes Master-Passwort
- Keine gemeinsamen Zugangsdaten
- Vollständig isoliert

## Zusammenfassung

✅ **Für Sie (Entwickler):**
1. `config.json` bereinigen (keine Credentials)
2. Git Push
3. Fertig!

✅ **Für neue Benutzer:**
1. `git clone`
2. `pip install -r requirements.txt`
3. `python web_server.py`
4. Zugangsdaten im Browser eingeben
5. Fertig!

**Das System ist bereits perfekt vorbereitet für die Veröffentlichung!** 🎉
