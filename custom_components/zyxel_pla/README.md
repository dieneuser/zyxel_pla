# Zyxel PLA Powerline Integration for Home Assistant

Custom Integration für Zyxel PLA6457 (und ähnliche G.hn Powerline-Adapter mit Weboberfläche).

## Features

- **Login** über das Web-Interface (Cookie-basiert)
- Auslesen von:
  - MAC-Adresse
  - Seriennummer
  - Firmware-Version
  - Hardware-Version
  - Uptime
  - Node Type (DOMAIN_MASTER / END_POINT)
  - Domain Name
  - **PHY TX / RX Geschwindigkeiten** (Mbps) zum Remote-Adapter
  - Remote MAC-Adresse
- Device-Grouping in Home Assistant
- Config-Flow (UI-Setup)

## Installation

1. Kopiere den Ordner `zyxel_pla` nach  
   `config/custom_components/zyxel_pla`

2. Home Assistant neu starten

3. **Einstellungen → Geräte & Dienste → Integration hinzufügen**  
   → nach **Zyxel PLA** suchen

4. IP-Adresse und Passwort des Adapters eingeben

## Sensoren

| Sensor              | Beschreibung                          | Einheit |
|---------------------|---------------------------------------|---------|
| MAC Address         | Eigene MAC                            | -       |
| Serial Number       | Seriennummer                          | -       |
| Firmware Version    | FW-Version                            | -       |
| PHY TX Rate         | Sende-Rate zum Partner                | Mbit/s  |
| PHY RX Rate         | Empfangs-Rate vom Partner             | Mbit/s  |
| Remote MAC Address  | MAC des verbundenen Adapters          | -       |
| Node Type           | DOMAIN_MASTER / END_POINT             | -       |
| Uptime              | Laufzeit                              | -       |

Weitere Sensoren (Hardware-Version, Domain Name usw.) sind standardmäßig deaktiviert und können in der Entity-Registry aktiviert werden.

## Hinweise

- Die Integration pollt standardmäßig alle **60 Sekunden**.
- Die PHY-Raten werden aus den internen Werten der Webseite berechnet (`value * 32 / 1000`), genau wie die Weboberfläche selbst.
- Bei mehreren verbundenen Geräten wird aktuell der **erste** Remote-Adapter als Haupt-Link angezeigt. Die komplette Liste steckt im Coordinator-Data unter `connections`.

## Erweiterungen (optional)

Falls du mehrere Remote-Adapter als eigene Sensoren haben möchtest, kann man das leicht erweitern (dynamische Entities). Sag einfach Bescheid!

## Getestet mit

- Zyxel PLA6457 (Firmware V1.00 (ACAJ.2)C0)
