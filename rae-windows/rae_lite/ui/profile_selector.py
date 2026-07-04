import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ProfileSelectorUI:
    """Interfejs użytkownika do wyboru profilu sprzętowego RAE-Windows."""

    def __init__(self, hardware_info: Dict[str, Any]):
        self.hardware_info = hardware_info
        self.result = None
        
        self.root = tk.Tk()
        self.root.title("Konfiguracja RAE-Windows")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        
        # Wyśrodkowanie okna
        self.root.eval('tk::PlaceWindow . center')

        self._setup_style()
        self._build_ui()

    def _setup_style(self):
        style = ttk.Style()
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("Recommendation.TLabel", font=("Segoe UI", 10, "italic"), foreground="#005a9e")

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Nagłówek
        ttk.Label(main_frame, text="Wykryto konfigurację sprzętową:", style="Header.TLabel").pack(pady=(0, 10))

        # Info o sprzęcie
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        gpu_name = self.hardware_info["gpu"]["name"] if self.hardware_info["gpu"]["has_nvidia"] else "Brak NVIDIA"
        
        ttk.Label(info_frame, text=f"• RAM: {self.hardware_info['ram_gb']} GB").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"• CPU: {self.hardware_info['cpu']['name']} ({self.hardware_info['cpu']['cores']} rdzeni)").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"• GPU: {gpu_name}").pack(anchor=tk.W)

        # Rekomendacja
        rec_profile = self.hardware_info["suggested_profile"]
        ttk.Label(main_frame, text=f"Rekomendowany profil: {rec_profile}", style="Recommendation.TLabel").pack(pady=10)

        # Opisy profili
        desc_frame = ttk.LabelFrame(main_frame, text="Wybierz poziom inteligencji (LLM)", padding="10")
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        profiles = [
            ("Profil A - Tylko Math", "Brak LLM. Najszybszy, najniższe użycie RAM. Działa na każdym PC."),
            ("Profil B - Lekki LLM", "Model 1-2B. Wymaga 8GB RAM. Podstawowa analiza zapytań."),
            ("Profil C - Standard LLM", "Model 3-7B. Wymaga 16GB RAM. Dobra jakość wnioskowania."),
            ("Profil D - GPU LLM", "Wymaga karty NVIDIA (6GB+ VRAM). Najwyższa wydajność i jakość.")
        ]

        self.selected_var = tk.StringVar(value=rec_profile)

        for code, (title, desc) in zip(["A", "B", "C", "D"], profiles):
            rb = ttk.Radiobutton(desc_frame, text=title, value=code, variable=self.selected_var)
            rb.pack(anchor=tk.W, pady=2)
            ttk.Label(desc_frame, text=f"  {desc}", font=("Segoe UI", 8)).pack(anchor=tk.W)

        # Przyciski
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        ttk.Button(btn_frame, text="Uruchom RAE", command=self._on_submit).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Anuluj", command=self.root.destroy).pack(side=tk.RIGHT)

    def _on_submit(self):
        self.result = self.selected_var.get()
        self.root.destroy()

    def run(self) -> Optional[str]:
        self.root.mainloop()
        return self.result

def select_profile(hardware_info: Dict[str, Any]) -> Optional[str]:
    """Uruchamia UI i zwraca wybrany profil."""
    ui = ProfileSelectorUI(hardware_info)
    return ui.run()
