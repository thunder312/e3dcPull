#!/usr/bin/env python3
"""
E3DC Data Fetcher
Verwendet pye3dc für lokale RSCP-Verbindung zum E3DC-System.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from e3dc import E3DC
except ImportError:
    print("Fehler: 'pye3dc' Bibliothek nicht gefunden.")
    print("Bitte installieren mit: pip install pye3dc")
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
    """Klasse zum Abrufen von Daten vom E3DC-System via lokaler RSCP-Verbindung"""

    def __init__(self, username: str, password: str, ip_address: str, rscp_key: str):
        """
        Initialisiert den E3DC Fetcher.

        Args:
            username: E3DC Portal Benutzername
            password: E3DC Portal Passwort
            ip_address: IP-Adresse des E3DC-Systems im lokalen Netzwerk
            rscp_key: RSCP-Passwort (auf dem Gerät unter Personalisieren -> RSCP-Passwort)
        """
        self.username = username
        self.password = password
        self.ip_address = ip_address
        self.rscp_key = rscp_key
        self.e3dc = None
        self.logged_in = False

    def login(self) -> bool:
        """Stellt die Verbindung zum E3DC-System her"""
        print(f"Verbinde mit E3DC unter {self.ip_address}...")

        try:
            self.e3dc = E3DC(
                E3DC.CONNECT_LOCAL,
                username=self.username,
                password=self.password,
                ipAddress=self.ip_address,
                key=self.rscp_key
            )
            print("Verbindung erfolgreich!")
            self.logged_in = True
            return True

        except Exception as e:
            print(f"Verbindungsfehler: {type(e).__name__}: {e}")
            self.logged_in = False
            return False

    def fetch_live_data(self) -> dict:
        """Ruft aktuelle Live-Daten ab"""
        if not self.logged_in or not self.e3dc:
            print("Nicht verbunden!")
            return {"error": "Nicht verbunden"}

        try:
            # Poll aktueller Systemstatus
            poll_data = self.e3dc.poll()

            # Daten in einheitliches Format umwandeln
            live_data = {
                "timestamp": datetime.now().isoformat(),
                "pvPower": poll_data.get("production", {}).get("solar", 0),
                "batteryPower": poll_data.get("production", {}).get("battery", 0),
                "gridPower": poll_data.get("production", {}).get("grid", 0),
                "homePower": poll_data.get("consumption", {}).get("house", 0),
                "batterySoc": poll_data.get("stateOfCharge", 0),
                "autarky": poll_data.get("autarky", 0),
                "selfConsumption": poll_data.get("selfConsumption", 0),
                "raw": poll_data  # Rohdaten für Debugging
            }

            print(f"Live-Daten abgerufen: PV={live_data['pvPower']}W, "
                  f"Batterie={live_data['batterySoc']}%, "
                  f"Verbrauch={live_data['homePower']}W")

            return live_data

        except Exception as e:
            error_msg = f"Fehler beim Abrufen der Live-Daten: {e}"
            print(error_msg)
            return {"error": error_msg}

    def fetch_history_data(self, start_date: str = None, end_date: str = None,
                           resolution: str = "day") -> dict:
        """
        Ruft historische Daten ab.

        Args:
            start_date: Startdatum (YYYY-MM-DD), Standard: vor 7 Tagen
            end_date: Enddatum (YYYY-MM-DD), Standard: heute
            resolution: "15min", "hour" oder "day" für entsprechende Granularität

        Returns:
            dict: Historische Daten oder dict mit "error" Schlüssel bei Fehler
        """
        if not self.logged_in or not self.e3dc:
            error_msg = "Nicht verbunden! Verbindung muss zuerst hergestellt werden."
            print(error_msg)
            return {"error": error_msg}

        # Standard-Zeitraum: letzte 7 Tage
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        # Auflösung bestimmen (Zeitspanne in Sekunden und Schrittweite)
        resolution_config = {
            "15min": {"timespan": 900, "step": timedelta(minutes=15), "label": "15-Minuten"},
            "hour": {"timespan": 3600, "step": timedelta(hours=1), "label": "Stunden"},
            "day": {"timespan": 86400, "step": timedelta(days=1), "label": "Tages"}
        }

        config = resolution_config.get(resolution, resolution_config["day"])
        timespan = config["timespan"]
        step = config["step"]

        print(f"Rufe historische Daten ab: {start_date} bis {end_date} (Auflösung: {config['label']})")

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            # Bei Tagesauflösung: Ende ist 00:00 des Folgetages
            # Bei feinerer Auflösung: Ende ist 23:59 des Enddatums
            if resolution == "day":
                end_dt = end_dt + timedelta(days=1) - step
            else:
                end_dt = end_dt.replace(hour=23, minute=59, second=59)

            all_data = []
            current_dt = start_dt
            total_intervals = 0

            while current_dt <= end_dt:
                try:
                    # get_db_data liefert Daten für einen bestimmten Zeitraum
                    interval_data = self.e3dc.get_db_data(
                        startDate=current_dt,
                        timespan=timespan,
                        keepAlive=True
                    )

                    if interval_data:
                        # Daten formatieren - korrekte Feldnamen von pye3dc
                        grid_in = interval_data.get("grid_power_in", 0)
                        grid_out = interval_data.get("grid_power_out", 0)
                        bat_in = interval_data.get("bat_power_in", 0)
                        bat_out = interval_data.get("bat_power_out", 0)
                        solar = interval_data.get("solarProduction", 0)

                        entry = {
                            "timestamp": current_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                            "date": current_dt.strftime("%Y-%m-%d"),
                            "time": current_dt.strftime("%H:%M"),
                            "resolution": resolution,
                            # Frontend-kompatible Felder
                            "pvPower": solar,
                            "pv_power": solar,
                            "batteryPower": bat_out - bat_in,  # positiv = entladen
                            "battery_power": bat_out - bat_in,
                            "gridPower": grid_in - grid_out,  # positiv = Bezug, negativ = Einspeisung
                            "grid_power": grid_in - grid_out,
                            "grid_draw": grid_in,  # Netzbezug
                            "grid_feed": grid_out,  # Netzeinspeisung
                            "consumption": interval_data.get("consumption", 0),
                            "homePower": interval_data.get("consumption", 0),
                            "batterySoc": interval_data.get("stateOfCharge", 0),
                            "battery_soc": interval_data.get("stateOfCharge", 0),
                            # Zusätzliche Details
                            "gridFeedIn": grid_out,
                            "gridConsumption": grid_in,
                            "batteryChargeEnergy": bat_in,
                            "batteryDischargeEnergy": bat_out,
                            "autarky": interval_data.get("autarky", 0),
                            "selfConsumption": interval_data.get("consumed_production", 0),
                        }
                        all_data.append(entry)
                        total_intervals += 1

                        # Bei Tag-Auflösung: Fortschritt anzeigen
                        if resolution == "day":
                            print(f"  {current_dt.strftime('%Y-%m-%d')}: PV={entry['pvPower']:.1f}Wh, "
                                  f"Verbrauch={entry['consumption']:.1f}Wh")

                except Exception as interval_error:
                    print(f"  Warnung: Keine Daten für {current_dt.strftime('%Y-%m-%d %H:%M')}: {interval_error}")

                current_dt += step

            print(f"Insgesamt {total_intervals} {config['label']}-Datensätze abgerufen")

            return {
                "data": all_data,
                "start_date": start_date,
                "end_date": end_date,
                "resolution": resolution,
                "count": len(all_data)
            }

        except Exception as e:
            error_msg = f"Fehler beim Abrufen der historischen Daten: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return {"error": error_msg}

    def export_to_csv(self, data: dict, output_path: Path) -> bool:
        """Exportiert die Daten als CSV"""
        if not data or "error" in data:
            print("Keine Daten zum Exportieren")
            return False

        # Sicherstellen, dass das Ausgabeverzeichnis existiert
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                # CSV-Header
                f.write("date,pv_energy,battery_charge,battery_discharge,"
                        "grid_feed_in,grid_consumption,home_consumption,autarky,self_consumption\n")

                # Daten schreiben
                entries = data.get("data", [])
                if isinstance(data, list):
                    entries = data

                for entry in entries:
                    date = entry.get("date", entry.get("timestamp", ""))
                    pv = entry.get("pvPower", 0)
                    bat_charge = entry.get("batteryChargeEnergy", 0)
                    bat_discharge = entry.get("batteryDischargeEnergy", 0)
                    grid_feed = entry.get("gridFeedIn", 0)
                    grid_cons = entry.get("gridConsumption", 0)
                    home_cons = entry.get("homeConsumption", 0)
                    autarky = entry.get("autarky", 0)
                    self_cons = entry.get("selfConsumption", 0)

                    f.write(f"{date},{pv},{bat_charge},{bat_discharge},"
                            f"{grid_feed},{grid_cons},{home_cons},{autarky},{self_cons}\n")

            print(f"CSV exportiert nach: {output_path}")
            return True

        except IOError as e:
            print(f"Fehler beim Schreiben der CSV: {e}")
            return False

    def export_to_json(self, data: dict, output_path: Path) -> bool:
        """Exportiert die Daten als JSON"""
        if not data:
            print("Keine Daten zum Exportieren")
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            print(f"JSON exportiert nach: {output_path}")
            return True

        except IOError as e:
            print(f"Fehler beim Schreiben der JSON: {e}")
            return False

    def disconnect(self):
        """Trennt die Verbindung zum E3DC-System"""
        if self.e3dc:
            try:
                self.e3dc.disconnect()
                print("Verbindung getrennt")
            except Exception:
                pass
        self.logged_in = False
        self.e3dc = None


def main(credentials=None):
    """
    Hauptfunktion

    Args:
        credentials: dict mit {username, password, ip_address, rscp_key}
    """
    config = load_config()

    if credentials is None:
        print("Fehler: Keine Credentials bereitgestellt!")
        print("Bitte starten Sie den Webserver mit: python web_server.py")
        sys.exit(1)

    # Prüfen ob alle erforderlichen Felder vorhanden sind
    required_fields = ["username", "password", "ip_address", "rscp_key"]
    missing = [f for f in required_fields if f not in credentials or not credentials[f]]
    if missing:
        print(f"Fehler: Fehlende Credentials: {', '.join(missing)}")
        sys.exit(1)

    # E3DC Fetcher initialisieren
    fetcher = E3DCFetcher(
        username=credentials["username"],
        password=credentials["password"],
        ip_address=credentials["ip_address"],
        rscp_key=credentials["rscp_key"]
    )

    try:
        # Verbindung herstellen
        if not fetcher.login():
            print("Verbindung fehlgeschlagen. Programm wird beendet.")
            sys.exit(1)

        # Daten abrufen
        print("\nRufe historische Daten ab (letzte 7 Tage)...")
        history_data = fetcher.fetch_history_data()

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
        if live_data and "error" not in live_data:
            live_json_path = data_folder / "e3dc_live.json"
            fetcher.export_to_json(live_data, live_json_path)

        print("\nFertig!")

    finally:
        fetcher.disconnect()


if __name__ == "__main__":
    main()
