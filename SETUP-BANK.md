# NovaBank Setup

## Run
```powershell
cd "C:\Users\BMSIT\New folder (2)"
python -u bank_backend.py
```

Open `http://localhost:8080`.

## Included data
The SQLite database is initialized automatically at `bank.db` with fictional customers, accounts, employees, branches, and loans.

## API
The browser uses REST endpoints under `/api`. All financial deposits, withdrawals, and transfers update balances inside the backend. Financial records are protected from deletion.

## Demo admin login
- Email: `admin@novabank.test`
- Password: `admin123`

This repository implementation uses Python/SQLite for the available local runtime. It is suitable for demonstration and can be migrated to Express/PostgreSQL by using the same REST resource contract.
