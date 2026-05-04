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

### Stay signed in / password autofill

Browsers often do not offer to save passwords for Streamlit login widgets the same way they do for normal websites.

This app supports an optional **Stay signed in** checkbox. It stores an **encrypted cookie** (not your password in plain text) so you can refresh the page without logging in again until the cookie expires.

If you want stronger separation between auth and cookie encryption, set these (optional):

```env
COOKIE_ENCRYPT_PASSWORD="a-long-random-string"
COOKIE_SECRET="another-long-random-string"
```

If omitted, the app falls back to using `APP_PASSWORD` for both defaults (works, but rotate together).

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

## Run with Docker on Windows

Assumes [Docker Desktop](https://www.docker.com/products/docker-desktop/) is installed.

1. Open PowerShell in this project folder.

2. (Optional) Create a `.env` file next to `docker-compose.yml` for login:

   ```env
   APP_USERNAME=admin
   APP_PASSWORD=change-this-password
   ```

3. Build and start:

   ```powershell
   docker compose up --build
   ```

4. Open the app in your browser:

   - `http://localhost:8501`

### Data persistence

Docker Compose mounts `./data` on your Windows host to `/app/data` in the container.

That is where `data/finance.db` and the old JSON backups live, so your data survives container restarts.

### Plain `docker run` (alternative)

```powershell
docker build -t finance-tracker .
docker run --rm -p 8501:8501 `
  -v "${PWD}/data:/app/data" `
  -e APP_USERNAME=admin `
  -e APP_PASSWORD=change-this-password `
  finance-tracker
```

## Notes

- Data is stored locally in the project folder.
- Authentication is disabled unless you set both `APP_USERNAME` and `APP_PASSWORD`.
- This app is intended for personal/local or private-network use.
- Transfers move money between accounts but do not count as income or expense.
