# RaproM

Installierbares Python-Paket fuer die Verarbeitung und Korrektur von MRR2
Radar-Rohdaten.

## Installation

```powershell
python -m pip install -e .
```

Die Conda-Umgebung kann weiterhin ueber `raprom_env.yml` erstellt werden.

## CLI

Raw-Dateien in einem Ordner zu NetCDF verarbeiten:

```powershell
raprom process "D:\Mrrdata" --integration-time 60
```

Nur Raw-Dateien korrigieren:

```powershell
raprom correct "D:\Mrrdata"
```

Optionen aus dem alten Skript sind als CLI-Flags verfuegbar:

```powershell
raprom process "D:\Mrrdata" -i 60 --antenna-height 120 -M 1.05
```
