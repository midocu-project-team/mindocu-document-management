# mindocu-document-management - Git Workflow

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
