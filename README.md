# Finance Tracker

A simple local Streamlit app to track income, expenses, transfers, and account balances.

## Features

- Add transactions with date, title, category, type, and amount
- Track income, expenses, and transfers between accounts/cards
- Filter by type, category, account, and search text
- Import pasted table/CSV data
- See summary metrics for income, expenses, and current balance
- Persist data in SQLite at `data/finance.db`

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

## Notes

- Data is stored locally in the project folder.
- Authentication is disabled unless you set both `APP_USERNAME` and `APP_PASSWORD`.
- This app is intended for personal/local or private-network use.
