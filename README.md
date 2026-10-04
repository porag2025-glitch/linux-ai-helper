# Linux AI Terminal Helper 🚀

A fast, lightweight GUI and CLI tool that translates natural language requests into safe Linux terminal commands with explanations.

![App Screenshot](icon.png)

## Features
- **Dual Mode:** Use either the intuitive Tkinter GUI or fast CLI interface.
- **Safety Filter:** Automatically blocks hazardous commands (e.g., `rm -rf /`).
- **Multi-Provider Support:** Supports Google Gemini, Groq, and local Ollama (for offline use).
- **Error Resilient:** Handles API overloads seamlessly with built-in fallbacks.

## Installation

```bash
git clone [https://github.com/YOUR_USERNAME/linux-ai-helper.git](https://github.com/YOUR_USERNAME/linux-ai-helper.git)
cd linux-ai-helper
pip install -e . --break-system-packages
