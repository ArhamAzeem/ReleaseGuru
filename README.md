# ReleaseGuru 🚀

ReleaseGuru is a lightweight, blazing-fast CLI tool designed to convert your git commit history into clean, user-facing, and professional changelogs using AI. 

It features an intelligent **AI Semantic Version Bump Recommender** and **One-Click GitHub Release Automation**. It is built on a **"bring-your-own-key"** model, supporting multiple AI providers. You can easily switch between providers, pass custom API keys, and use custom models to bear the charge yourself!

---

## 🛠️ Project Structure

```text
releaseguru/
├── releaseguru.py      # Main Click-based CLI entry point (SemVer + GitHub integrations)
├── providers.py        # Adaptor/connector logic for all AI providers
├── requirements.txt    # Python library dependencies (includes requests)
├── .env.example        # Shell template for API keys & GitHub token
└── README.md           # Documentation, usage guide, and release steps
```

---

## 🌟 Advanced Features

### 1. 🤖 AI Semantic Version Recommender
If you do not specify an explicit version with `--version`, the AI analyzes your commit log and outputs a recommendation based on SemVer:
- **Major**: If breaking changes are found.
- **Minor**: If new features are added.
- **Patch**: If only bug fixes, improvements, or chores are found.

ReleaseGuru automatically reads your latest Git tag, calculates the recommended version, and outputs it in the release notes! E.g. `v1.2.0` automatically bumps to `v1.3.0` for new features.

### 2. 🐙 One-Click GitHub Release Automation
Add the `--publish` flag to push your tag and create a new Release directly on GitHub! ReleaseGuru automatically parses your repository slug (e.g. `owner/repo`) from your Git remote origin URL and publishes the release with your clean, AI-generated changelog description.

---

## ⚡ Supported Providers & Defaults

| Provider | Click Option `--provider` | Default Model | Free Tier |
|---|---|---|---|
| **Groq** (Fastest) | `groq` | `llama-3.3-70b-versatile` | Yes — 14,400 req/day |
| **Gemini** | `gemini` | `gemini-1.5-flash` | Yes — 1,500 req/day |
| **OpenAI** | `openai` | `gpt-4o-mini` | No (paid/very cheap) |
| **Anthropic** | `anthropic` | `claude-3-5-haiku-20241022` | No (paid/very cheap) |
| **xAI** | `xai` | `grok-3-mini` | $25 free credits on signup |

---

## 📦 Setup & Installation

### 1. Clone / Copy the project
Make sure you are in the project folder:
```bash
cd "/path/to/ReleaseGuru"
```

### 2. Set up a Virtual Environment
Initialize and activate your virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# Windows (Command Prompt):
venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup environment variables
Copy the example environment template:
```bash
cp .env.example .env
```
Open `.env` and fill in the API key for your chosen provider, and optionally your `GITHUB_TOKEN`.

---

## 🎯 Usage Examples

### 1. Automatic Generation & SemVer Bumping (No Args)
Auto-detects active key from `.env`, analyzes commits since the latest tag, recommends the SemVer bump, bumps the version label, and outputs the changelog:
```bash
python releaseguru.py
```

### 2. One-Click GitHub Publishing
Publish the release directly to GitHub with the AI-recommended version and changelog:
```bash
python releaseguru.py --publish
```
*Note: Make sure your `GITHUB_TOKEN` is set in `.env` or passed via `--github-token`.*

### 3. Overriding Version, Model, and Key
Bear your own charges on the fly by supplying your personal API key, choosing a specific model, and manually forcing a version label:
```bash
python releaseguru.py --provider openai --api-key "sk-proj-YOUR_KEY" --model "gpt-4o" --version "v2.0.0" --publish
```

### 4. Save Directly to a File
```bash
python releaseguru.py --output CHANGELOG.md
```

### 5. Running from other repositories
You can run ReleaseGuru inside any git repository by calling the script:
```bash
cd /path/to/another/project
python /path/to/ReleaseGuru/releaseguru.py --publish
```

---

## 🚀 How to Release / Distribute

To distribute ReleaseGuru to other developers, you have three primary options:

### Option A: Direct Script Sharing
Host the `releaseguru/` directory on GitHub. Developers can clone it, setup their virtual environments, and run it.

### Option B: Executable Packaging (Single Binary)
Compile ReleaseGuru into a single standalone executable (e.g. `releaseguru.exe` on Windows or a binary on macOS/Linux) that does not require Python.

1. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```
2. **Build the Executable**:
   ```bash
   pyinstaller --onefile releaseguru.py
   ```
3. **Distribute**:
   The standalone executable will be located in the `dist/` directory.

### Option C: Publish to PyPI (For Global Pip Installation)
To allow installation via `pip install releaseguru`:
1. Create a `pyproject.toml` or `setup.py` file.
2. Build the package: `python -m build`.
3. Upload to PyPI: `twine upload dist/*`.
