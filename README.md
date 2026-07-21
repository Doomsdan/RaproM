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

Wiederkehrende Parameter koennen in einer TOML- oder YAML-Datei gespeichert
werden. CLI-Flags ueberschreiben Werte aus der Datei:

```toml
[process]
path = "D:/Mrrdata"
integration_time = 60
radar_height = 120.0
output_dir = "D:/Mrrdata/Processed"
correct = true

[process.calibration]
adjust_m = 1.05
```

Start mit Konfiguration:

```powershell
raprom process --config raprom.example.toml
```

Der gleiche Aufruf kann einzelne Werte gezielt ueberschreiben:

```powershell
raprom process --config raprom.example.toml --integration-time 30
```

## Stationsdateien

Grunddaten einzelner Stationen koennen als YAML-Dateien im Ordner `stations/`
abgelegt werden. `stations/station-template.yaml` dient als Vorlage fuer neue
Stationen:

```yaml
station:
  id: station-a
  name: Station A
  timezone: Europe/Berlin
  location:
    latitude: 50.123
    longitude: 8.456
    altitude_m: 142.5
  instrument:
    serial_number: "0509106128"
    antenna_height_m: 120.0
  paths:
    raw_data: D:/Mrrdata/station-a
    output: D:/Mrrdata/station-a/Processed

process:
  path: D:/Mrrdata/station-a
  integration_time: 60
  antenna_height: 120.0
  output_dir: D:/Mrrdata/station-a/Processed
  correct: true
  calibration:
    adjust_m: 1.0
```

Der `station`-Block speichert nur die Grunddaten. Der `process`-Block kann
direkt fuer die Verarbeitung genutzt werden:

```powershell
raprom process --config stations/station-a.yaml
```

## Logging

Die CLI schreibt Statusmeldungen ueber Python-Logging auf die Konsole. Mit
`--log-file` werden dieselben Meldungen zusaetzlich in eine Datei geschrieben:

```powershell
raprom process "D:\Mrrdata" -i 60 --log-file raprom.log
```

Mehr Details gibt es mit `-v`, Debug-Ausgaben mit `-vv`. Mit `--quiet` werden
nur Warnungen und Fehler angezeigt.

## Performance-Regressionen pruefen

Fuer Optimierungen kann eine einzelne Raw-Datei verarbeitet und gegen eine
bekannte NetCDF-Referenz exakt verglichen werden:

```powershell
raprom benchmark "D:\Mrrdata\0101.raw" -i 60 --reference "D:\Mrrdata\0101-processed.nc" --output-dir ".\benchmark-output"
```

Der Befehl endet mit Fehlercode `1`, sobald Dimensionen, Variablen, Attribute
oder Datenwerte abweichen. NaN-Werte gelten nur dann als gleich, wenn sie an
denselben Positionen stehen.

## GUI-Prototyp

Eine einfache Desktop-Oberflaeche kann nach der Installation gestartet werden:

```powershell
raprom-gui
```

Die GUI verarbeitet entweder eine einzelne `.raw`-Datei oder alle `.raw`-Dateien
in einem Ordner. Integration Time, Antennenhoehe, Kalibrierfaktor, Korrektur und
Ausgabeordner koennen im Fenster gesetzt werden; Statusmeldungen erscheinen im
Logbereich. Waehrend der Verarbeitung zeigt die GUI die Laufzeit, die aktuell
verarbeitete Datei und regelmaessige "Noch aktiv ..."-Meldungen an.
