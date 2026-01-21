#!/usr/bin/env python3
"""
E3DC Data Fetcher
Verwendet pye3dc für lokale RSCP-Verbindung zum E3DC-System.
"""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    from e3dc import E3DC
    from e3dc._rscpTags import RscpTag, RscpType
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

    def _fetch_day_intervals(self, day_start: datetime, interval_seconds: int = 900, debug: bool = True) -> list:
        """
        Ruft alle Intervalle für einen Tag ab mit korrekten RSCP-Parametern.

        Die pye3dc-Bibliothek hat einen Bug: Sie setzt TIME_INTERVAL = TIME_SPAN,
        was nur einen aggregierten Wert zurückgibt. Diese Methode verwendet
        sendRequest() direkt mit korrekten Parametern.

        WICHTIG: Die Response für einen ganzen Tag (96 Intervalle) ist zu groß
        für den pye3dc-Buffer. Daher wird der Tag in 4x 6-Stunden-Blöcke aufgeteilt.

        Args:
            day_start: Beginn des Tages (00:00:00)
            interval_seconds: Intervall in Sekunden (Standard: 900 = 15 Min)
            debug: Debug-Ausgaben aktivieren

        Returns:
            list: Liste von Intervall-Daten für den Tag
        """
        all_intervals = []

        # Tag in 1-Stunden-Blöcke aufteilen (24 Anfragen pro Tag)
        # pye3dc hat einen Bug: socket.recv() wird nur einmal aufgerufen,
        # aber große Responses kommen in mehreren TCP-Paketen.
        # Mit 1h-Chunks (4 Intervalle à ~160 Bytes) bleibt es unter der MTU.
        chunk_hours = 1
        chunk_seconds = chunk_hours * 3600  # 3600 Sekunden = 1 Stunde
        chunks_per_day = 24 // chunk_hours  # 24 Chunks

        seen_timestamps = set()  # Duplikate vermeiden

        for chunk_idx in range(chunks_per_day):
            chunk_start = day_start + timedelta(hours=chunk_idx * chunk_hours)
            start_timestamp = int(time.mktime(chunk_start.timetuple()))

            if debug and chunk_idx == 0:
                print(f"\n  [DEBUG] RSCP-Anfrage (Tag aufgeteilt in {chunks_per_day}x {chunk_hours}h Blöcke):")
                print(f"    TIME_START: {start_timestamp} ({chunk_start})")
                print(f"    TIME_INTERVAL: {interval_seconds}s ({interval_seconds/60:.0f} Min)")
                print(f"    TIME_SPAN: {chunk_seconds}s ({chunk_hours}h)")

            intervals = self._fetch_chunk(start_timestamp, interval_seconds, chunk_seconds, debug and chunk_idx == 0)

            # Nur neue Intervalle hinzufügen (Duplikate filtern)
            new_count = 0
            for interval in intervals:
                ts = interval.get("timestamp", 0)
                if ts not in seen_timestamps:
                    seen_timestamps.add(ts)
                    all_intervals.append(interval)
                    new_count += 1

            if debug:
                print(f"    Chunk {chunk_idx + 1}/{chunks_per_day}: {new_count} neue Intervalle (von {len(intervals)})")

        if debug:
            print(f"\n  [DEBUG] Gesamt: {len(all_intervals)} Intervalle für den Tag")
            if all_intervals:
                solar_sum = sum(i.get("solarProduction", 0) for i in all_intervals)
                cons_sum = sum(i.get("consumption", 0) for i in all_intervals)
                print(f"    Summe Solar: {solar_sum:.0f} Wh = {solar_sum/1000:.2f} kWh")
                print(f"    Summe Verbrauch: {cons_sum:.0f} Wh = {cons_sum/1000:.2f} kWh")

        return all_intervals

    def _fetch_chunk(self, start_timestamp: int, interval_seconds: int, span_seconds: int, debug: bool = False) -> list:
        """
        Ruft einen Zeitblock ab (intern verwendet von _fetch_day_intervals).
        """

        try:
            # Direkte RSCP-Anfrage mit korrekten Parametern
            response = self.e3dc.sendRequest(
                (
                    RscpTag.DB_REQ_HISTORY_DATA_DAY,
                    RscpType.Container,
                    [
                        (RscpTag.DB_REQ_HISTORY_TIME_START, RscpType.Uint64, start_timestamp),
                        (RscpTag.DB_REQ_HISTORY_TIME_INTERVAL, RscpType.Uint64, interval_seconds),
                        (RscpTag.DB_REQ_HISTORY_TIME_SPAN, RscpType.Uint64, span_seconds),
                    ],
                ),
                keepAlive=True,
            )

            if debug:
                print(f"\n  [DEBUG] Response erhalten:")
                print(f"    Type: {type(response)}")
                if response:
                    print(f"    Länge: {len(response) if hasattr(response, '__len__') else 'N/A'}")
                    if isinstance(response, tuple) and len(response) >= 1:
                        print(f"    response[0] (Tag): {response[0]}")
                    if isinstance(response, tuple) and len(response) >= 2:
                        print(f"    response[1] (Type): {response[1]}")
                    if isinstance(response, tuple) and len(response) >= 3:
                        data = response[2]
                        print(f"    response[2] Type: {type(data)}")
                        if isinstance(data, list):
                            print(f"    response[2] Länge: {len(data)}")
                            if len(data) > 0:
                                print(f"    Erstes Element: {type(data[0])}")
                                # Zeige erste 3 Container
                                for i, item in enumerate(data[:3]):
                                    print(f"    Container[{i}]: {item}")
                                if len(data) > 3:
                                    print(f"    ... und {len(data) - 3} weitere Container")
                else:
                    print("    Response ist None oder leer!")

            # Response parsen - enthält mehrere DB_SUM_CONTAINER
            intervals = []
            debug_first_interval = True  # Nur erstes Intervall detailliert loggen

            # Die Response-Struktur ist: (Tag, Type, [Container1, Container2, ...])
            if response and len(response) >= 3 and isinstance(response[2], list):
                containers = response[2]

                if debug:
                    print(f"\n  [DEBUG] Parse {len(containers)} Container...")

                for container in containers:
                    # Jeder Container ist ein Tuple: (Tag, Type, [Werte])
                    if not isinstance(container, tuple) or len(container) < 3:
                        if debug:
                            print(f"    [DEBUG] Überspringe ungültigen Container: {type(container)}")
                        continue

                    container_tag = container[0]
                    # DB_SUM_CONTAINER ist die Summe für den Zeitraum, DB_VALUE_CONTAINER sind Einzelwerte
                    # Wir wollen nur DB_VALUE_CONTAINER (die 15-Min-Intervalle)
                    if container_tag == 'DB_SUM_CONTAINER':
                        continue  # Summe überspringen

                    values = container[2] if isinstance(container[2], list) else []

                    # Werte aus dem Container extrahieren
                    interval_data = {}
                    graph_index = 0
                    unknown_tags = []

                    for item in values:
                        if not isinstance(item, tuple) or len(item) < 3:
                            continue
                        tag, tag_type, value = item

                        # Tags kommen als Strings, nicht als Enums!
                        tag_name = tag.name if hasattr(tag, 'name') else str(tag)

                        if tag_name == 'DB_GRAPH_INDEX':
                            graph_index = int(value)  # Float zu Int
                        elif tag_name == 'DB_DC_POWER':
                            interval_data["solarProduction"] = value
                        elif tag_name == 'DB_CONSUMPTION':
                            interval_data["consumption"] = value
                        elif tag_name == 'DB_GRID_POWER_IN':
                            interval_data["grid_power_in"] = value
                        elif tag_name == 'DB_GRID_POWER_OUT':
                            interval_data["grid_power_out"] = value
                        elif tag_name == 'DB_BAT_POWER_IN':
                            interval_data["bat_power_in"] = value
                        elif tag_name == 'DB_BAT_POWER_OUT':
                            interval_data["bat_power_out"] = value
                        elif tag_name == 'DB_BAT_CHARGE_LEVEL':
                            interval_data["stateOfCharge"] = value
                        elif tag_name == 'DB_AUTARKY':
                            interval_data["autarky"] = value
                        elif tag_name == 'DB_CONSUMED_PRODUCTION':
                            interval_data["consumed_production"] = value
                        else:
                            unknown_tags.append((tag_name, value))

                    if interval_data:
                        # Timestamp für dieses Intervall berechnen
                        # graph_index gibt die Position im Tagesverlauf an
                        interval_timestamp = start_timestamp + (graph_index * interval_seconds)
                        interval_data["timestamp"] = interval_timestamp
                        interval_data["graph_index"] = graph_index
                        intervals.append(interval_data)

                        # Debug: Erstes Intervall detailliert anzeigen
                        if debug and debug_first_interval:
                            ts = datetime.fromtimestamp(interval_timestamp)
                            print(f"\n  [DEBUG] Erstes geparste Intervall (Index {graph_index}, {ts.strftime('%H:%M')}):")
                            print(f"    solarProduction: {interval_data.get('solarProduction', 'N/A')} Wh")
                            print(f"    consumption: {interval_data.get('consumption', 'N/A')} Wh")
                            print(f"    grid_power_in: {interval_data.get('grid_power_in', 'N/A')} Wh")
                            print(f"    grid_power_out: {interval_data.get('grid_power_out', 'N/A')} Wh")
                            print(f"    bat_power_in: {interval_data.get('bat_power_in', 'N/A')} Wh")
                            print(f"    bat_power_out: {interval_data.get('bat_power_out', 'N/A')} Wh")
                            print(f"    stateOfCharge: {interval_data.get('stateOfCharge', 'N/A')} %")
                            if unknown_tags:
                                print(f"    Unbekannte Tags: {unknown_tags[:5]}")
                            debug_first_interval = False

                if debug:
                    print(f"\n  [DEBUG] Erfolgreich {len(intervals)} Intervalle geparst")
                    if intervals:
                        # Zeige Zusammenfassung des ersten Tages
                        solar_sum = sum(i.get("solarProduction", 0) for i in intervals)
                        cons_sum = sum(i.get("consumption", 0) for i in intervals)
                        print(f"    Summe Solar: {solar_sum:.0f} Wh = {solar_sum/1000:.2f} kWh")
                        print(f"    Summe Verbrauch: {cons_sum:.0f} Wh = {cons_sum/1000:.2f} kWh")
            else:
                if debug:
                    print(f"  [DEBUG] Response hat nicht das erwartete Format!")
                    print(f"    response: {response}")

            return intervals

        except Exception as e:
            print(f"    Fehler bei _fetch_chunk: {e}")
            import traceback
            traceback.print_exc()
            return []

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

        # Auflösung bestimmen
        resolution_config = {
            "15min": {"interval": 900, "label": "15-Minuten"},
            "hour": {"interval": 3600, "label": "Stunden"},
            "day": {"interval": 86400, "label": "Tages"}
        }

        config = resolution_config.get(resolution, resolution_config["day"])
        interval_seconds = config["interval"]

        print(f"Rufe historische Daten ab: {start_date} bis {end_date} (Auflösung: {config['label']})")

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            now = datetime.now()

            all_data = []
            current_day = start_dt
            is_first_day = True  # Debug nur für ersten Tag

            # Tag für Tag abfragen
            while current_day <= end_dt:
                day_start = current_day.replace(hour=0, minute=0, second=0, microsecond=0)

                print(f"  Lade {current_day.strftime('%Y-%m-%d')}...", end="", flush=True)

                if resolution == "day":
                    # Bei Tagesauflösung: Alte Methode verwenden (get_db_data)
                    # Diese gibt korrekt die Tagessumme zurück
                    try:
                        day_data = self.e3dc.get_db_data(
                            startDate=current_day.date(),
                            timespan="DAY",
                            keepAlive=True
                        )

                        if day_data:
                            grid_in = day_data.get("grid_power_in", 0)
                            grid_out = day_data.get("grid_power_out", 0)
                            bat_in = day_data.get("bat_power_in", 0)
                            bat_out = day_data.get("bat_power_out", 0)
                            solar = day_data.get("solarProduction", 0)

                            entry = {
                                "timestamp": current_day.strftime("%Y-%m-%dT00:00:00"),
                                "date": current_day.strftime("%Y-%m-%d"),
                                "time": "00:00",
                                "resolution": resolution,
                                "pvPower": solar,
                                "pv_power": solar,
                                "batteryPower": bat_out - bat_in,
                                "battery_power": bat_out - bat_in,
                                "gridPower": grid_in - grid_out,
                                "grid_power": grid_in - grid_out,
                                "grid_draw": grid_in,
                                "grid_feed": grid_out,
                                "consumption": day_data.get("consumption", 0),
                                "homePower": day_data.get("consumption", 0),
                                "batterySoc": day_data.get("stateOfCharge", 0),
                                "battery_soc": day_data.get("stateOfCharge", 0),
                                "gridFeedIn": grid_out,
                                "gridConsumption": grid_in,
                                "batteryChargeEnergy": bat_in,
                                "batteryDischargeEnergy": bat_out,
                                "autarky": day_data.get("autarky", 0),
                                "selfConsumption": day_data.get("consumed_production", 0),
                            }
                            all_data.append(entry)
                            print(f" PV={solar:.0f}Wh, Verbrauch={entry['consumption']:.0f}Wh")
                        else:
                            print(" keine Daten")

                    except Exception as e:
                        print(f" Fehler: {e}")
                else:
                    # Bei 15min/hour Auflösung: Neue Methode mit korrekten RSCP-Parametern
                    # Debug nur für ersten Tag aktivieren
                    intervals = self._fetch_day_intervals(day_start, interval_seconds, debug=is_first_day)
                    is_first_day = False

                    if intervals:
                        count = 0
                        for interval in intervals:
                            # Timestamp in datetime umwandeln
                            ts = datetime.fromtimestamp(interval.get("timestamp", 0))

                            # Nur Daten bis jetzt (keine Zukunft)
                            if ts > now:
                                continue

                            grid_in = interval.get("grid_power_in", 0)
                            grid_out = interval.get("grid_power_out", 0)
                            bat_in = interval.get("bat_power_in", 0)
                            bat_out = interval.get("bat_power_out", 0)
                            solar = interval.get("solarProduction", 0)

                            # Werte sind Energie in Wh für das Intervall
                            # Für Leistung in W: Wh / (Intervall in Stunden)
                            interval_hours = interval_seconds / 3600.0

                            entry = {
                                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                                "date": ts.strftime("%Y-%m-%d"),
                                "time": ts.strftime("%H:%M"),
                                "resolution": resolution,
                                # Leistung in W (Energie/Zeit)
                                "pvPower": solar / interval_hours,
                                "pv_power": solar / interval_hours,
                                "batteryPower": (bat_out - bat_in) / interval_hours,
                                "battery_power": (bat_out - bat_in) / interval_hours,
                                "gridPower": (grid_in - grid_out) / interval_hours,
                                "grid_power": (grid_in - grid_out) / interval_hours,
                                "grid_draw": grid_in / interval_hours,
                                "grid_feed": grid_out / interval_hours,
                                "consumption": interval.get("consumption", 0) / interval_hours,
                                "homePower": interval.get("consumption", 0) / interval_hours,
                                "batterySoc": interval.get("stateOfCharge", 0),
                                "battery_soc": interval.get("stateOfCharge", 0),
                                "gridFeedIn": grid_out / interval_hours,
                                "gridConsumption": grid_in / interval_hours,
                                "batteryChargeEnergy": bat_in,
                                "batteryDischargeEnergy": bat_out,
                                "autarky": interval.get("autarky", 0),
                                "selfConsumption": interval.get("consumed_production", 0),
                            }
                            all_data.append(entry)
                            count += 1

                        print(f" {count} Intervalle")
                    else:
                        print(" keine Daten")

                current_day += timedelta(days=1)

            # Daten nach Timestamp sortieren
            all_data.sort(key=lambda x: x.get("timestamp", ""))

            print(f"Insgesamt {len(all_data)} {config['label']}-Datensätze abgerufen")

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
