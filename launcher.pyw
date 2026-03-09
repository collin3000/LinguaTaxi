#!/usr/bin/env python3
"""
LinguaTaxi — Live Caption & Translation
Desktop launcher with server management and browser integration.
"""

import json, os, platform, queue, re, signal, subprocess, sys, threading, time, webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ── Version & Paths ──

APP_NAME = "LinguaTaxi"
APP_FULL = "LinguaTaxi — Live Caption & Translation"
VERSION = "1.0.0"

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

# Determine app directory (where server.py lives)
if os.environ.get("LINGUATAXI_APP_DIR"):
    APP_DIR = Path(os.environ["LINGUATAXI_APP_DIR"])
elif getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).resolve().parent

SERVER_PY = APP_DIR / "server.py"

# Settings directory
if IS_WIN:
    SETTINGS_DIR = Path(os.environ.get("APPDATA", Path.home())) / "LinguaTaxi"
elif IS_MAC:
    SETTINGS_DIR = Path.home() / "Library" / "Application Support" / "LinguaTaxi"
else:
    SETTINGS_DIR = Path.home() / ".config" / "linguataxi"

SETTINGS_FILE = SETTINGS_DIR / "launcher_settings.json"
DEFAULT_TRANSCRIPTS = Path.home() / "Documents" / "LinguaTaxi Transcripts"

# ── Default Settings ──

DEFAULT_SETTINGS = {
    "transcripts_dir": str(DEFAULT_TRANSCRIPTS),
    "mic_index": None,
    "backend": "auto",
    "model": "large-v3-turbo",
    "display_port": 3000,
    "operator_port": 3001,
    "extended_port": 3002,
    "host": "0.0.0.0",
    "window_geometry": None,
}


def load_settings():
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def save_settings(cfg):
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# ── Microphone detection ──

