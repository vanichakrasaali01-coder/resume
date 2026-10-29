# NovaBank and Medora Hospital Web Projects

This workspace contains standalone browser interfaces and SQLite-backed Python demo servers.

## Medora Hospital

```powershell
python backend.py
```

Open `http://localhost:8080`. Local database files are intentionally excluded from Git.

## NovaBank

```powershell
python bank_backend.py
```

Open `http://localhost:8080`. Stop one server before starting the other on the same port.

Demo credentials are documented only in local setup files and must never be committed.
