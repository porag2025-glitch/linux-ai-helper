import sys
import argparse
import json
import os
import threading
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

CONFIG_FILE = os.path.expanduser("~/.config/linux_ai_helper.json")
ICON_FILE = os.path.join(os.path.dirname(__file__), "icon.png")

DANGEROUS_PATTERNS = [
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=", "> /dev/sd", 
    "chmod -R 777 /", ":(){ :|:& };:"
]

SYSTEM_PROMPT = """You are a Linux terminal command assistant. 
Convert user requests into valid, safe Linux commands for Debian/Ubuntu based systems. 
Even if the user specifies an unfamiliar, misspelled, or obscure package name (e.g., 'abro'), generate the standard installation/execution command.

FORMAT INSTRUCTIONS:
Return EXACTLY two lines:
Line 1: The exact bash command ONLY (no markdown backticks, no quotes).
Line 2: A short 1-line explanation of what the command does.

Example response format:
sudo apt update && sudo apt install -y vlc
Installs VLC media player using the apt package manager."""


def load_settings():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"provider": "Gemini", "gemini_api_key": "", "groq_api_key": "", "ollama_url": "http://localhost:11434", "ollama_model": "llama3"}


def save_settings(settings):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings, f, indent=4)


def is_dangerous(command):
    cmd_clean = command.strip().lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd_clean:
            return True
    return False


def call_ai_provider(prompt, settings=None):
    if settings is None:
        settings = load_settings()
    
    provider = settings.get("provider", "Gemini")

    if provider == "Gemini":
        from google import genai
        api_key = settings.get("gemini_api_key", "")
        if not api_key:
            raise ValueError("Gemini API key is missing in settings.")
        
        client = genai.Client(api_key=api_key)
        
        # Try primary model, fallback if 503 server overload occurs
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{SYSTEM_PROMPT}\n\nUser request: {prompt}",
            )
        except Exception:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=f"{SYSTEM_PROMPT}\n\nUser request: {prompt}",
            )
            
        raw_text = response.text.strip()

    elif provider == "Groq":
        api_key = settings.get("groq_api_key", "")
        if not api_key:
            raise ValueError("Groq API key is missing in settings.")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            "temperature": 0.1, "max_tokens": 200
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        raw_text = resp.json()["choices"][0]["message"]["content"].strip()

    else:  # Ollama
        base_url = settings.get("ollama_url", "http://localhost:11434").rstrip("/")
        url = f"{base_url}/api/generate"
        payload = {"model": settings.get("ollama_model", "llama3"), "prompt": f"{SYSTEM_PROMPT}\n\nUser request: {prompt}", "stream": False}
        resp = requests.post(url, json=payload, timeout=90)
        resp.raise_for_status()
        raw_text = resp.json()["response"].strip()

    # Clean Markdown block backticks if AI outputs them
    lines = [line.strip() for line in raw_text.split("\n") if line.strip() and not line.startswith("```")]
    
    cmd = lines[0] if len(lines) > 0 else ""
    exp = lines[1] if len(lines) > 1 else "No explanation provided."
    
    return cmd, exp


# --- GUI Implementation ---
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, settings, on_save):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("400x320")
        self.settings = settings
        self.on_save = on_save
        self._set_icon()
        self._build_ui()

    def _set_icon(self):
        if os.path.exists(ICON_FILE):
            try:
                icon_img = ImageTk.PhotoImage(Image.open(ICON_FILE))
                self.iconphoto(True, icon_img)
            except Exception:
                pass

    def _build_ui(self):
        ttk.Label(self, text="AI Provider:").pack(anchor="w", padx=10, pady=5)
        self.provider_var = tk.StringVar(value=self.settings.get("provider", "Gemini"))
        provider_combo = ttk.Combobox(self, textvariable=self.provider_var, values=["Gemini", "Groq", "Ollama"], state="readonly")
        provider_combo.pack(fill="x", padx=10)

        ttk.Label(self, text="Gemini API Key:").pack(anchor="w", padx=10, pady=5)
        self.gemini_entry = ttk.Entry(self, show="*")
        self.gemini_entry.insert(0, self.settings.get("gemini_api_key", ""))
        self.gemini_entry.pack(fill="x", padx=10)

        ttk.Label(self, text="Groq API Key:").pack(anchor="w", padx=10, pady=5)
        self.groq_entry = ttk.Entry(self, show="*")
        self.groq_entry.insert(0, self.settings.get("groq_api_key", ""))
        self.groq_entry.pack(fill="x", padx=10)

        ttk.Button(self, text="Save Settings", command=self._save).pack(pady=15)

    def _save(self):
        self.settings["provider"] = self.provider_var.get()
        self.settings["gemini_api_key"] = self.gemini_entry.get().strip()
        self.settings["groq_api_key"] = self.groq_entry.get().strip()
        save_settings(self.settings)
        self.on_save(self.settings)
        self.destroy()


class LinuxAIHelperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Linux AI Terminal Helper")
        self.root.geometry("600x480")
        self.settings = load_settings()
        self._set_icon()
        self._build_ui()

    def _set_icon(self):
        if os.path.exists(ICON_FILE):
            try:
                icon_img = ImageTk.PhotoImage(Image.open(ICON_FILE))
                self.root.iconphoto(True, icon_img)
            except Exception:
                pass

    def _build_ui(self):
        top_bar = ttk.Frame(self.root)
        top_bar.pack(fill="x", padx=10, pady=5)
        
        header_frame = ttk.Frame(top_bar)
        header_frame.pack(side="left")

        if os.path.exists(ICON_FILE):
            try:
                img = Image.open(ICON_FILE).resize((32, 32), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img)
                logo_lbl = ttk.Label(header_frame, image=self.logo_img)
                logo_lbl.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        title_lbl = ttk.Label(header_frame, text="Linux AI Terminal Helper", font=("Helvetica", 14, "bold"))
        title_lbl.pack(side="left")

        ttk.Button(top_bar, text="⚙ Settings", command=self.open_settings).pack(side="right")

        ttk.Label(self.root, text="What do you want to do?").pack(anchor="w", padx=10, pady=5)
        self.input_text = tk.Text(self.root, height=3)
        self.input_text.pack(fill="x", padx=10)

        self.generate_btn = ttk.Button(self.root, text="⚡ Generate Command", command=self.generate_command)
        self.generate_btn.pack(fill="x", padx=10, pady=10)

        ttk.Label(self.root, text="Generated Command:").pack(anchor="w", padx=10)
        self.output_text = tk.Text(self.root, height=2, fg="cyan", bg="black")
        self.output_text.pack(fill="x", padx=10)

        ttk.Label(self.root, text="Explanation:").pack(anchor="w", padx=10, pady=(10, 0))
        self.explanation_lbl = ttk.Label(self.root, text="-", wraplength=560, justify="left")
        self.explanation_lbl.pack(anchor="w", padx=10, pady=5)

        self.status_lbl = ttk.Label(self.root, text="Ready")
        self.status_lbl.pack(anchor="w", padx=10, pady=5)

    def open_settings(self):
        SettingsDialog(self.root, self.settings, lambda updated: setattr(self, 'settings', updated))

    def generate_command(self):
        prompt = self.input_text.get("1.0", tk.END).strip()
        if not prompt:
            return
        
        self.generate_btn.config(state="disabled")
        self.status_lbl.config(text="Generating...")

        threading.Thread(target=self._worker, args=(prompt,), daemon=True).start()

    def _worker(self, prompt):
        try:
            cmd, exp = call_ai_provider(prompt, self.settings)
            self.root.after(0, self._on_success, cmd, exp)
        except Exception as e:
            self.root.after(0, self._on_error, str(e))

    def _on_success(self, cmd, exp):
        self.generate_btn.config(state="normal")
        if is_dangerous(cmd):
            messagebox.showwarning("Warning", f"Dangerous command detected:\n{cmd}")
            self.status_lbl.config(text="⚠️ Dangerous command blocked.")
            return

        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, cmd)
        self.explanation_lbl.config(text=f"💡 {exp}")
        self.status_lbl.config(text="✔ Command generated successfully.")

    def _on_error(self, err):
        self.generate_btn.config(state="normal")
        messagebox.showerror("Error", f"Server Busy / Error: {err}\n\nPlease try clicking Generate again.")
        self.status_lbl.config(text="✖ Server busy or error occurred.")


def main():
    parser = argparse.ArgumentParser(description="Linux AI Terminal Helper (GUI & CLI)")
    parser.add_argument("prompt", nargs="*", help="Optional CLI prompt input. E.g., ai 'install vlc'")
    args = parser.parse_args()

    if args.prompt:
        user_prompt = " ".join(args.prompt)
        try:
            cmd, exp = call_ai_provider(user_prompt)
            if is_dangerous(cmd):
                print(f"\n\033[91m⚠️ WARNING: Dangerous command detected!\033[0m\n{cmd}\n")
            else:
                print(f"\n📌 Command:\n\033[92m{cmd}\033[0m\n")
                print(f"💡 Explanation:\n{exp}\n")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        root = tk.Tk()
        app = LinuxAIHelperApp(root)
        root.mainloop()

if __name__ == "__main__":
    main()
