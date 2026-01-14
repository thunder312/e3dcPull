#!/usr/bin/env python3
"""
E3DC Browser Automation
Lädt CSV-Daten vom E3DC-Portal mittels Playwright
"""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Konfiguration laden
CONFIG_PATH = Path(__file__).parent / "config.json"
DATA_PATH = Path(__file__).parent / "data"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_e3dc_csv(start_date: str, end_date: str, headless: bool = False):
    """
    Lädt CSV-Daten vom E3DC-Portal.

    Args:
        start_date: Startdatum im Format "DD.MM.YYYY"
        end_date: Enddatum im Format "DD.MM.YYYY"
        headless: Browser ohne GUI ausführen (Standard: False für bessere Kompatibilität)
    """
    config = load_config()
    username = config["e3dc"]["username"]
    password = config["e3dc"]["password"]
    dashboard_url = config["e3dc"]["dashboard_url"]

    DATA_PATH.mkdir(exist_ok=True)

    with sync_playwright() as p:
        print("Starte Browser...")
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            accept_downloads=True,
            locale="de-DE"
        )
        page = context.new_page()

        try:
            # Login-Seite aufrufen
            print("Öffne E3DC Portal...")
            page.goto("https://my.e3dc.com/login", wait_until="networkidle")
            time.sleep(2)

            # Login-Formular ausfüllen
            print("Führe Login durch...")

            # Warte bis die Seite geladen ist
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # Alle input-Felder finden (erstes = E-Mail, zweites = Passwort)
            inputs = page.locator('input').all()
            print(f"Gefundene Input-Felder: {len(inputs)}")

            if len(inputs) >= 2:
                # Erstes Textfeld = E-Mail
                inputs[0].fill(username)
                time.sleep(0.5)

                # Zweites Feld = Passwort
                inputs[1].fill(password)
                time.sleep(0.5)
            else:
                # Fallback: Versuche verschiedene Selektoren
                email_field = page.locator('input:not([type="password"]):not([type="hidden"])').first
                email_field.fill(username)
                password_field = page.locator('input[type="password"]').first
                password_field.fill(password)

            # Login-Button klicken - kann button, a, div, span sein
            # Suche nach Element mit Text "Anmelden"
            login_selectors = [
                'text="Anmelden"',
                ':has-text("Anmelden")',
                'button:has-text("Anmelden")',
                '[role="button"]:has-text("Anmelden")',
                'a:has-text("Anmelden")',
                'div:has-text("Anmelden")',
            ]

            clicked = False
            for selector in login_selectors:
                try:
                    elem = page.locator(selector).first
                    if elem.is_visible(timeout=2000):
                        print(f"Login-Button gefunden: {selector}")
                        elem.click()
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                # Fallback: Enter-Taste drücken
                print("Kein Button gefunden, drücke Enter...")
                page.keyboard.press("Enter")

            # Warten bis Login-Prozess abgeschlossen
            print("Warte auf Login-Abschluss...")
            time.sleep(5)

            # Cookie-Banner behandeln - verschiedene Selektoren
            cookie_selectors = [
                'text="Alle akzeptieren"',
                'text="cookies.accept-all"',
                'button:has-text("accept-all")',
                'button:has-text("akzeptieren")',
                '[data-testid="cookies-accept-all"]',
            ]

            for selector in cookie_selectors:
                try:
                    cookie_btn = page.locator(selector).first
                    if cookie_btn.is_visible(timeout=2000):
                        print(f"Cookie-Banner akzeptieren mit: {selector}")
                        cookie_btn.click()
                        time.sleep(2)
                        break
                except:
                    continue

            print(f"Eingeloggt! URL: {page.url}")

            # Zum spezifischen Dashboard navigieren
            print(f"Navigiere zu: {dashboard_url}")
            page.goto(dashboard_url, wait_until="networkidle")
            time.sleep(3)

            # Nochmal Cookie-Banner prüfen
            for selector in cookie_selectors:
                try:
                    cookie_btn = page.locator(selector).first
                    if cookie_btn.is_visible(timeout=2000):
                        print(f"Cookie-Banner erneut akzeptieren: {selector}")
                        cookie_btn.click()
                        time.sleep(2)
                        break
                except:
                    continue

            # Seite mehrmals neu laden um Übersetzungen zu triggern
            print("Lade Seite neu für Übersetzungen...")
            for reload_attempt in range(3):
                page.reload(wait_until="networkidle")
                time.sleep(3)

                page_content = page.content()
                if "Solarproduktion" in page_content or "Hausverbrauch" in page_content:
                    print(f"Übersetzungen geladen nach {reload_attempt + 1} Reload(s)!")
                    break
                print(f"Reload {reload_attempt + 1}/3...")

            time.sleep(2)

            # Screenshot für Debug
            page.screenshot(path=str(DATA_PATH / "debug_dashboard.png"))
            print("Screenshot gespeichert: data/debug_dashboard.png")

            # Nach Export/Download Button suchen
            print("Suche Export-Funktion...")

            # Verschiedene mögliche Export-Buttons
            export_selectors = [
                'button:has-text("Export")',
                'button:has-text("CSV")',
                'button:has-text("Download")',
                '[aria-label*="export"]',
                '[aria-label*="Export"]',
                '[aria-label*="download"]',
                '[data-testid*="export"]',
                '.export-button',
                '#export-btn'
            ]

            export_button = None
            for selector in export_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=1000):
                        export_button = btn
                        print(f"Export-Button gefunden: {selector}")
                        break
                except:
                    continue

            if export_button:
                # Datum-Bereich einstellen
                print(f"Setze Datumsbereich: {start_date} - {end_date}")

                # 1. Erst Hinweis-Dialog schließen falls vorhanden
                try:
                    close_btn = page.locator('button[aria-label="close"], svg[data-testid="CloseIcon"], button:has(svg)').first
                    if close_btn.is_visible(timeout=1000):
                        close_btn.click()
                        time.sleep(1)
                        print("  Hinweis-Dialog geschlossen")
                except:
                    pass

                # 2. Checkbox "Erweiterter Zeitraum" aktivieren
                # Die Checkbox ist ein input[type="checkbox"] vor dem Text "customRangeCheckbox"
                try:
                    # Methode 1: Finde das Checkbox-Input direkt
                    # Suche nach allen Checkboxen und prüfe welche in der Nähe des richtigen Texts ist
                    checkboxes = page.locator('input[type="checkbox"], [role="checkbox"]').all()
                    print(f"  Gefundene Checkboxen: {len(checkboxes)}")

                    checkbox_clicked = False

                    # Versuche die erste sichtbare Checkbox im Header-Bereich zu finden
                    for i, cb in enumerate(checkboxes[:5]):
                        try:
                            if cb.is_visible(timeout=500):
                                # Prüfe ob diese Checkbox im oberen Bereich ist (Chart-Header)
                                box = cb.bounding_box()
                                if box and box['y'] < 500:  # Oberer Bereich der Seite
                                    print(f"  Klicke Checkbox {i} bei y={box['y']}")
                                    cb.click()
                                    checkbox_clicked = True
                                    time.sleep(2)
                                    break
                        except:
                            continue

                    if not checkbox_clicked:
                        # Fallback: Klicke auf das Label/Span neben der Checkbox
                        label = page.locator('span:has-text("customRangeCheckbox"), span:has-text("Erweiterter Zeitraum")').first
                        if label.is_visible(timeout=1000):
                            # Finde die Checkbox links vom Label
                            label_box = label.bounding_box()
                            if label_box:
                                # Klicke 30px links vom Label (dort sollte die Checkbox sein)
                                page.mouse.click(label_box['x'] - 30, label_box['y'] + label_box['height'] / 2)
                                print(f"  Checkbox per Koordinaten geklickt")
                                checkbox_clicked = True
                                time.sleep(2)

                    # Screenshot nach Checkbox-Klick
                    page.screenshot(path=str(DATA_PATH / "debug_after_checkbox.png"))

                    # 2. Jetzt sollten Datumsfelder erscheinen - suche danach
                    time.sleep(1)

                    # Suche nach Datums-Inputs (können verschiedene Typen sein)
                    date_inputs = page.locator('input[type="date"], input[type="text"][placeholder*="Datum"], input[type="text"][value*="2026"]').all()
                    print(f"  Gefundene Datumsfelder: {len(date_inputs)}")

                    if len(date_inputs) >= 2:
                        # Startdatum
                        print(f"  Setze Startdatum: {start_date}")
                        date_inputs[0].click()
                        date_inputs[0].fill("")
                        date_inputs[0].type(start_date)
                        time.sleep(0.5)

                        # Enddatum
                        print(f"  Setze Enddatum: {end_date}")
                        date_inputs[1].click()
                        date_inputs[1].fill("")
                        date_inputs[1].type(end_date)
                        time.sleep(0.5)

                        # Enter drücken um zu bestätigen
                        page.keyboard.press("Enter")
                        time.sleep(2)

                    elif len(date_inputs) == 1:
                        # Möglicherweise ein Datepicker-Dialog
                        print("  Nur ein Datumsfeld gefunden - versuche Kalender")

                    # Screenshot nach Datum-Eingabe
                    page.screenshot(path=str(DATA_PATH / "debug_after_date.png"))

                except Exception as e:
                    print(f"  Fehler beim Setzen des Datums: {e}")

                # Download starten
                print("Starte Download...")
                with page.expect_download(timeout=60000) as download_info:
                    export_button.click()

                download = download_info.value
                download_path = DATA_PATH / f"e3dc_export_{start_date.replace('.', '-')}_{end_date.replace('.', '-')}.csv"
                download.save_as(str(download_path))
                print(f"CSV gespeichert: {download_path}")

                return str(download_path)
            else:
                print("Kein Export-Button gefunden. Prüfe Screenshot für manuelle Analyse.")

                # Alle sichtbaren Buttons ausgeben
                buttons = page.locator('button').all()
                print(f"\nGefundene Buttons ({len(buttons)}):")
                for i, btn in enumerate(buttons[:20]):
                    try:
                        text = btn.inner_text(timeout=500)
                        if text.strip():
                            print(f"  {i}: {text[:50]}")
                    except:
                        pass

                return None

        except PlaywrightTimeout as e:
            print(f"Timeout: {e}")
            page.screenshot(path=str(DATA_PATH / "debug_error.png"))
            return None
        except Exception as e:
            print(f"Fehler: {e}")
            page.screenshot(path=str(DATA_PATH / "debug_error.png"))
            return None
        finally:
            browser.close()


