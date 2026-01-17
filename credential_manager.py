#!/usr/bin/env python3
"""
Credential Manager für E3DC
Verschlüsselt und verwaltet E3DC-Zugangsdaten mit Fernet-Verschlüsselung
"""

import json
import os
import base64
from pathlib import Path
from typing import Optional, Dict
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Konfiguration
CREDENTIALS_FILE = Path(__file__).parent / ".credentials.enc"
CONFIG_FILE = Path(__file__).parent / "config.json"
PBKDF2_ITERATIONS = 100000


class CredentialManager:
    """Verwaltet verschlüsselte Zugangsdaten"""

    @staticmethod
    def _derive_key(master_password: str, salt: bytes) -> bytes:
        """
        Leitet einen Verschlüsselungsschlüssel aus dem Master-Passwort ab.

        Args:
            master_password: Master-Passwort
            salt: Salt für die Key-Derivation

        Returns:
            32-Byte Schlüssel für Fernet
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

    @staticmethod
    def credentials_exist() -> bool:
        """
        Prüft ob verschlüsselte Credentials existieren.

        Returns:
            True wenn .credentials.enc existiert
        """
        return CREDENTIALS_FILE.exists()

    @staticmethod
    def save_credentials(
        username: str,
        password: str,
        ip_address: str,
        rscp_key: str,
        master_password: str
    ) -> bool:
        """
        Verschlüsselt und speichert E3DC-Credentials.

        Args:
            username: E3DC Benutzername
            password: E3DC Passwort
            ip_address: IP-Adresse des E3DC-Systems
            rscp_key: RSCP-Passwort
            master_password: Master-Passwort für Verschlüsselung

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            # Zufälliges Salt generieren
            salt = os.urandom(16)

            # Verschlüsselungsschlüssel ableiten
            key = CredentialManager._derive_key(master_password, salt)
            fernet = Fernet(key)

            # Credentials als JSON
            credentials_data = {
                "username": username,
                "password": password,
                "ip_address": ip_address,
                "rscp_key": rscp_key
            }
            credentials_json = json.dumps(credentials_data)

            # Verschlüsseln
            encrypted_data = fernet.encrypt(credentials_json.encode())

            # Speichern: Salt + verschlüsselte Daten
            storage_data = {
                "salt": base64.b64encode(salt).decode(),
                "data": base64.b64encode(encrypted_data).decode()
            }

            with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
                json.dump(storage_data, f, indent=2)

            # Dateiberechtigungen setzen (nur Eigentümer kann lesen/schreiben)
            if os.name != "nt":  # Unix-basierte Systeme
                os.chmod(CREDENTIALS_FILE, 0o600)

            return True

        except Exception as e:
            print(f"Fehler beim Speichern der Credentials: {e}")
            return False

    @staticmethod
    def load_credentials(master_password: str) -> Optional[Dict[str, str]]:
        """
        Lädt und entschlüsselt E3DC-Credentials.

        Args:
            master_password: Master-Passwort für Entschlüsselung

        Returns:
            Dictionary mit username, password, ip_address, rscp_key oder None bei Fehler
        """
        try:
            if not CREDENTIALS_FILE.exists():
                print("Keine gespeicherten Credentials gefunden")
                return None

            # Gespeicherte Daten laden
            with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                storage_data = json.load(f)

            salt = base64.b64decode(storage_data["salt"])
            encrypted_data = base64.b64decode(storage_data["data"])

            # Schlüssel ableiten
            key = CredentialManager._derive_key(master_password, salt)
            fernet = Fernet(key)

            # Entschlüsseln
            decrypted_data = fernet.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())

            return credentials

        except InvalidToken:
            print("Falsches Master-Passwort!")
            return None
        except Exception as e:
            print(f"Fehler beim Laden der Credentials: {e}")
            return None

    @staticmethod
    def migrate_from_config() -> Optional[Dict[str, str]]:
        """
        Liest Credentials aus der alten config.json (für Migration).
        DEPRECATED: Wird für alte Konfigurationen verwendet.

        Returns:
            Dictionary mit Credentials oder None falls nicht vorhanden
        """
        try:
            if not CONFIG_FILE.exists():
                return None

            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Prüfen ob "e3dc"-Sektion existiert
            if "e3dc" not in config:
                return None

            e3dc_config = config["e3dc"]

            # Prüfen ob alle erforderlichen Felder vorhanden sind (neues Format)
            if all(key in e3dc_config for key in ["username", "password", "ip_address", "rscp_key"]):
                return {
                    "username": e3dc_config["username"],
                    "password": e3dc_config["password"],
                    "ip_address": e3dc_config["ip_address"],
                    "rscp_key": e3dc_config["rscp_key"]
                }

            return None

        except Exception as e:
            print(f"Fehler beim Lesen der config.json: {e}")
            return None

    @staticmethod
    def remove_credentials_from_config() -> bool:
        """
        Entfernt die "e3dc"-Sektion aus config.json nach erfolgreicher Migration.

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            if not CONFIG_FILE.exists():
                return False

            # Backup erstellen
            backup_path = CONFIG_FILE.with_suffix(".json.bak")
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Backup speichern
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            # "e3dc"-Sektion entfernen
            if "e3dc" in config:
                del config["e3dc"]

            # Server-Konfiguration hinzufügen (falls noch nicht vorhanden)
            if "server" not in config:
                config["server"] = {
                    "host": "localhost",
                    "port": 5000,
                    "auto_open_browser": True
                }

            # Aktualisierte Config speichern
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            return True

        except Exception as e:
            print(f"Fehler beim Aktualisieren der config.json: {e}")
            return False

    @staticmethod
    def delete_credentials() -> bool:
        """
        Löscht die gespeicherten Credentials (für Reset).

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            if CREDENTIALS_FILE.exists():
                CREDENTIALS_FILE.unlink()
                return True
            return False
        except Exception as e:
            print(f"Fehler beim Löschen der Credentials: {e}")
            return False


