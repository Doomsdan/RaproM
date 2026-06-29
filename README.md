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

Korrigierte Dateien werden in `D:\Mrrdata\CorrectedRaw` geschrieben. Die
Originaldateien bleiben unveraendert im Eingabeordner.

Optionen aus dem alten Skript sind als CLI-Flags verfuegbar:

```powershell
raprom process "D:\Mrrdata" -i 60 --antenna-height 120 -M 1.05
```

## Logging

Die CLI schreibt Statusmeldungen ueber Python-Logging auf die Konsole. Mit
`--log-file` werden dieselben Meldungen zusaetzlich in eine Datei geschrieben:

```powershell
raprom process "D:\Mrrdata" -i 60 --log-file raprom.log
```

Mehr Details gibt es mit `-v`, Debug-Ausgaben mit `-vv`. Mit `--quiet` werden
nur Warnungen und Fehler angezeigt.