def fix_csv_headers_and_timestamps(csv_path: Path, start_date: str) -> Path:
    """
    Repariert die CSV-Datei: Ersetzt Platzhalter-Überschriften und rekonstruiert Zeitstempel.

    Args:
        csv_path: Pfad zur heruntergeladenen CSV
        start_date: Startdatum im Format "DD.MM.YYYY"

    Returns:
        Pfad zur reparierten CSV
    """
    # Korrekte deutsche Spaltenüberschriften (wie im Original-E3DC-Export)
    correct_headers = [
        '"Zeitstempel"',
        '"Ladezustand [%]"',
        '"Solarproduktion [W]"',
        '"Batterie Laden [W]"',
        '"Batterie Entladen [W]"',
        '"Netzeinspeisung [W]"',
        '"Netzbezug [W]"',
        '"Hausverbrauch [W]"',
        '"Abregelungsgrenze [W]"'
    ]

    # Startdatum parsen
    day, month, year = map(int, start_date.split('.'))
    current_time = datetime(year, month, day, 0, 0, 0)

    # CSV lesen
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    if len(lines) < 2:
        print("CSV ist leer oder hat keine Daten")
        return csv_path

    # Neue Zeilen erstellen
    new_lines = []

    # Header ersetzen
    new_lines.append(';'.join(correct_headers) + '\n')

    # Datenzeilen verarbeiten
    for i, line in enumerate(lines[1:], 1):
        parts = line.strip().split(';')
        if len(parts) < 2:
            continue

        # Zeitstempel generieren (15-Minuten-Intervalle)
        timestamp = current_time.strftime('%d.%m.%Y %H:%M:%S')
        current_time += timedelta(minutes=15)

        # Erste Spalte (Platzhalter-Zeitstempel) durch echten Zeitstempel ersetzen
        parts[0] = timestamp

        new_lines.append(';'.join(parts) + '\n')

    # Reparierte CSV speichern
    fixed_path = csv_path.parent / f"{csv_path.stem}_fixed.csv"
    with open(fixed_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"CSV repariert: {fixed_path}")
    print(f"  - {len(new_lines) - 1} Datensätze")
    print(f"  - Zeitraum: {start_date} bis {current_time.strftime('%d.%m.%Y %H:%M:%S')}")

    return fixed_path