def list_mics():
    """Return list of (index, name) for available input devices."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        mics = []
        for i, d in enumerate(devices):
            if d.get("max_input_channels", 0) > 0:
                mics.append((i, d["name"]))
        return mics
    except Exception:
        return []


# ══════════════════════════════════════════════
# MAIN APPLICATION
# ══════════════════════════════════════════════

class LinguaTaxiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.server_proc = None
        self.log_queue = queue.Queue()
        self._server_running = False
        self._closing = False

        self._setup_window()
        self._build_ui()
        self._poll_log_queue()

        # Handle close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        if IS_WIN:
            # Handle Ctrl+C
            signal.signal(signal.SIGINT, lambda *a: self._on_close())

    # ── Window Setup ──

    def _setup_window(self):
        self.title(APP_FULL)
        self.minsize(520, 620)
        self.resizable(True, True)

        # Restore geometry
        geo = self.settings.get("window_geometry")
        if geo:
            try:
                self.geometry(geo)
            except Exception:
                self.geometry("560x700")
        else:
            self.geometry("560x700")

        # Center on screen if no saved position
        if not geo:
            self.update_idletasks()
            w, h = self.winfo_width(), self.winfo_height()
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

        # Dark theme colors
        self.BG = "#1a1a2e"
        self.BG2 = "#16213e"
        self.BG3 = "#0f3460"
        self.FG = "#e8e8e8"
        self.FG2 = "#8899aa"
        self.ACCENT = "#4FC3F7"
        self.GREEN = "#4CAF50"
        self.RED = "#f44336"
        self.ORANGE = "#FF9800"
        self.YELLOW = "#FFD54F"

        self.configure(bg=self.BG)

        # Configure ttk styles
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=self.BG, foreground=self.FG,
                         fieldbackground=self.BG2, borderwidth=0)
        style.configure("TFrame", background=self.BG)
        style.configure("Card.TFrame", background=self.BG2)
        style.configure("TLabel", background=self.BG, foreground=self.FG, font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"), foreground=self.ACCENT)
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground=self.FG2)
        style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"), foreground=self.FG2)
        style.configure("Section.TLabel", font=("Segoe UI", 9, "bold"),
                         foreground=self.ACCENT, background=self.BG)

        style.configure("TButton", padding=(12, 6), font=("Segoe UI", 10),
                         background=self.BG3, foreground=self.FG)
        style.map("TButton",
                   background=[("active", self.ACCENT), ("disabled", "#333")],
                   foreground=[("active", "#000"), ("disabled", "#666")])

        style.configure("Start.TButton", font=("Segoe UI", 11, "bold"),
                         background=self.GREEN, foreground="#fff", padding=(16, 10))
        style.map("Start.TButton",
                   background=[("active", "#66BB6A"), ("disabled", "#333")])

        style.configure("Stop.TButton", font=("Segoe UI", 11, "bold"),
                         background=self.RED, foreground="#fff", padding=(16, 10))
        style.map("Stop.TButton",
                   background=[("active", "#EF5350"), ("disabled", "#333")])

        style.configure("Browser.TButton", font=("Segoe UI", 10),
                         background=self.BG3, foreground=self.ACCENT, padding=(10, 7))
        style.map("Browser.TButton",
                   background=[("active", self.ACCENT)],
                   foreground=[("active", "#000"), ("disabled", "#555")])

        style.configure("TCombobox", fieldbackground=self.BG2, foreground=self.FG)
        style.configure("TLabelframe", background=self.BG, foreground=self.ACCENT)
        style.configure("TLabelframe.Label", background=self.BG,
                         foreground=self.ACCENT, font=("Segoe UI", 9, "bold"))

    # ── Build UI ──

    def _build_ui(self):
        # Main container with padding
        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)

        # ── Header ──
        hdr = ttk.Frame(main)
        hdr.pack(fill="x", pady=(0, 12))

        ttk.Label(hdr, text="🚕  LinguaTaxi", style="Title.TLabel").pack(anchor="w")
        ttk.Label(hdr, text="Live Caption & Translation",
                  style="Subtitle.TLabel").pack(anchor="w")

        # ── Server Control ──
        srv_frame = ttk.LabelFrame(main, text="  Server  ", padding=12)
        srv_frame.pack(fill="x", pady=(0, 10))

        status_row = ttk.Frame(srv_frame)
        status_row.pack(fill="x", pady=(0, 8))

        self.status_dot = tk.Canvas(status_row, width=12, height=12,
                                     bg=self.BG, highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 6))
        self._draw_dot("#666")

        self.status_label = ttk.Label(status_row, text="Stopped",
                                       style="Status.TLabel")
        self.status_label.pack(side="left")

        self.backend_label = ttk.Label(status_row, text="",
                                        style="Subtitle.TLabel")
        self.backend_label.pack(side="right")

        btn_row = ttk.Frame(srv_frame)
        btn_row.pack(fill="x")

        self.start_btn = ttk.Button(btn_row, text="▶  Start Server",
                                     style="Start.TButton", command=self._start_server)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.stop_btn = ttk.Button(btn_row, text="⏹  Stop",
                                    style="Stop.TButton", command=self._stop_server,
                                    state="disabled")
        self.stop_btn.pack(side="right", expand=True, fill="x", padx=(4, 0))

        # ── Browser Buttons ──
        browser_frame = ttk.LabelFrame(main, text="  Open in Browser  ", padding=12)
        browser_frame.pack(fill="x", pady=(0, 10))

        self.op_btn = ttk.Button(browser_frame, text="🎛  Operator Controls",
                                  style="Browser.TButton", command=self._open_operator,
                                  state="disabled")
        self.op_btn.pack(fill="x", pady=(0, 5))

        disp_row = ttk.Frame(browser_frame)
        disp_row.pack(fill="x")

        self.main_btn = ttk.Button(disp_row, text="📺  Main Display",
                                    style="Browser.TButton", command=self._open_main,
                                    state="disabled")
        self.main_btn.pack(side="left", expand=True, fill="x", padx=(0, 3))

        self.ext_btn = ttk.Button(disp_row, text="📺  Extended Display",
                                   style="Browser.TButton", command=self._open_extended,
                                   state="disabled")
        self.ext_btn.pack(side="right", expand=True, fill="x", padx=(3, 0))

        self.dict_btn = ttk.Button(browser_frame, text="📝  Dictation (Voice-to-Text)",
                                    style="Browser.TButton", command=self._open_dictation,
                                    state="disabled")
        self.dict_btn.pack(fill="x", pady=(5, 0))

        # ── Settings ──
        settings_frame = ttk.LabelFrame(main, text="  Settings  ", padding=12)
        settings_frame.pack(fill="x", pady=(0, 10))

        # Transcript directory
        ttk.Label(settings_frame, text="Transcript Files:",
                  style="Section.TLabel").pack(anchor="w")
        tdir_row = ttk.Frame(settings_frame)
        tdir_row.pack(fill="x", pady=(2, 8))

        self.tdir_var = tk.StringVar(value=self.settings.get("transcripts_dir",
                                     str(DEFAULT_TRANSCRIPTS)))
        self.tdir_entry = ttk.Entry(tdir_row, textvariable=self.tdir_var,
                                     font=("Segoe UI", 9))
        self.tdir_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        ttk.Button(tdir_row, text="📁 Browse",
                   command=self._browse_tdir).pack(side="right")

        # Microphone
        ttk.Label(settings_frame, text="Microphone:",
                  style="Section.TLabel").pack(anchor="w")
        self.mic_var = tk.StringVar(value="System Default")
        self.mic_combo = ttk.Combobox(settings_frame, textvariable=self.mic_var,
                                       state="readonly", font=("Segoe UI", 9))
        self.mic_combo.pack(fill="x", pady=(2, 8))
        self._refresh_mics()

        # Backend
        ttk.Label(settings_frame, text="Speech Backend:",
                  style="Section.TLabel").pack(anchor="w")
        self._backend_labels = {"auto": "auto", "whisper": "whisper (best)",
                                 "vosk": "vosk (CPU only)", "mlx": "mlx (Apple Silicon)"}
        self._backend_from_label = {v: k for k, v in self._backend_labels.items()}
        stored_backend = self.settings.get("backend", "auto")
        self.backend_var = tk.StringVar(value=self._backend_labels.get(stored_backend, stored_backend))
        backend_values = ["auto", "whisper (best)", "vosk (CPU only)"]
        if IS_MAC:
            backend_values.append("mlx (Apple Silicon)")
        backend_combo = ttk.Combobox(settings_frame, textvariable=self.backend_var,
                                      state="readonly", font=("Segoe UI", 9),
                                      values=backend_values)
        backend_combo.pack(fill="x", pady=(2, 0))

        # ── Log Area ──
        log_frame = ttk.LabelFrame(main, text="  Server Log  ", padding=(8, 6))
        log_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.log_text = tk.Text(log_frame, height=8, wrap="word",
                                 bg="#0a0a1a", fg="#7fdbca", insertbackground="#7fdbca",
                                 font=("Consolas" if IS_WIN else "Menlo", 9),
                                 relief="flat", padx=8, pady=6,
                                 state="disabled")
        self.log_text.pack(fill="both", expand=True)

        # Configure log colors
        self.log_text.tag_configure("info", foreground="#7fdbca")
        self.log_text.tag_configure("warn", foreground="#FFD54F")
        self.log_text.tag_configure("error", foreground="#ff6b6b")
        self.log_text.tag_configure("system", foreground="#4FC3F7")

        # ── Footer ──
        footer = ttk.Frame(main)
        footer.pack(fill="x")

        self.open_tdir_btn = ttk.Button(footer, text="📂 Open Transcripts",
                                         command=self._open_transcripts_dir)
        self.open_tdir_btn.pack(side="left")

        ttk.Button(footer, text="ℹ About",
                   command=self._show_about).pack(side="left", padx=(6, 0))

        ttk.Label(footer, text=f"v{VERSION}", style="Subtitle.TLabel").pack(side="right")

        # Welcome message
        self._log_system(f"LinguaTaxi v{VERSION}")
        self._log_system(f"App directory: {APP_DIR}")
        self._log_system(f"Transcripts: {self.tdir_var.get()}")
        self._log_system("Ready — click 'Start Server' to begin.")

    # ── Drawing ──

    def _draw_dot(self, color):
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 10, 10, fill=color, outline="")

    # ── Microphone Management ──

    def _refresh_mics(self):
        mics = list_mics()
        self._mic_devices = mics
        names = ["System Default"] + [f"[{i}] {n}" for i, n in mics]
        self.mic_combo["values"] = names

        # Restore saved selection
        saved_idx = self.settings.get("mic_index")
        if saved_idx is not None:
            for j, (i, n) in enumerate(mics):
                if i == saved_idx:
                    self.mic_combo.current(j + 1)
                    return
        self.mic_combo.current(0)

    def _get_selected_mic_index(self):
        sel = self.mic_combo.current()
        if sel <= 0:
            return None  # System default
        return self._mic_devices[sel - 1][0]

    # ── Server Management ──

    def _build_server_cmd(self):
        python = self._find_python()
        cmd = [python, str(SERVER_PY)]

        # Backend
        backend = self._backend_from_label.get(self.backend_var.get(), self.backend_var.get())
        if backend and backend != "auto":
            cmd.extend(["--backend", backend])

        # Microphone
        mic_idx = self._get_selected_mic_index()
        if mic_idx is not None:
            cmd.extend(["--mic", str(mic_idx)])

        # Transcripts directory
        tdir = self.tdir_var.get().strip()
        if tdir:
            cmd.extend(["--transcripts-dir", tdir])

        return cmd

    # ── First-Run Model Download ──

    def _needs_model_download(self):
        """Check if speech models are already present."""
        models_dir = APP_DIR / "models"

        # Check for Vosk models
        for item in (models_dir.iterdir() if models_dir.exists() else []):
            if item.is_dir() and "vosk-model" in item.name:
                return False

        # Check for Whisper models in HuggingFace cache
        hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
        if hf_cache.exists():
            for item in hf_cache.iterdir():
                if item.is_dir() and "whisper" in item.name.lower():
                    return False

        return True

    def _download_models(self):
        """Show a progress dialog while downloading speech models."""
        dlg = tk.Toplevel(self)
        dlg.title("First-Time Setup")
        dlg.geometry("480x200")
        dlg.resizable(False, False)
        dlg.configure(bg=self.BG)
        dlg.transient(self)
        dlg.grab_set()

        # Center on parent
        dlg.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 480) // 2
        py = self.winfo_y() + (self.winfo_height() - 200) // 2
        dlg.geometry(f"+{px}+{py}")

        f = ttk.Frame(dlg, padding=24)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Downloading Speech Recognition Model",
                  font=("Segoe UI", 12, "bold"),
                  foreground=self.ACCENT, background=self.BG).pack(pady=(0, 8))

        status_var = tk.StringVar(value="Preparing download...")
        status_lbl = ttk.Label(f, textvariable=status_var,
                               style="Subtitle.TLabel", wraplength=420)
        status_lbl.pack(pady=(0, 12))

        progress = ttk.Progressbar(f, mode="indeterminate", length=420)
        progress.pack(pady=(0, 12))
        progress.start(15)

        hint = ttk.Label(f,
                         text="This only happens once. The model enables offline speech recognition.",
                         style="Subtitle.TLabel", wraplength=420)
        hint.pack()

        download_done = [False]

        def run_download():
            try:
                python = self._find_python()
                dl_script = APP_DIR / "download_models.py"

                if not dl_script.exists():
                    status_var.set("Model will download on first server start.")
                    download_done[0] = True
                    return

                kwargs = {}
                if IS_WIN:
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

                proc = subprocess.Popen(
                    [python, str(dl_script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    cwd=str(APP_DIR),
                    **kwargs,
                )

                for line in iter(proc.stdout.readline, ""):
                    line = line.strip()
                    if line and not line.startswith("="):
                        clean = line.lstrip(" [")
                        if clean:
                            status_var.set(clean[:80])

                proc.wait()

            except Exception as e:
                status_var.set(f"Model will download on first server start.")

            finally:
                download_done[0] = True

        t = threading.Thread(target=run_download, daemon=True)
        t.start()

        def poll():
            if download_done[0]:
                progress.stop()
                dlg.destroy()
                return
            dlg.after(200, poll)

        poll()
        self.wait_window(dlg)

    def _find_python(self):
        """Find the Python executable for running scripts."""
        if IS_WIN:
            venv_py = APP_DIR / "venv" / "Scripts" / "python.exe"
        else:
            venv_py = APP_DIR / "venv" / "bin" / "python3"
        if venv_py.exists():
            return str(venv_py)
        return sys.executable

    # ── Server Management ──

    def _start_server(self):
        if self._server_running:
            return

        # First-run: download speech model if needed
        if self._needs_model_download():
            self._log_system("First run — downloading speech recognition model...")
            self._download_models()
            self._log_system("Model setup complete.")

        # Save settings
        self._save_current_settings()

        # Ensure transcript dir exists
        tdir = Path(self.tdir_var.get().strip())
        try:
            tdir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create transcript directory:\n{e}")
            return

        cmd = self._build_server_cmd()
        self._log_system(f"Starting: {' '.join(cmd)}")

        try:
            # Use CREATE_NO_WINDOW on Windows to avoid console flash
            kwargs = {}
            if IS_WIN:
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self.server_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                cwd=str(APP_DIR),
                env={**os.environ, "PYTHONUNBUFFERED": "1",
                     "LINGUATAXI_TRANSCRIPTS": self.tdir_var.get().strip()},
                **kwargs,
            )

            self._server_running = True
            self._update_ui_state(running=True)

            # Start log reader thread
            t = threading.Thread(target=self._read_server_output, daemon=True)
            t.start()

        except FileNotFoundError:
            self._log_error("Python not found. Please install Python 3.10+ or reinstall LinguaTaxi.")
        except Exception as e:
            self._log_error(f"Failed to start server: {e}")

    def _stop_server(self):
        if not self._server_running or not self.server_proc:
            return

        self._log_system("Stopping server...")

        try:
            if IS_WIN:
                # Graceful shutdown on Windows
                self.server_proc.terminate()
            else:
                self.server_proc.send_signal(signal.SIGINT)

            # Wait up to 5 seconds
            try:
                self.server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_proc.kill()
                self.server_proc.wait(timeout=3)
        except Exception as e:
            self._log_error(f"Error stopping server: {e}")
            try:
                self.server_proc.kill()
            except Exception:
                pass

        self._server_running = False
        self.server_proc = None
        self._update_ui_state(running=False)
        self._log_system("Server stopped.")

    def _read_server_output(self):
        """Read server stdout in a background thread."""
        proc = self.server_proc
        try:
            for line in iter(proc.stdout.readline, ""):
                if not line or not self._server_running:
                    break
                line = line.rstrip("\n\r")
                if line:
                    self.log_queue.put(("output", line))

                    # Detect backend info
                    if "Backend:" in line or "backend:" in line.lower():
                        self.log_queue.put(("backend", line))
                    # Detect ready state
                    if "Uvicorn running" in line or "Started" in line:
                        self.log_queue.put(("ready", True))
        except Exception:
            pass
        finally:
            # Server exited
            if self._server_running:
                self.log_queue.put(("stopped", None))

    def _poll_log_queue(self):
        """Process log messages from the server thread (runs on main thread)."""
        try:
            while True:
                msg_type, data = self.log_queue.get_nowait()

                if msg_type == "output":
                    # Determine tag
                    tag = "info"
                    lower = data.lower()
                    if "error" in lower or "failed" in lower or "exception" in lower:
                        tag = "error"
                    elif "warn" in lower:
                        tag = "warn"
                    self._append_log(data, tag)

                elif msg_type == "backend":
                    # Extract backend name
                    m = re.search(r'Backend:\s*(.+)', data, re.IGNORECASE)
                    if m:
                        self.backend_label.configure(text=m.group(1).strip())

                elif msg_type == "ready":
                    self._draw_dot(self.GREEN)
                    self.status_label.configure(text="Running", foreground=self.GREEN)
                    self._log_system("Server is ready!")

                elif msg_type == "stopped":
                    self._server_running = False
                    self.server_proc = None
                    self._update_ui_state(running=False)
                    self._log_system("Server process ended.")

        except queue.Empty:
            pass

        if not self._closing:
            self.after(100, self._poll_log_queue)

    # ── UI State ──

    def _update_ui_state(self, running):
        if running:
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.op_btn.configure(state="normal")
            self.main_btn.configure(state="normal")
            self.ext_btn.configure(state="normal")
            self.dict_btn.configure(state="normal")
            self._draw_dot(self.ORANGE)
            self.status_label.configure(text="Starting...", foreground=self.ORANGE)
            self.backend_label.configure(text="detecting...")
        else:
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.op_btn.configure(state="disabled")
            self.main_btn.configure(state="disabled")
            self.ext_btn.configure(state="disabled")
            self.dict_btn.configure(state="disabled")
            self._draw_dot("#666")
            self.status_label.configure(text="Stopped", foreground=self.FG2)
            self.backend_label.configure(text="")

    # ── Browser Actions ──

    def _open_operator(self):
        port = self.settings.get("operator_port", 3001)
        webbrowser.open(f"http://localhost:{port}")

    def _open_main(self):
        port = self.settings.get("display_port", 3000)
        webbrowser.open(f"http://localhost:{port}")

    def _open_extended(self):
        port = self.settings.get("extended_port", 3002)
        webbrowser.open(f"http://localhost:{port}")

    def _open_dictation(self):
        port = self.settings.get("dictation_port", 3005)
        webbrowser.open(f"http://localhost:{port}")

    def _open_transcripts_dir(self):
        tdir = Path(self.tdir_var.get().strip())
        tdir.mkdir(parents=True, exist_ok=True)
        if IS_WIN:
            os.startfile(str(tdir))
        elif IS_MAC:
            subprocess.Popen(["open", str(tdir)])
        else:
            subprocess.Popen(["xdg-open", str(tdir)])

    # ── Settings ──

    def _browse_tdir(self):
        current = self.tdir_var.get().strip()
        d = filedialog.askdirectory(initialdir=current if Path(current).exists() else str(Path.home()),
                                     title="Select Transcript Save Location")
        if d:
            self.tdir_var.set(d)
            self._save_current_settings()
            self._log_system(f"Transcripts directory: {d}")

    def _save_current_settings(self):
        self.settings["transcripts_dir"] = self.tdir_var.get().strip()
        self.settings["mic_index"] = self._get_selected_mic_index()
        self.settings["backend"] = self._backend_from_label.get(self.backend_var.get(), self.backend_var.get())
        self.settings["window_geometry"] = self.geometry()
        save_settings(self.settings)

    # ── Logging ──

    def _append_log(self, text, tag="info"):
        self.log_text.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {text}\n", tag)
        self.log_text.see("end")
        # Trim to 500 lines
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 500:
            self.log_text.delete("1.0", f"{lines - 500}.0")
        self.log_text.configure(state="disabled")

    def _log_system(self, text):
        self._append_log(text, "system")

    def _log_error(self, text):
        self._append_log(text, "error")

    # ── About ──

    def _show_about(self):
        about = tk.Toplevel(self)
        about.title("About LinguaTaxi")
        about.geometry("400x320")
        about.resizable(False, False)
        about.configure(bg=self.BG)
        about.transient(self)
        about.grab_set()

        f = ttk.Frame(about, padding=24)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="🚕  LinguaTaxi", style="Title.TLabel").pack(pady=(0, 4))
        ttk.Label(f, text="Live Caption & Translation",
                  style="Subtitle.TLabel").pack()
        ttk.Label(f, text=f"Version {VERSION}",
                  style="Subtitle.TLabel").pack(pady=(8, 16))

        info = (
            "Real-time speech captioning with up to 5\n"
            "simultaneous translations via DeepL.\n\n"
            "Supports NVIDIA CUDA (Windows/Linux),\n"
            "Apple Metal (macOS), and CPU fallback.\n\n"
            "Backends: faster-whisper • mlx-whisper • Vosk"
        )
        ttk.Label(f, text=info, justify="center",
                  style="Subtitle.TLabel").pack()

        ttk.Button(f, text="Close", command=about.destroy).pack(pady=(16, 0))

    # ── Cleanup ──

    def _on_close(self):
        self._closing = True
        self._save_current_settings()

        if self._server_running:
            if messagebox.askyesno("Quit",
                "The server is still running.\nStop it and quit?"):
                self._stop_server()
            else:
                self._closing = False
                return

        self.destroy()


# ══════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════

if __name__ == "__main__":
    app = LinguaTaxiApp()
    app.mainloop()
