# Weihnachtsessen Anmeldung

Dies ist eine kleine Flask-Anwendung zur Anmeldung zum Weihnachtsessen des DARC Ortsverbands Essen-Mitte L11.

## Voraussetzungen

- Python 3
- Abhängigkeiten aus `requirements.txt`

```bash
pip install -r requirements.txt
```

## Starten der Anwendung

1. Erstelle eine `.env` Datei nach dem Vorbild von `.env.sample` und passe die Zugangsdaten an.
2. Starte die Anwendung mit:

```bash
python app.py
```

Die Webseite ist anschließend unter `http://localhost:8086` erreichbar.

Der Adminbereich befindet sich unter `http://localhost:8086/admin` und ist mit dem in der `.env` Datei angegebenen Benutzernamen und Passwort geschützt.