if __name__ == "__main__":
    # Argumente parsen
    if len(sys.argv) >= 3:
        start = sys.argv[1]
        end = sys.argv[2]
    else:
        start = "01.01.2026"
        end = "05.01.2026"

    # Standard: sichtbarer Browser (besser für Übersetzungen)
    # --headless für unsichtbaren Browser
    headless = "--headless" in sys.argv

    print(f"E3DC CSV Download")
    print(f"Zeitraum: {start} - {end}")
    print(f"Modus: {'Headless' if headless else 'Sichtbar'}")
    print("-" * 40)

    result = fetch_e3dc_csv(start, end, headless=headless)

    if result:
        print(f"\nDownload erfolgreich: {result}")

        # CSV reparieren (Spaltenüberschriften und Zeitstempel)
        print("\nRepariere CSV (Überschriften und Zeitstempel)...")
        fixed_csv = fix_csv_headers_and_timestamps(Path(result), start)

        # Als e3dc_data.csv kopieren für HTML-Seite
        import shutil
        target = DATA_PATH / "e3dc_data.csv"
        shutil.copy(fixed_csv, target)
        print(f"\nKopiert nach: {target}")
        print("Laden Sie die HTML-Seite neu um die Daten zu sehen.")
    else:
        print("\nCSV-Download fehlgeschlagen. Prüfen Sie die Screenshots im data-Ordner.")
