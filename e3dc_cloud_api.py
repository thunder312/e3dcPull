#!/usr/bin/env python3
"""
E3DC Cloud API Fetcher
Verwendet die offizielle E3DC Cloud API (api.e3dc.com) für Datenabfragen.
Dokumentation: https://api.e3dc.com/
"""

import json
from datetime import datetime, timedelta
from typing import Optional

import requests


class E3DCCloudAPI:
    """Klasse zum Abrufen von Daten über die offizielle E3DC Cloud API"""

    API_BASE_URL = "https://api.e3dc.com"

    def __init__(self, username: str, password: str, serial_number: str = None):
        """
        Initialisiert den E3DC Cloud API Client.

        Args:
            username: E3DC Portal Benutzername (E-Mail)
            password: E3DC Portal Passwort (Klartext)
            serial_number: Seriennummer des E3DC-Systems (optional, wird automatisch ermittelt)
        """
        self.username = username
        self.password = password
        self.serial_number = serial_number
        self.token = None
        self.logged_in = False
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json"
        })

    def login(self) -> bool:
        """
        Authentifiziert sich bei der E3DC Cloud API.

        Returns:
            bool: True wenn erfolgreich, False bei Fehler
        """
        print("Verbinde mit E3DC Cloud API (api.e3dc.com)...")

        try:
            # Authentifizierung: POST /api/auth/
            # Content-Type: application/x-www-form-urlencoded
            # Passwort im Klartext (kein MD5!)
            response = self.session.post(
                f"{self.API_BASE_URL}/api/auth/",
                data={
                    "user": self.username,
                    "password": self.password
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                # Token aus Antwort extrahieren
                # Die API gibt ein JWT zurück
                if isinstance(data, dict):
                    self.token = data.get("token") or data.get("jwtToken") or data.get("accessToken")
                    if not self.token and "result" in data:
                        # Manche APIs geben {result: true, token: "..."} zurück
                        self.token = data.get("token")
                elif isinstance(data, str):
                    # Token direkt als String
                    self.token = data

                if self.token:
                    # Token für alle weiteren Anfragen setzen
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.token}"
                    })
                    self.logged_in = True
                    print("Cloud API Authentifizierung erfolgreich!")

                    # Seriennummer ermitteln falls nicht angegeben
                    if not self.serial_number:
                        self._fetch_serial_number()

                    return True
                else:
                    # Vielleicht ist die gesamte Antwort das Token
                    print(f"Antwort erhalten: {data}")
                    # Versuchen, die Antwort als Token zu nutzen
                    if data:
                        self.token = str(data) if not isinstance(data, dict) else None

                    if self.token:
                        self.session.headers.update({
                            "Authorization": f"Bearer {self.token}"
                        })
                        self.logged_in = True
                        print("Cloud API Verbindung erfolgreich!")
                        if not self.serial_number:
                            self._fetch_serial_number()
                        return True

                    print("Kein Token in der Antwort gefunden")
                    return False

            else:
                print(f"Authentifizierung fehlgeschlagen: {response.status_code}")
                print(f"Antwort: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"Verbindungsfehler: {e}")
            return False
        except Exception as e:
            print(f"Fehler bei der Authentifizierung: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _fetch_serial_number(self):
        """Ermittelt die Seriennummer des ersten registrierten Systems."""
        try:
            # GET /api/systemList/
            response = self.session.get(
                f"{self.API_BASE_URL}/api/systemList/",
                timeout=30
            )

            if response.status_code == 200:
                systems = response.json()
                print(f"Systeme gefunden: {systems}")

                if systems and len(systems) > 0:
                    # Erstes System verwenden
                    if isinstance(systems[0], dict):
                        self.serial_number = systems[0].get("serialNumber") or systems[0].get("sn") or systems[0].get("serial")
                    else:
                        # Liste enthält direkt Seriennummern als Strings
                        self.serial_number = systems[0]
                    print(f"Seriennummer ermittelt: {self.serial_number}")
                else:
                    print("Keine Systeme gefunden!")
            else:
                print(f"Fehler beim Abrufen der Systemliste: {response.status_code}")
                print(f"Antwort: {response.text}")

        except Exception as e:
            print(f"Fehler beim Ermitteln der Seriennummer: {e}")

    def fetch_live_data(self) -> dict:
        """
        Ruft aktuelle Live-Daten ab.
        GET /api/systemState/{sn}

        Returns:
            dict: Live-Daten oder dict mit "error" Schlüssel bei Fehler
        """
        if not self.logged_in:
            if not self.login():
                return {"error": "Nicht eingeloggt"}

        if not self.serial_number:
            return {"error": "Keine Seriennummer verfügbar"}

        try:
            response = self.session.get(
                f"{self.API_BASE_URL}/api/systemState/{self.serial_number}",
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                # Daten in einheitliches Format umwandeln
                live_data = {
                    "timestamp": datetime.now().isoformat(),
                    "pvPower": data.get("pvPower", 0) or data.get("solarPower", 0) or 0,
                    "batteryPower": data.get("batteryPower", 0) or data.get("batPower", 0) or 0,
                    "gridPower": data.get("gridPower", 0) or 0,
                    "homePower": data.get("homePower", 0) or data.get("consumption", 0) or 0,
                    "batterySoc": data.get("batterySoc", 0) or data.get("stateOfCharge", 0) or data.get("soc", 0) or 0,
                    "autarky": data.get("autarky", 0) or 0,
                    "selfConsumption": data.get("selfConsumption", 0) or 0,
                    "raw": data
                }

                print(f"Live-Daten abgerufen: PV={live_data['pvPower']}W, "
                      f"SOC={live_data['batterySoc']}%")

                return live_data

            elif response.status_code == 401:
                # Token abgelaufen, neu einloggen
                self.logged_in = False
                if self.login():
                    return self.fetch_live_data()
                return {"error": "Authentifizierung fehlgeschlagen"}

            else:
                return {"error": f"API-Fehler: {response.status_code} - {response.text}"}

        except Exception as e:
            return {"error": str(e)}

    def fetch_history_data(self, start_date: str = None, end_date: str = None,
                           resolution: str = "15min") -> dict:
        """
        Ruft historische Daten von der Cloud API ab.
        GET /api/historyvalues/{sn}/{from},{to}

        Args:
            start_date: Startdatum (YYYY-MM-DD), Standard: gestern
            end_date: Enddatum (YYYY-MM-DD), Standard: heute
            resolution: "15min", "hour" oder "day"

        Returns:
            dict: Historische Daten oder dict mit "error" Schlüssel bei Fehler
        """
        if not self.logged_in:
            if not self.login():
                return {"error": "Nicht eingeloggt"}

        if not self.serial_number:
            return {"error": "Keine Seriennummer verfügbar"}

        # Standard-Zeitraum: letzter Tag
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        print(f"Rufe historische Daten ab: {start_date} bis {end_date}")

        try:
            # Datum zu Unix-Timestamp konvertieren
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            # Ende des Tages (23:59:59)
            end_dt = end_dt.replace(hour=23, minute=59, second=59)

            start_ts = int(start_dt.timestamp())
            end_ts = int(end_dt.timestamp())

            # GET /api/historyvalues/{sn}/{from},{to}
            response = self.session.get(
                f"{self.API_BASE_URL}/api/historyvalues/{self.serial_number}/{start_ts},{end_ts}",
                timeout=60
            )

            if response.status_code == 200:
                raw_data = response.json()

                # Daten in einheitliches Format umwandeln
                all_data = self._transform_history_data(raw_data, resolution)

                print(f"Insgesamt {len(all_data)} Datensätze abgerufen")

                return {
                    "data": all_data,
                    "start_date": start_date,
                    "end_date": end_date,
                    "resolution": resolution,
                    "count": len(all_data)
                }

            elif response.status_code == 401:
                # Token abgelaufen
                self.logged_in = False
                if self.login():
                    return self.fetch_history_data(start_date, end_date, resolution)
                return {"error": "Authentifizierung fehlgeschlagen"}

            else:
                error_msg = f"API-Fehler: {response.status_code} - {response.text}"
                print(error_msg)
                return {"error": error_msg}

        except Exception as e:
            error_msg = f"Fehler beim Abrufen der historischen Daten: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return {"error": error_msg}

    def _transform_history_data(self, raw_data: list, resolution: str) -> list:
        """
        Transformiert die Rohdaten der Cloud API in das Dashboard-Format.

        Die API liefert 15-Minuten-Werte mit Feldern wie:
        - timestamp / time / t
        - batPowerIn / batPowerOut (oder batteryPower)
        - gridPowerIn / gridPowerOut (oder gridPower)
        - pvPower / solarPower
        - consumption / homePower
        """
        all_data = []

        if not raw_data:
            return all_data

        for entry in raw_data:
            try:
                # Timestamp extrahieren
                ts = entry.get("timestamp") or entry.get("time") or entry.get("t")
                if ts is None:
                    continue

                if isinstance(ts, (int, float)):
                    timestamp = datetime.fromtimestamp(ts)
                elif isinstance(ts, str):
                    # ISO-Format oder Unix-Timestamp als String
                    if ts.isdigit():
                        timestamp = datetime.fromtimestamp(int(ts))
                    else:
                        timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                else:
                    continue

                # Werte extrahieren
                pv_power = entry.get("pvPower") or entry.get("solarPower") or entry.get("pv") or 0
                consumption = entry.get("consumption") or entry.get("homePower") or entry.get("home") or 0
                battery_soc = entry.get("batterySoc") or entry.get("stateOfCharge") or entry.get("soc") or 0

                # Grid: positiv = Bezug, negativ = Einspeisung
                grid_power = entry.get("gridPower") or entry.get("grid") or 0
                grid_in = entry.get("gridPowerIn") or entry.get("gridIn") or entry.get("gridConsumption") or 0
                grid_out = entry.get("gridPowerOut") or entry.get("gridOut") or entry.get("gridFeedIn") or 0

                # Falls nur kombinierter Wert vorhanden
                if grid_power and not grid_in and not grid_out:
                    grid_in = max(0, grid_power)
                    grid_out = abs(min(0, grid_power))

                # Batterie: positiv = Laden, negativ = Entladen
                battery_power = entry.get("batteryPower") or entry.get("batPower") or 0
                bat_in = entry.get("batPowerIn") or entry.get("batteryCharge") or 0
                bat_out = entry.get("batPowerOut") or entry.get("batteryDischarge") or 0

                # Falls nur kombinierter Wert vorhanden
                if battery_power and not bat_in and not bat_out:
                    bat_in = max(0, battery_power)
                    bat_out = abs(min(0, battery_power))

                data_entry = {
                    "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                    "date": timestamp.strftime("%Y-%m-%d"),
                    "time": timestamp.strftime("%H:%M"),
                    "resolution": "15min",
                    # Leistung in W
                    "pvPower": pv_power,
                    "pv_power": pv_power,
                    "batteryPower": battery_power,
                    "battery_power": battery_power,
                    "battery_charge": bat_in,
                    "battery_discharge": bat_out,
                    "gridPower": grid_power,
                    "grid_power": grid_power,
                    "grid_draw": grid_in,
                    "grid_feed": grid_out,
                    "consumption": consumption,
                    "homePower": consumption,
                    "batterySoc": battery_soc,
                    "battery_soc": battery_soc,
                    "gridFeedIn": grid_out,
                    "gridConsumption": grid_in,
                }

                all_data.append(data_entry)

            except Exception as e:
                print(f"Fehler beim Verarbeiten eines Eintrags: {e}")
                continue

        # Nach Timestamp sortieren
        all_data.sort(key=lambda x: x.get("timestamp", ""))

        # Bei Tages-Auflösung aggregieren
        if resolution == "day":
            all_data = self._aggregate_to_days(all_data)
        elif resolution == "hour":
            all_data = self._aggregate_to_hours(all_data)

        return all_data

    def _aggregate_to_days(self, data: list) -> list:
        """Aggregiert 15-Minuten-Daten zu Tagesdaten."""
        if not data:
            return []

        days = {}
        for entry in data:
            date = entry.get("date")
            if date not in days:
                days[date] = {
                    "timestamp": f"{date}T00:00:00",
                    "date": date,
                    "time": "00:00",
                    "resolution": "day",
                    "pv_power": 0,
                    "pvPower": 0,
                    "consumption": 0,
                    "homePower": 0,
                    "grid_draw": 0,
                    "gridConsumption": 0,
                    "grid_feed": 0,
                    "gridFeedIn": 0,
                    "battery_charge": 0,
                    "battery_discharge": 0,
                    "battery_soc": 0,
                    "batterySoc": 0,
                    "_count": 0,
                    "_soc_sum": 0
                }

            d = days[date]
            # Energie summieren (W * 0.25h = Wh für 15-Min-Intervalle)
            d["pv_power"] += entry.get("pv_power", 0) * 0.25
            d["pvPower"] = d["pv_power"]
            d["consumption"] += entry.get("consumption", 0) * 0.25
            d["homePower"] = d["consumption"]
            d["grid_draw"] += entry.get("grid_draw", 0) * 0.25
            d["gridConsumption"] = d["grid_draw"]
            d["grid_feed"] += entry.get("grid_feed", 0) * 0.25
            d["gridFeedIn"] = d["grid_feed"]
            d["battery_charge"] += entry.get("battery_charge", 0) * 0.25
            d["battery_discharge"] += entry.get("battery_discharge", 0) * 0.25
            d["_soc_sum"] += entry.get("battery_soc", 0)
            d["_count"] += 1

        # SOC-Durchschnitt berechnen und temporäre Felder entfernen
        result = []
        for date in sorted(days.keys()):
            d = days[date]
            if d["_count"] > 0:
                d["battery_soc"] = d["_soc_sum"] / d["_count"]
                d["batterySoc"] = d["battery_soc"]
            del d["_count"]
            del d["_soc_sum"]
            result.append(d)

        return result

    def _aggregate_to_hours(self, data: list) -> list:
        """Aggregiert 15-Minuten-Daten zu Stundendaten."""
        if not data:
            return []

        hours = {}
        for entry in data:
            ts = entry.get("timestamp", "")
            if len(ts) >= 13:
                hour_key = ts[:13] + ":00:00"
            else:
                continue

            if hour_key not in hours:
                hours[hour_key] = {
                    "timestamp": hour_key,
                    "date": entry.get("date"),
                    "time": hour_key[11:16],
                    "resolution": "hour",
                    "pv_power": 0,
                    "pvPower": 0,
                    "consumption": 0,
                    "homePower": 0,
                    "grid_draw": 0,
                    "gridConsumption": 0,
                    "grid_feed": 0,
                    "gridFeedIn": 0,
                    "battery_charge": 0,
                    "battery_discharge": 0,
                    "battery_soc": 0,
                    "batterySoc": 0,
                    "_count": 0,
                    "_soc_sum": 0
                }

            h = hours[hour_key]
            h["pv_power"] += entry.get("pv_power", 0) * 0.25
            h["pvPower"] = h["pv_power"]
            h["consumption"] += entry.get("consumption", 0) * 0.25
            h["homePower"] = h["consumption"]
            h["grid_draw"] += entry.get("grid_draw", 0) * 0.25
            h["gridConsumption"] = h["grid_draw"]
            h["grid_feed"] += entry.get("grid_feed", 0) * 0.25
            h["gridFeedIn"] = h["grid_feed"]
            h["battery_charge"] += entry.get("battery_charge", 0) * 0.25
            h["battery_discharge"] += entry.get("battery_discharge", 0) * 0.25
            h["_soc_sum"] += entry.get("battery_soc", 0)
            h["_count"] += 1

        result = []
        for key in sorted(hours.keys()):
            h = hours[key]
            if h["_count"] > 0:
                h["battery_soc"] = h["_soc_sum"] / h["_count"]
                h["batterySoc"] = h["battery_soc"]
            del h["_count"]
            del h["_soc_sum"]
            result.append(h)

        return result

    def disconnect(self):
        """Beendet die Session."""
        self.logged_in = False
        self.token = None
        self.session.close()
        print("Cloud API Verbindung getrennt")


def main():
    """Test-Funktion"""
    print("E3DC Cloud API Test (api.e3dc.com)")
    print("=" * 40)

    username = input("E3DC Benutzername (E-Mail): ")
    password = input("E3DC Passwort: ")

    api = E3DCCloudAPI(username, password)

    if api.login():
        print("\nRufe Live-Daten ab...")
        live = api.fetch_live_data()
        print(json.dumps(live, indent=2, default=str))

        print("\nRufe historische Daten ab (gestern)...")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        history = api.fetch_history_data(start_date=yesterday, end_date=yesterday, resolution="day")
        if "data" in history:
            print(f"Anzahl Datensätze: {len(history['data'])}")
            if history['data']:
                print("Erster Eintrag:", json.dumps(history['data'][0], indent=2))

        api.disconnect()
    else:
        print("Login fehlgeschlagen!")


if __name__ == "__main__":
    main()
