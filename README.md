# Finance Tracker

A simple local Streamlit app to track income and expenses.

## Features

- Add transactions with date, title, category, type, and amount
- Track both income and expense entries
- Filter by type, category, and search text
- See summary metrics for income, expenses, and current balance
- Persist data locally in `data/transactions.json`

## Run locally

1. Install dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

2. Start the app:

   ```powershell
   py -m streamlit run app.py
   ```

3. Open the local URL shown in the terminal.

## Notes

- Data is stored locally in the project folder.
- This app is intended for personal/local use.
