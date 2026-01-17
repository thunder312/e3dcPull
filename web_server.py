#!/usr/bin/env python3
"""
Flask Webserver für E3DC Solar Dashboard
Verwaltet Login, Credential-Storage und Data-APIs
"""

import json
import os
import webbrowser
from pathlib import Path
from threading import Timer

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from werkzeug.exceptions import NotFound

from credential_manager import CredentialManager
from e3dc_fetch import E3DCFetcher

# App initialisieren
app = Flask(__name__,
            static_folder='static',
            static_url_path='/static')

# Secret Key für Sessions (sollte in Produktion aus Umgebungsvariable kommen)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# Konfiguration
CONFIG_PATH = Path(__file__).parent / "config.json"
BASE_PATH = Path(__file__).parent

# Global: E3DC Fetcher Instance (wird nach Login initialisiert)
_e3dc_fetcher = None


def load_config():
    """Lädt die Server-Konfiguration"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("server", {
            "host": "localhost",
            "port": 5000,
            "auto_open_browser": True
        })
    return {
        "host": "localhost",
        "port": 5000,
        "auto_open_browser": True
    }


def open_browser(host, port):
    """Öffnet den Browser nach kurzem Delay"""
    url = f"http://{host}:{port}"
    Timer(1.5, lambda: webbrowser.open(url)).start()


# ========== CACHE CONTROL ==========

@app.after_request
def add_cache_control(response):
    """Verhindert Browser-Caching für API-Antworten"""
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


# ========== ROUTES ==========

@app.route('/')
def index():
    """Root-Route: Redirect zu Login oder Dashboard"""
    if 'authenticated' in session and session['authenticated']:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login')
def login():
    """Login-Seite"""
    return send_from_directory(BASE_PATH, 'login.html')


@app.route('/dashboard')
def dashboard():
    """Dashboard (erfordert Authentifizierung)"""
    if 'authenticated' not in session or not session['authenticated']:
        return redirect(url_for('login'))
    return send_from_directory(BASE_PATH, 'index.html')


# ========== API: CREDENTIAL MANAGEMENT ==========

@app.route('/api/credentials/status', methods=['GET'])
def credential_status():
    """
    Prüft ob Credentials existieren und ob Migration verfügbar ist.

    Returns:
        JSON: {
            exists: bool,
            migration_available: bool,
            migration_data: {...} | null
        }
    """
    exists = CredentialManager.credentials_exist()
    migration_data = CredentialManager.migrate_from_config()

    return jsonify({
        "exists": exists,
        "migration_available": migration_data is not None,
        "migration_data": migration_data if migration_data and not exists else None
    })


@app.route('/api/credentials/setup', methods=['POST'])
def credential_setup():
    """
    Speichert neue Credentials (Ersteinrichtung).

    Expects JSON:
        {
            username: str,
            password: str,
            ip_address: str,
            rscp_key: str,
            master_password: str
        }

    Returns:
        JSON: {success: bool, error: str | null}
    """
    try:
        data = request.get_json()

        # Validierung
        required_fields = ['username', 'password', 'ip_address', 'rscp_key', 'master_password']
        if not all(field in data for field in required_fields):
            return jsonify({
                "success": False,
                "error": "Fehlende Felder"
            }), 400

        # Credentials speichern
        success = CredentialManager.save_credentials(
            username=data['username'],
            password=data['password'],
            ip_address=data['ip_address'],
            rscp_key=data['rscp_key'],
            master_password=data['master_password']
        )

        if not success:
            return jsonify({
                "success": False,
                "error": "Fehler beim Speichern der Credentials"
            }), 500

        # Session setzen
        session['authenticated'] = True
        session['credentials'] = {
            "username": data['username'],
            "password": data['password'],
            "ip_address": data['ip_address'],
            "rscp_key": data['rscp_key']
        }

        # E3DC Fetcher initialisieren
        global _e3dc_fetcher
        _e3dc_fetcher = E3DCFetcher(
            username=data['username'],
            password=data['password'],
            ip_address=data['ip_address'],
            rscp_key=data['rscp_key']
        )

        return jsonify({
            "success": True,
            "error": None
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/credentials/unlock', methods=['POST'])
def credential_unlock():
    """
    Entsperrt gespeicherte Credentials mit Master-Passwort.

    Expects JSON:
        {
            master_password: str
        }

    Returns:
        JSON: {success: bool, error: str | null}
    """
    try:
        data = request.get_json()
        master_password = data.get('master_password')

        if not master_password:
            return jsonify({
                "success": False,
                "error": "Master-Passwort erforderlich"
            }), 400

        # Credentials laden
        credentials = CredentialManager.load_credentials(master_password)

        if not credentials:
            return jsonify({
                "success": False,
                "error": "Falsches Master-Passwort oder Fehler beim Laden"
            }), 401

        # Migration durchführen falls noch ausstehend
        if CredentialManager.migrate_from_config():
            CredentialManager.remove_credentials_from_config()

        # Session setzen
        session['authenticated'] = True
        session['credentials'] = credentials

        # E3DC Fetcher initialisieren
        global _e3dc_fetcher
        _e3dc_fetcher = E3DCFetcher(
            username=credentials['username'],
            password=credentials['password'],
            ip_address=credentials.get('ip_address', ''),
            rscp_key=credentials.get('rscp_key', '')
        )

        return jsonify({
            "success": True,
            "error": None
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/credentials/reset', methods=['POST'])
def credential_reset():
    """
    Löscht gespeicherte Credentials (für Reset).

    Returns:
        JSON: {success: bool, error: str | null}
    """
    try:
        success = CredentialManager.delete_credentials()

        if success:
            # Session löschen
            session.clear()

            # Fetcher zurücksetzen
            global _e3dc_fetcher
            _e3dc_fetcher = None

            return jsonify({
                "success": True,
                "error": None
            })
        else:
            return jsonify({
                "success": False,
                "error": "Keine Credentials zum Löschen gefunden"
            }), 404

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ========== API: DATA ENDPOINTS ==========

@app.route('/api/data/live', methods=['GET'])
def get_live_data():
    """
    Ruft aktuelle Live-Daten ab (erfordert Authentifizierung).

    Returns:
        JSON: Live-Daten vom E3DC-Portal
    """
    if 'authenticated' not in session or not session['authenticated']:
        return jsonify({"error": "Nicht authentifiziert"}), 401

    try:
        global _e3dc_fetcher

        # Fetcher initialisieren falls noch nicht geschehen
        if _e3dc_fetcher is None:
            credentials = session.get('credentials')
            if not credentials:
                return jsonify({"error": "Keine Credentials in Session"}), 401

            _e3dc_fetcher = E3DCFetcher(
                username=credentials['username'],
                password=credentials['password'],
                ip_address=credentials.get('ip_address', ''),
                rscp_key=credentials.get('rscp_key', '')
            )

        # Login falls noch nicht eingeloggt
        if not _e3dc_fetcher.logged_in:
            if not _e3dc_fetcher.login():
                return jsonify({"error": "Verbindung fehlgeschlagen"}), 500

        # Live-Daten abrufen
        live_data = _e3dc_fetcher.fetch_live_data()
        return jsonify(live_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/data/history', methods=['GET'])
def get_history_data():
    """
    Ruft historische Daten ab (erfordert Authentifizierung).

    Query-Parameter:
        start_date: str (YYYY-MM-DD, optional)
        end_date: str (YYYY-MM-DD, optional)
        resolution: str (hour|day|month|year, default: day)

    Returns:
        JSON: Historische Daten vom E3DC-Portal
    """
    if 'authenticated' not in session or not session['authenticated']:
        return jsonify({"error": "Nicht authentifiziert"}), 401

    try:
        global _e3dc_fetcher

        # Fetcher initialisieren falls noch nicht geschehen
        if _e3dc_fetcher is None:
            credentials = session.get('credentials')
            if not credentials:
                return jsonify({"error": "Keine Credentials in Session"}), 401

            _e3dc_fetcher = E3DCFetcher(
                username=credentials['username'],
                password=credentials['password'],
                ip_address=credentials.get('ip_address', ''),
                rscp_key=credentials.get('rscp_key', '')
            )

        # Login falls noch nicht eingeloggt
        if not _e3dc_fetcher.logged_in:
            if not _e3dc_fetcher.login():
                return jsonify({"error": "Verbindung fehlgeschlagen"}), 500

        # Parameter auslesen
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        resolution = request.args.get('resolution', 'day')

        # Historische Daten abrufen
        history_data = _e3dc_fetcher.fetch_history_data(
            start_date=start_date,
            end_date=end_date,
            resolution=resolution
        )

        return jsonify(history_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/logout', methods=['POST'])
def logout():
    """
    Logout: Session beenden

    Returns:
        JSON: {success: bool}
    """
    session.clear()
    global _e3dc_fetcher
    _e3dc_fetcher = None

    return jsonify({"success": True})


# ========== STATIC FILES ==========

@app.route('/css/<path:filename>')
def css_files(filename):
    """CSS-Dateien ausliefern"""
    return send_from_directory(BASE_PATH / 'css', filename)


@app.route('/js/<path:filename>')
def js_files(filename):
    """JavaScript-Dateien ausliefern"""
    return send_from_directory(BASE_PATH / 'js', filename)


@app.route('/data/<path:filename>')
def data_files(filename):
    """Daten-Dateien ausliefern (CSV/JSON)"""
    return send_from_directory(BASE_PATH / 'data', filename)


# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def not_found(e):
    """404-Fehlerseite"""
    return jsonify({"error": "Nicht gefunden"}), 404


@app.errorhandler(500)
def internal_error(e):
    """500-Fehlerseite"""
    return jsonify({"error": "Interner Serverfehler"}), 500


# ========== MAIN ==========

def main():
    """Startet den Flask-Webserver"""
    print("=== E3DC Solar Dashboard Server ===\n")

    # Konfiguration laden
    config = load_config()
    host = config.get("host", "localhost")
    port = config.get("port", 5000)
    auto_open = config.get("auto_open_browser", True)

    # Credential-Status prüfen
    if CredentialManager.credentials_exist():
        print("✓ Verschlüsselte Credentials gefunden")
    else:
        print("! Keine Credentials gefunden - Ersteinrichtung erforderlich")

    # Migration verfügbar?
    migration_data = CredentialManager.migrate_from_config()
    if migration_data:
        print("! Migration verfügbar: Credentials in config.json gefunden")

    print(f"\nServer startet auf http://{host}:{port}")
    print("Drücken Sie STRG+C zum Beenden\n")

    # Browser öffnen
    if auto_open:
        open_browser(host, port)

    # Server starten
    try:
        app.run(
            host=host,
            port=port,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\nServer beendet.")
    except Exception as e:
        print(f"\nFehler beim Starten des Servers: {e}")


if __name__ == "__main__":
    main()
