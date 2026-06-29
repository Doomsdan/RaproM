"""Desktop GUI prototype for RaProM."""

from __future__ import annotations

import logging
import math
import queue
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


LOGGER_NAME = "raprom"


@dataclass(frozen=True)
class GuiProcessSettings:
    """Validated settings collected from the GUI."""

    input_path: Path
    integration_time: int
    antenna_height: float
    adjust_m: float
    output_dir: Path | None
    correct: bool


@dataclass(frozen=True)
class FileProgress:
    """Progress information for the currently processed raw file."""

    index: int
    total: int
    path: Path


def parse_optional_float(value: str, default: float = math.nan) -> float:
    """Return *default* for empty text, otherwise parse a float."""
    text = value.strip()
    if not text:
        return default
    return float(text.replace(",", "."))


def build_process_settings(
    input_path: str,
    integration_time: str,
    antenna_height: str,
    adjust_m: str,
    output_dir: str,
    correct: bool,
) -> GuiProcessSettings:
    """Validate text fields and return processing settings."""
    source = Path(input_path).expanduser()
    if not input_path.strip():
        raise ValueError("Bitte eine .raw-Datei oder einen Ordner auswaehlen.")
    if not source.exists():
        raise ValueError(f"Eingabepfad existiert nicht: {source}")
    if source.is_file() and source.suffix.lower() != ".raw":
        raise ValueError("Einzeldateien muessen die Endung .raw haben.")

    try:
        parsed_integration_time = int(integration_time)
    except ValueError as exc:
        raise ValueError("Integrationszeit muss eine ganze Zahl in Sekunden sein.") from exc
    if parsed_integration_time <= 0:
        raise ValueError("Integrationszeit muss groesser als 0 sein.")

    try:
        parsed_antenna_height = parse_optional_float(antenna_height)
        parsed_adjust_m = parse_optional_float(adjust_m, default=1.0)
    except ValueError as exc:
        raise ValueError("Antennenhoehe und Kalibrierfaktor muessen Zahlen sein.") from exc

    destination = Path(output_dir).expanduser() if output_dir.strip() else None
    return GuiProcessSettings(
        input_path=source,
        integration_time=parsed_integration_time,
        antenna_height=parsed_antenna_height,
        adjust_m=parsed_adjust_m,
        output_dir=destination,
        correct=correct,
    )


def find_raw_files(input_path: Path) -> list[Path]:
    """Return selected raw file(s) in deterministic processing order."""
    if input_path.is_file():
        return [input_path]
    from .io import list_raw_files

    return list_raw_files(input_path)


def process_selected_path(settings: GuiProcessSettings, progress_callback=None) -> list[str]:
    """Process a selected raw file or all raw files in a selected folder."""
    prepare_directory, process_raw_file = _get_processors()
    logger = logging.getLogger(LOGGER_NAME)
    output_dir = str(settings.output_dir) if settings.output_dir else None
    if settings.input_path.is_file():
        raw_files = [settings.input_path]
        all_raw_files = raw_files
    else:
        raw_files, all_raw_files = prepare_directory(settings.input_path, output_dir=output_dir, correct=settings.correct)
    logger.info("Found %s raw file(s) in %s", len(all_raw_files), settings.input_path)

    outputs = []
    for index, raw_file in enumerate(raw_files, start=1):
        if progress_callback is not None:
            progress_callback(FileProgress(index, len(raw_files), raw_file))
        logger.info("Starting file %s of %s: %s", index, len(raw_files), raw_file)
        outputs.append(
            process_raw_file(
                raw_file,
                settings.integration_time,
                antenna_height=settings.antenna_height,
                adjust_m=settings.adjust_m,
                correct=settings.correct,
                output_dir=output_dir,
            )
        )
    return outputs


def _get_processors():
    from .netcdf import prepare_directory, process_raw_file

    return prepare_directory, process_raw_file


class QueueLogHandler(logging.Handler):
    """Logging handler that forwards records to the Tk event queue."""

    def __init__(self, event_queue: queue.Queue[tuple[str, object]]) -> None:
        super().__init__()
        self.event_queue = event_queue

    def emit(self, record: logging.LogRecord) -> None:
        self.event_queue.put(("log", self.format(record)))