# CLI-Test-Funktionen (für direktes Testen des Moduls)
def main():
    """Test-Funktion für Kommandozeilen-Nutzung"""
    import sys

    print("=== E3DC Credential Manager ===\n")

    if CredentialManager.credentials_exist():
        print("Gespeicherte Credentials gefunden.")
        master_pw = input("Master-Passwort eingeben: ")

        credentials = CredentialManager.load_credentials(master_pw)
        if credentials:
            print("\nCredentials erfolgreich geladen:")
            print(f"  Username: {credentials['username']}")
            print(f"  Password: {'*' * len(credentials['password'])}")
            print(f"  IP-Adresse: {credentials.get('ip_address', 'N/A')}")
            print(f"  RSCP-Key: {'*' * len(credentials.get('rscp_key', ''))}")
        else:
            print("Fehler beim Laden der Credentials.")
            sys.exit(1)
    else:
        print("Keine Credentials gefunden. Erstelle neue...")

        username = input("E3DC Benutzername: ")
        password = input("E3DC Passwort: ")
        ip_address = input("E3DC IP-Adresse: ")
        rscp_key = input("RSCP-Passwort: ")

        master_pw = input("\nMaster-Passwort erstellen (min. 8 Zeichen): ")
        if len(master_pw) < 8:
            print("Master-Passwort zu kurz!")
            sys.exit(1)

        master_pw_confirm = input("Master-Passwort bestätigen: ")
        if master_pw != master_pw_confirm:
            print("Passwörter stimmen nicht überein!")
            sys.exit(1)

        if CredentialManager.save_credentials(username, password, ip_address, rscp_key, master_pw):
            print("\nCredentials erfolgreich gespeichert!")
        else:
            print("Fehler beim Speichern!")
            sys.exit(1)


if __name__ == "__main__":
    main()
