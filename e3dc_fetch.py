#!/usr/bin/env python3
"""
E3DC Data Fetcher
Lädt CSV-Daten vom E3DC-Portal herunter für die lokale Visualisierung.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("Fehler: 'requests' Bibliothek nicht gefunden.")
    print("Bitte installieren mit: pip install requests")
    sys.exit(1)

# Konfiguration laden
CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config():
    """Lädt die Konfiguration aus config.json"""
    if not CONFIG_PATH.exists():
        print(f"Fehler: Konfigurationsdatei nicht gefunden: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

class E3DCFetcher:
    """Klasse zum Abrufen von Daten vom E3DC-Portal"""

    BASE_URL = "https://my.e3dc.com"
    LOGIN_URL = f"{BASE_URL}/login"
    API_URL = f"{BASE_URL}/api"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        })
        self.logged_in = False

    def login(self) -> bool:
        """Führt den Login durch"""
        print("Versuche Login...")

        # Erst die Login-Seite aufrufen um CSRF-Token zu bekommen
        try:
            self.session.get(self.BASE_URL)
        except requests.RequestException as e:
            print(f"Fehler beim Aufrufen der Seite: {e}")
            return False

        # Login durchführen
        login_data = {
            "username": self.username,
            "password": self.password,
        }

        try:
            response = self.session.post(
                f"{self.API_URL}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                print("Login erfolgreich!")
                self.logged_in = True
                return True
            else:
                print(f"Login fehlgeschlagen: Status {response.status_code}")
                print(f"Antwort: {response.text[:500]}")
                return False

        except requests.RequestException as e:
            print(f"Login-Fehler: {e}")
            return False

    def get_system_id(self) -> str:
        """Extrahiert die System-ID aus der Dashboard-URL"""
        config = load_config()
        url = config["e3dc"]["dashboard_url"]
        # URL-Format: .../overview/{system_id}/{serial}
        parts = url.rstrip("/").split("/")
        if len(parts) >= 2:
            return parts[-2]  # system_id
        return ""

    def get_serial(self) -> str:
        """Extrahiert die Seriennummer aus der Dashboard-URL"""
        config = load_config()
        url = config["e3dc"]["dashboard_url"]
        parts = url.rstrip("/").split("/")
        if len(parts) >= 1:
            return parts[-1]  # serial
        return ""

    def fetch_live_data(self) -> dict:
        """Ruft aktuelle Live-Daten ab"""
        if not self.logged_in:
            print("Nicht eingeloggt!")
            return {}

        system_id = self.get_system_id()
        serial = self.get_serial()

        try:
            # Live-Daten API-Endpunkt
            response = self.session.get(
                f"{self.API_URL}/systems/{system_id}/live",
                params={"serial": serial}
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Fehler beim Abrufen der Live-Daten: {response.status_code}")
                return {}

        except requests.RequestException as e:
            print(f"Fehler: {e}")
            return {}

    def fetch_history_data(self, start_date: str = None, end_date: str = None,
                          resolution: str = "day") -> dict:
        """
        Ruft historische Daten ab.

        Args:
            start_date: Startdatum (YYYY-MM-DD), Standard: vor 30 Tagen
            end_date: Enddatum (YYYY-MM-DD), Standard: heute
            resolution: "hour", "day", "month", "year"
        """
        if not self.logged_in:
            print("Nicht eingeloggt!")
            return {}

        system_id = self.get_system_id()
        serial = self.get_serial()

        # Standard-Zeitraum: letzte 30 Tage
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        try:
            response = self.session.get(
                f"{self.API_URL}/systems/{system_id}/history",
                params={
                    "serial": serial,
                    "start": start_date,
                    "end": end_date,
                    "resolution": resolution
                }
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Fehler beim Abrufen der History: {response.status_code}")
                print(f"Antwort: {response.text[:500]}")
                return {}

        except requests.RequestException as e:
            print(f"Fehler: {e}")
            return {}

    def export_to_csv(self, data: dict, output_path: Path) -> bool:
        """Exportiert die Daten als CSV"""
        if not data:
            print("Keine Daten zum Exportieren")
            return False

        # Sicherstellen, dass das Ausgabeverzeichnis existiert
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                # CSV-Header
                f.write("timestamp,pv_power,battery_power,grid_power,consumption,battery_soc\n")

                # Daten schreiben
                if "data" in data:
                    for entry in data["data"]:
                        timestamp = entry.get("timestamp", "")
                        pv = entry.get("pv_power", entry.get("pvPower", 0))
                        battery = entry.get("battery_power", entry.get("batteryPower", 0))
                        grid = entry.get("grid_power", entry.get("gridPower", 0))
                        consumption = entry.get("consumption", entry.get("homePower", 0))
                        soc = entry.get("battery_soc", entry.get("batterySoc", 0))

                        f.write(f"{timestamp},{pv},{battery},{grid},{consumption},{soc}\n")

                elif isinstance(data, list):
                    for entry in data:
                        timestamp = entry.get("timestamp", "")
                        pv = entry.get("pv_power", entry.get("pvPower", 0))
                        battery = entry.get("battery_power", entry.get("batteryPower", 0))
                        grid = entry.get("grid_power", entry.get("gridPower", 0))
                        consumption = entry.get("consumption", entry.get("homePower", 0))
                        soc = entry.get("battery_soc", entry.get("batterySoc", 0))

                        f.write(f"{timestamp},{pv},{battery},{grid},{consumption},{soc}\n")

            print(f"CSV exportiert nach: {output_path}")
            return True

        except IOError as e:
            print(f"Fehler beim Schreiben der CSV: {e}")
            return False

    def export_to_json(self, data: dict, output_path: Path) -> bool:
        """Exportiert die Daten als JSON (für die HTML-Seite)"""
        if not data:
            print("Keine Daten zum Exportieren")
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"JSON exportiert nach: {output_path}")
            return True

        except IOError as e:
            print(f"Fehler beim Schreiben der JSON: {e}")
            return False


def main():
    """Hauptfunktion"""
    config = load_config()

    # E3DC Fetcher initialisieren
    fetcher = E3DCFetcher(
        username=config["e3dc"]["username"],
        password=config["e3dc"]["password"]
    )

    # Login
    if not fetcher.login():
        print("Login fehlgeschlagen. Programm wird beendet.")
        sys.exit(1)

    # Daten abrufen
    print("\nRufe historische Daten ab (letzte 30 Tage)...")
    history_data = fetcher.fetch_history_data(resolution="day")

    # Ausgabepfade
    base_path = Path(__file__).parent
    data_folder = base_path / config["output"]["csv_folder"]

    # Als CSV und JSON exportieren
    csv_path = data_folder / config["output"]["csv_filename"]
    json_path = data_folder / "e3dc_data.json"

    fetcher.export_to_csv(history_data, csv_path)
    fetcher.export_to_json(history_data, json_path)

    # Live-Daten auch abrufen
    print("\nRufe Live-Daten ab...")
    live_data = fetcher.fetch_live_data()
    if live_data:
        live_json_path = data_folder / "e3dc_live.json"
        fetcher.export_to_json(live_data, live_json_path)

    print("\nFertig!")


if __name__ == "__main__":
    main()
