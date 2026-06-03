# mindocu-document-management

Dieses Projekt nutzt [**uv**](https://docs.astral.sh/uv/) als Paket- und Umgebungsmanager.

---

## 📦 uv-Workflow

### Voraussetzung: uv installieren

Einmalig pro Rechner (macOS / Linux):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> Windows oder andere Methoden: siehe https://docs.astral.sh/uv/getting-started/installation/

### Projekt einrichten

Nach dem Klonen des Repos die Umgebung erstellen und alle Abhängigkeiten installieren:

```bash
uv sync
```

`uv sync` liest `pyproject.toml` und `uv.lock`, legt automatisch ein `.venv` an,
installiert die passende Python-Version (siehe `.python-version`, aktuell **3.13**)
und installiert exakt die in `uv.lock` festgehaltenen Versionen.

> Eine manuelle Aktivierung des venv ist **nicht** nötig – `uv run` kümmert sich darum.

### Code ausführen

```bash
uv run main.py
```

Oder ein beliebiges Kommando in der Projektumgebung:

```bash
uv run python -m backend.reader
uv run pytest          # Tests ausführen
```

### Abhängigkeiten verwalten

Niemals `pip install` verwenden – stattdessen:

```bash
uv add docling             # Laufzeit-Abhängigkeit hinzufügen
uv add --dev pytest        # Entwicklungs-Abhängigkeit hinzufügen
uv remove docling          # Abhängigkeit entfernen
```

Diese Befehle aktualisieren automatisch `pyproject.toml` **und** `uv.lock`.

> ⚠️ **Wichtig:** `pyproject.toml` und `uv.lock` immer **gemeinsam** committen,
> damit alle im Team die identischen Versionen verwenden.

### Wichtige Dateien

| Datei              | Zweck                                                        |
| ------------------ | ----------------------------------------------------------- |
| `pyproject.toml`   | Projekt-Metadaten und deklarierte Abhängigkeiten            |
| `uv.lock`          | Exakt aufgelöste Versionen (committen!)                     |
| `.python-version`  | Festgelegte Python-Version für das Projekt                  |
| `.venv/`           | Lokale virtuelle Umgebung (wird ignoriert, nicht committen) |

---

# Git Workflow

## 🌿 Neues Feature starten

Immer von einem aktuellen `main` Branch starten:

```bash
git checkout main
git pull origin main
git checkout -b feature/mein-feature
```

---

## 💾 Änderungen committen

Während der Entwicklung regelmäßig committen:

```bash
git add .
git commit -m "feat/refactor/...: kurze Beschreibung der Änderung"
```

Nutze bei der Commit-Nachricht die Best-Practices unter: https://www.conventionalcommits.org/en/v1.0.0/

> Tipp: Lieber kleine, häufige Commits als einen großen am Ende.

---

## 🚀 Feature fertigstellen & PR erstellen

Wenn das Feature fertig ist:

```bash
# Branch pushen
git push origin feature/mein-feature
```

Danach auf GitHub:

1. Banner **"Compare & pull request"** klicken
2. Titel und Beschreibung ausfüllen
3. **"Create pull request"** klicken
4. Auf Approval eines Teammitglieds warten
5. Nach Approval → **"Merge pull request"**

---

## 🧹 Aufräumen nach dem Merge

```bash
git checkout main
git pull origin main
git branch -d feature/mein-feature
```

---

## ⚠️ Wichtige Regeln

- **Nie direkt auf `main` pushen**
- Jedes Feature bekommt einen eigenen Branch
- Branch-Namen beschreibend halten: `feature/login`, `fix/button-farbe`, `docs/readme`
