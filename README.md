# Finance Tracker

A simple Streamlit app to track income, expenses, transfers between accounts/cards, and account balances.

## Features

- Add transactions with date, title, category, type, and amount
- Track income, expenses, and transfers between accounts/cards
- Filter by type, category, account, and search text
- Import pasted table/CSV data
- See summary metrics for income, expenses, and current balance
- Manage multiple accounts/cards with separate balances
- Store data in SQLite at `data/finance.db`
- Automatically migrate old JSON data into SQLite on first run
- Optional simple authentication with username/password

## Requirements

- Python 3.11+ recommended
- Dependencies from `requirements.txt`
- SQLite is included with Python, so no extra database install is needed

## Run locally

1. Install dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

2. (Optional) Enable simple authentication with Streamlit secrets:

   Create `.streamlit/secrets.toml`:

   ```toml
   APP_USERNAME = "admin"
   APP_PASSWORD = "change-this-password"
   ```

   Or set environment variables instead:

   ```powershell
   $env:APP_USERNAME="admin"
   $env:APP_PASSWORD="change-this-password"
   ```

3. Start the app:

   ```powershell
   py -m streamlit run app.py --server.headless true --browser.gatherUsageStats false
   ```

4. Open the local URL shown in the terminal.

## Data files

- Main database: `data/finance.db`
- Old JSON backups:
  - `data/accounts.json`
  - `data/transactions.json`

The app now reads and writes through SQLite. The JSON files are kept as backup data from the earlier version.

## Simple authentication

Authentication is off by default. It turns on only when both credentials are set.

You can configure it in one of these ways:

### Option 1: Streamlit secrets

Create `.streamlit/secrets.toml`:

```toml
APP_USERNAME = "admin"
APP_PASSWORD = "change-this-password"
```

### Option 2: Environment variables

```powershell
$env:APP_USERNAME="admin"
$env:APP_PASSWORD="change-this-password"
```

## Deploy on a private server

For a private server or Tailscale setup, run:

```powershell
py -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Then open the app from another device using the server IP or Tailscale IP:

- `http://<server-ip>:8501`

## Notes

- Data is stored locally in the project folder.
- Authentication is disabled unless you set both `APP_USERNAME` and `APP_PASSWORD`.
- This app is intended for personal/local or private-network use.
- Transfers move money between accounts but do not count as income or expense.