class RapromGui(tk.Tk):
    """Small cross-platform desktop prototype for processing MRR raw data."""

    def __init__(self) -> None:
        super().__init__()
        self.title("RaProM")
        self.minsize(860, 620)

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.log_handler: QueueLogHandler | None = None
        self.processing_started_at: float | None = None
        self.last_heartbeat_at: float | None = None

        self.input_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.integration_time = tk.StringVar(value="60")
        self.antenna_height = tk.StringVar()
        self.adjust_m = tk.StringVar(value="1.0")
        self.correct = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Bereit")
        self.progress_detail = tk.StringVar(value="Keine Verarbeitung aktiv")

        self._configure_style()
        self._build_layout()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_events)
        self.after(1000, self._update_runtime)

    def _configure_style(self) -> None:
        self.style = ttk.Style(self)
        self.style.configure("TFrame", padding=0)
        self.style.configure("Header.TLabel", font=("", 16, "bold"))
        self.style.configure("Status.TLabel", foreground="#0f5f4a")
        self.style.configure("Danger.TLabel", foreground="#9f2d20")
        self.style.configure("Primary.TButton", padding=(12, 7))

    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="RaProM Datenverarbeitung", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.status, style="Status.TLabel").grid(row=0, column=1, sticky="e")

        notebook = ttk.Notebook(root)
        notebook.grid(row=1, column=0, sticky="nsew")
        root.rowconfigure(1, weight=1)

        start_tab = ttk.Frame(notebook, padding=16)
        settings_tab = ttk.Frame(notebook, padding=16)
        notebook.add(start_tab, text="Startseite")
        notebook.add(settings_tab, text="Einstellungen")
        self._build_start_tab(start_tab)
        self._build_settings_tab(settings_tab)

    def _build_start_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(4, weight=1)

        input_group = ttk.LabelFrame(parent, text="Eingabe", padding=14)
        input_group.grid(row=0, column=0, sticky="ew")
        input_group.columnconfigure(0, weight=1)
        ttk.Entry(input_group, textvariable=self.input_path).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(input_group, text="Datei", command=self._choose_file).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(input_group, text="Ordner", command=self._choose_folder).grid(row=0, column=2)

        output_group = ttk.LabelFrame(parent, text="Ausgabe", padding=14)
        output_group.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        output_group.columnconfigure(0, weight=1)
        ttk.Entry(output_group, textvariable=self.output_dir).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(output_group, text="Zielordner", command=self._choose_output_folder).grid(row=0, column=1)

        controls = ttk.Frame(parent)
        controls.grid(row=2, column=0, sticky="ew", pady=(14, 10))
        controls.columnconfigure(1, weight=1)
        self.run_button = ttk.Button(controls, text="Verarbeitung starten", style="Primary.TButton", command=self._start_processing)
        self.run_button.grid(row=0, column=0, sticky="w")
        self.progress = ttk.Progressbar(controls, mode="indeterminate")
        self.progress.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        ttk.Label(parent, textvariable=self.progress_detail, foreground="#575757").grid(
            row=3, column=0, sticky="w", pady=(0, 10)
        )

        log_group = ttk.LabelFrame(parent, text="Log", padding=10)
        log_group.grid(row=4, column=0, sticky="nsew")
        log_group.columnconfigure(0, weight=1)
        log_group.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_group, height=14, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_group, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _build_settings_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)

        fields = [
            ("Integrationszeit [s]", self.integration_time),
            ("Antennenhoehe [m]", self.antenna_height),
            ("Kalibrierfaktor M", self.adjust_m),
        ]
        for row, (label, variable) in enumerate(fields):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=7, padx=(0, 14))
            ttk.Entry(parent, textvariable=variable, width=18).grid(row=row, column=1, sticky="w", pady=7)

        ttk.Checkbutton(parent, text="Raw-Dateien vor Verarbeitung korrigieren", variable=self.correct).grid(
            row=len(fields), column=0, columnspan=2, sticky="w", pady=(12, 0)
        )

        hint = (
            "Leere Antennenhoehe bedeutet: Hoehen aus der Raw-Datei werden als Hoehe ueber Grund verwendet."
        )
        ttk.Label(parent, text=hint, foreground="#575757", wraplength=560).grid(
            row=len(fields) + 1, column=0, columnspan=2, sticky="w", pady=(18, 0)
        )

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(title="Raw-Datei auswaehlen", filetypes=[("MRR raw", "*.raw"), ("Alle Dateien", "*.*")])
        if path:
            self.input_path.set(path)

    def _choose_folder(self) -> None:
        path = filedialog.askdirectory(title="Ordner mit Raw-Dateien auswaehlen")
        if path:
            self.input_path.set(path)

    def _choose_output_folder(self) -> None:
        path = filedialog.askdirectory(title="Zielordner auswaehlen")
        if path:
            self.output_dir.set(path)

    def _start_processing(self) -> None:
        try:
            settings = build_process_settings(
                self.input_path.get(),
                self.integration_time.get(),
                self.antenna_height.get(),
                self.adjust_m.get(),
                self.output_dir.get(),
                self.correct.get(),
            )
        except ValueError as exc:
            messagebox.showerror("Einstellungen pruefen", str(exc))
            return

        self._clear_log()
        self._configure_processing_logging()
        self.status.set("Laeuft")
        self.progress_detail.set("Startet ...")
        self.processing_started_at = time.monotonic()
        self.last_heartbeat_at = self.processing_started_at
        self.run_button.state(["disabled"])
        self.progress.start(10)
        self.worker = threading.Thread(target=self._run_worker, args=(settings,), daemon=True)
        self.worker.start()

    def _run_worker(self, settings: GuiProcessSettings) -> None:
        try:
            outputs = process_selected_path(settings, progress_callback=self._queue_file_progress)
        except Exception as exc:  # pragma: no cover - exercised manually through the GUI
            logging.getLogger(LOGGER_NAME).exception("Verarbeitung fehlgeschlagen")
            self.events.put(("error", str(exc)))
        else:
            self.events.put(("done", outputs))

    def _queue_file_progress(self, progress: FileProgress) -> None:
        self.events.put(("file_progress", progress))

    def _configure_processing_logging(self) -> None:
        logger = logging.getLogger(LOGGER_NAME)
        logger.setLevel(logging.INFO)
        if self.log_handler is not None:
            logger.removeHandler(self.log_handler)
        self.log_handler = QueueLogHandler(self.events)
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%H:%M:%S"))
        logger.addHandler(self.log_handler)

    def _poll_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "log":
                    self._append_log(str(payload))
                elif event == "file_progress":
                    progress = payload
                    if isinstance(progress, FileProgress):
                        self._set_progress_detail(progress)
                elif event == "done":
                    self._finish_processing("Fertig")
                    outputs = payload if isinstance(payload, list) else []
                    self._append_log(f"Fertig. Erzeugte NetCDF-Dateien: {len(outputs)}")
                    if outputs:
                        self._append_log("\n".join(str(output) for output in outputs))
                elif event == "error":
                    self._finish_processing("Fehler")
                    messagebox.showerror("Verarbeitung fehlgeschlagen", str(payload))
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _finish_processing(self, status: str) -> None:
        self.progress.stop()
        self.run_button.state(["!disabled"])
        self.status.set(status)
        if self.processing_started_at is not None:
            elapsed = time.monotonic() - self.processing_started_at
            self.progress_detail.set(f"{status} nach {format_duration(elapsed)}")
        self.processing_started_at = None
        self.last_heartbeat_at = None

    def _set_progress_detail(self, progress: FileProgress) -> None:
        elapsed = 0.0
        if self.processing_started_at is not None:
            elapsed = time.monotonic() - self.processing_started_at
        self.progress_detail.set(
            f"Datei {progress.index} von {progress.total} | Laufzeit {format_duration(elapsed)} | {progress.path.name}"
        )

    def _update_runtime(self) -> None:
        if self.worker is not None and self.worker.is_alive() and self.processing_started_at is not None:
            elapsed = time.monotonic() - self.processing_started_at
            self.status.set(f"Laeuft seit {format_duration(elapsed)}")
            if self.last_heartbeat_at is not None and time.monotonic() - self.last_heartbeat_at >= 30:
                self._append_log(f"Noch aktiv ... Laufzeit {format_duration(elapsed)}")
                self.last_heartbeat_at = time.monotonic()
        self.after(1000, self._update_runtime)

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _on_close(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            if not messagebox.askyesno("Verarbeitung laeuft", "Die Verarbeitung laeuft noch. Trotzdem schliessen?"):
                return
        self.destroy()


def main() -> int:
    app = RapromGui()
    app.mainloop()
    return 0


def format_duration(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


if __name__ == "__main__":
    raise SystemExit(main())
