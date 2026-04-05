#!/usr/bin/env python3
"""
Test-Skript für E3DC Cloud API Verbindung
Testet die Verbindung mit der offiziellen API (api.e3dc.com)
"""

from e3dc_cloud_api import E3DCCloudAPI

def test_connection():
    print("=== E3DC Cloud API Verbindungstest ===")
    print("API: api.e3dc.com (offizielle REST API)")
    print("=" * 40)

    # Eingabe der Zugangsdaten
    username = input("\nE3DC Benutzername (E-Mail): ").strip()
    password = input("E3DC Passwort: ").strip()

    print(f"\nVerbinde mit:")
    print(f"  Benutzer: {username}")
    print(f"  Passwort: {'*' * len(password)}")

    print("\nVersuche Verbindung aufzubauen...")

    api = E3DCCloudAPI(username, password)

    if api.login():
        print(f"\n✓ Verbindung erfolgreich!")
        print(f"  Seriennummer: {api.serial_number}")

        # Live-Daten abrufen
        print("\nRufe Live-Daten ab...")
        live = api.fetch_live_data()

        if "error" not in live:
            print("\nLive-Daten:")
            print(f"  PV-Leistung: {live.get('pvPower', 0)} W")
            print(f"  Verbrauch: {live.get('homePower', 0)} W")
            print(f"  Batterie SOC: {live.get('batterySoc', 0)} %")
            print(f"  Netz: {live.get('gridPower', 0)} W")
            print(f"  Autarkie: {live.get('autarky', 0)} %")
        else:
            print(f"\n✗ Fehler beim Abrufen der Live-Daten: {live.get('error')}")

        api.disconnect()
        print("\n✓ Test abgeschlossen")

    else:
        print(f"\n✗ Verbindung fehlgeschlagen!")
        print("\nMögliche Ursachen:")
        print("  1. Falsche E-Mail-Adresse")
        print("  2. Falsches Passwort")
        print("  3. API nicht erreichbar")
        print("\nBitte prüfen Sie Ihre Zugangsdaten im E3DC Portal:")
        print("  https://my.e3dc.com/")


if __name__ == "__main__":
    test_connection()
