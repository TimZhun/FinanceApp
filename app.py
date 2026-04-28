from __future__ import annotations

import hmac
import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Tuple
from uuid import uuid4

import pandas as pd
import streamlit as st


APP_TITLE = "Finance Tracker"
DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "transactions.json"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
DB_FILE = DATA_DIR / "finance.db"
CATEGORIES = [
    "Salary",
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Health",
    "Entertainment",
    "Education",
    "Savings",
    "Other",
]


def get_auth_config() -> Tuple[str, str]:
    username = ""
    password = ""

    try:
        username = str(st.secrets.get("APP_USERNAME", "")).strip()
        password = str(st.secrets.get("APP_PASSWORD", "")).strip()
    except Exception:
        pass

    username = username or os.getenv("APP_USERNAME", "").strip()
    password = password or os.getenv("APP_PASSWORD", "").strip()
    return username, password


def is_auth_enabled() -> bool:
    username, password = get_auth_config()
    return bool(username and password)


def check_credentials(username: str, password: str) -> bool:
    expected_username, expected_password = get_auth_config()
    return hmac.compare_digest(username, expected_username) and hmac.compare_digest(
        password, expected_password
    )


def render_login() -> bool:
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False

    if not is_auth_enabled():
        st.info(
            "Authentication is currently disabled. Set APP_USERNAME and APP_PASSWORD "
            "in Streamlit secrets or environment variables to enable login."
        )
        st.session_state.is_authenticated = True
        return True

    if st.session_state.is_authenticated:
        return True

    st.title(APP_TITLE)
    st.caption("Sign in to access your finance data.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            if check_credentials(username.strip(), password):
                st.session_state.is_authenticated = True
                st.rerun()
            else:
                st.error("Invalid username or password.")

    return False


def render_logout() -> None:
    if is_auth_enabled() and st.sidebar.button("Log out", use_container_width=True):
        st.session_state.is_authenticated = False
        st.rerun()


@dataclass
class Account:
    id: str
    name: str
    starting_balance: float


@dataclass
class Transaction:
    id: str
    entry_date: str
    title: str
    category: str
    kind: str
    amount: float
    note: str
    account_id: str
    transfer_to_account_id: str


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")
    if not ACCOUNTS_FILE.exists():
        ACCOUNTS_FILE.write_text("[]", encoding="utf-8")


def db_connect() -> sqlite3.Connection:
    ensure_storage()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def db_init() -> None:
    with db_connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL UNIQUE,
              starting_balance REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS transactions (
              id TEXT PRIMARY KEY,
              entry_date TEXT NOT NULL,
              title TEXT NOT NULL,
              category TEXT NOT NULL,
              kind TEXT NOT NULL,
              amount REAL NOT NULL,
              note TEXT NOT NULL DEFAULT '',
              account_id TEXT NOT NULL,
              transfer_to_account_id TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(entry_date);
            CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
            """
        )


def db_is_empty() -> bool:
    db_init()
    with db_connect() as conn:
        a = conn.execute("SELECT COUNT(*) AS c FROM accounts").fetchone()["c"]
        t = conn.execute("SELECT COUNT(*) AS c FROM transactions").fetchone()["c"]
    return int(a) == 0 and int(t) == 0


def load_accounts_json() -> List[Account]:
    ensure_storage()
    raw = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    return [
        Account(
            id=item["id"],
            name=item["name"],
            starting_balance=float(item.get("starting_balance", 0.0)),
        )
        for item in raw
    ]


def load_transactions_json() -> List[Transaction]:
    ensure_storage()
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    transactions: List[Transaction] = []
    for item in raw:
        transactions.append(
            Transaction(
                id=item["id"],
                entry_date=item["entry_date"],
                title=item["title"],
                category=item["category"],
                kind=item["kind"],
                amount=float(item["amount"]),
                note=item.get("note", ""),
                account_id=item.get("account_id", ""),
                transfer_to_account_id=item.get("transfer_to_account_id", ""),
            )
        )
    return transactions


def migrate_json_to_sqlite_if_needed() -> None:
    """
    One-time migration: if SQLite is empty, import existing JSON accounts/transactions.
    JSON files remain as a backup.
    """
    if not db_is_empty():
        return

    accounts = load_accounts_json()
    transactions = load_transactions_json()

    with db_connect() as conn:
        for account in accounts:
            conn.execute(
                "INSERT OR IGNORE INTO accounts (id, name, starting_balance) VALUES (?, ?, ?)",
                (account.id, account.name, float(account.starting_balance)),
            )
        for tx in transactions:
            conn.execute(
                """
                INSERT OR IGNORE INTO transactions
                (id, entry_date, title, category, kind, amount, note, account_id, transfer_to_account_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx.id,
                    tx.entry_date,
                    tx.title,
                    tx.category,
                    tx.kind,
                    float(tx.amount),
                    tx.note or "",
                    tx.account_id,
                    tx.transfer_to_account_id or "",
                ),
            )


def load_accounts() -> List[Account]:
    db_init()
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT id, name, starting_balance FROM accounts ORDER BY name COLLATE NOCASE"
        ).fetchall()
    return [
        Account(
            id=row["id"],
            name=row["name"],
            starting_balance=float(row["starting_balance"]),
        )
        for row in rows
    ]


def load_transactions() -> List[Transaction]:
    db_init()
    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT id, entry_date, title, category, kind, amount, note, account_id, transfer_to_account_id
            FROM transactions
            ORDER BY entry_date DESC, created_at DESC
            """
        ).fetchall()
    return [
        Transaction(
            id=row["id"],
            entry_date=row["entry_date"],
            title=row["title"],
            category=row["category"],
            kind=row["kind"],
            amount=float(row["amount"]),
            note=row["note"] or "",
            account_id=row["account_id"],
            transfer_to_account_id=row["transfer_to_account_id"] or "",
        )
        for row in rows
    ]


def refresh_state_from_db() -> None:
    st.session_state.accounts = load_accounts()
    st.session_state.transactions = load_transactions()


def parse_amount(value: str) -> float:
    cleaned = value.strip().replace(" ", "").replace("\u00a0", "")
    cleaned = cleaned.replace(",", ".")
    return float(cleaned)


def parse_ddmmyyyy(value: str) -> date:
    return datetime.strptime(value.strip(), "%d.%m.%Y").date()


def format_currency(value: float) -> str:
    return f"₸{value:,.2f}"


def initialize_state() -> None:
    db_init()
    migrate_json_to_sqlite_if_needed()

    if "accounts" not in st.session_state or "transactions" not in st.session_state:
        refresh_state_from_db()

    if not st.session_state.accounts:
        default = Account(id=str(uuid4()), name="Cash", starting_balance=0.0)
        with db_connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO accounts (id, name, starting_balance) VALUES (?, ?, ?)",
                (default.id, default.name, float(default.starting_balance)),
            )
        refresh_state_from_db()


def accounts_by_id(accounts: List[Account]) -> Dict[str, Account]:
    return {account.id: account for account in accounts}


def account_label(account: Account) -> str:
    return f"{account.name} ({format_currency(account.starting_balance)} start)"


def add_account(name: str, starting_balance: float) -> None:
    account = Account(id=str(uuid4()), name=name.strip(), starting_balance=float(starting_balance))
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO accounts (id, name, starting_balance) VALUES (?, ?, ?)",
            (account.id, account.name, float(account.starting_balance)),
        )
    refresh_state_from_db()


def delete_account(account_id: str) -> Tuple[bool, str]:
    used = any(item.account_id == account_id for item in st.session_state.transactions)
    if used:
        return False, "This account has transactions. Delete or move them first."
    with db_connect() as conn:
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    refresh_state_from_db()
    if not st.session_state.accounts:
        default = Account(id=str(uuid4()), name="Cash", starting_balance=0.0)
        with db_connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO accounts (id, name, starting_balance) VALUES (?, ?, ?)",
                (default.id, default.name, float(default.starting_balance)),
            )
        refresh_state_from_db()
    return True, "Account deleted."


def add_transaction(
    entry_date: date,
    title: str,
    category: str,
    kind: str,
    amount: float,
    note: str,
    account_id: str,
    transfer_to_account_id: str = "",
) -> None:
    transaction = Transaction(
        id=str(uuid4()),
        entry_date=entry_date.isoformat(),
        title=title.strip(),
        category=category,
        kind=kind,
        amount=round(float(amount), 2),
        note=note.strip(),
        account_id=account_id,
        transfer_to_account_id=transfer_to_account_id,
    )
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO transactions
            (id, entry_date, title, category, kind, amount, note, account_id, transfer_to_account_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction.id,
                transaction.entry_date,
                transaction.title,
                transaction.category,
                transaction.kind,
                float(transaction.amount),
                transaction.note or "",
                transaction.account_id,
                transaction.transfer_to_account_id or "",
            ),
        )
    refresh_state_from_db()


def add_transfer(
    entry_date: date,
    from_account_id: str,
    to_account_id: str,
    amount: float,
    note: str,
) -> None:
    accounts = accounts_by_id(st.session_state.accounts)
    from_name = accounts.get(from_account_id, Account(id="", name="(Unknown)", starting_balance=0.0)).name
    to_name = accounts.get(to_account_id, Account(id="", name="(Unknown)", starting_balance=0.0)).name
    title = f"Transfer {from_name} → {to_name}"
    add_transaction(
        entry_date=entry_date,
        title=title,
        category="Transfer",
        kind="Transfer",
        amount=round(float(amount), 2),
        note=note,
        account_id=from_account_id,
        transfer_to_account_id=to_account_id,
    )


def delete_transaction(transaction_id: str) -> None:
    with db_connect() as conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    refresh_state_from_db()


def build_dataframe(transactions: List[Transaction]) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame(
            columns=["Date", "Title", "Category", "Account", "Type", "Amount", "Note"]
        )

    accounts = accounts_by_id(st.session_state.accounts)
    rows = []
    for item in transactions:
        account_name = accounts.get(
            item.account_id, Account(id="", name="(Unknown)", starting_balance=0.0)
        ).name
        transfer_to_name = ""
        if item.transfer_to_account_id:
            transfer_to_name = accounts.get(
                item.transfer_to_account_id,
                Account(id="", name="(Unknown)", starting_balance=0.0),
            ).name

        account_display = (
            f"{account_name} → {transfer_to_name}"
            if item.kind == "Transfer" and transfer_to_name
            else account_name
        )
        rows.append(
            {
                "ID": item.id,
                "Date": datetime.fromisoformat(item.entry_date).strftime("%Y-%m-%d"),
                "Title": item.title,
                "Category": item.category,
                "Account": account_display,
                "AccountID": item.account_id,
                "TransferToAccountID": item.transfer_to_account_id,
                "Type": item.kind,
                "Amount": item.amount,
                "Note": item.note,
            }
        )
    return pd.DataFrame(rows)


def filtered_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    st.sidebar.header("Filters")
    selected_type = st.sidebar.selectbox(
        "Transaction type", ["All", "Income", "Expense", "Transfer"]
    )
    categories = ["All"] + sorted(df["Category"].dropna().unique().tolist())
    selected_category = st.sidebar.selectbox("Category", categories)
    accounts = ["All"] + sorted(df["Account"].dropna().unique().tolist())
    selected_account = st.sidebar.selectbox("Account", accounts)
    search_text = st.sidebar.text_input("Search title or note")

    filtered = df.copy()
    if selected_type != "All":
        filtered = filtered[filtered["Type"] == selected_type]
    if selected_category != "All":
        filtered = filtered[filtered["Category"] == selected_category]
    if selected_account != "All":
        filtered = filtered[filtered["Account"] == selected_account]
    if search_text.strip():
        query = search_text.strip().lower()
        filtered = filtered[
            filtered["Title"].str.lower().str.contains(query)
            | filtered["Note"].fillna("").str.lower().str.contains(query)
        ]

    return filtered


def compute_account_balances(all_df: pd.DataFrame) -> Dict[str, float]:
    balances: Dict[str, float] = {a.id: float(a.starting_balance) for a in st.session_state.accounts}
    if all_df.empty:
        return balances

    for _, row in all_df.iterrows():
        account_id = row.get("AccountID", "")
        if not account_id or account_id not in balances:
            continue
        amount = float(row["Amount"])
        if row["Type"] == "Income":
            balances[account_id] += amount
        elif row["Type"] == "Expense":
            balances[account_id] -= amount
        elif row["Type"] == "Transfer":
            balances[account_id] -= amount
            to_account_id = row.get("TransferToAccountID", "")
            if to_account_id and to_account_id in balances:
                balances[to_account_id] += amount
    return balances


def get_or_create_account_id(account_name: str) -> str:
    name = account_name.strip()
    for account in st.session_state.accounts:
        if account.name.strip().lower() == name.lower():
            return account.id
    add_account(name, 0.0)
    # state refreshed in add_account()
    for account in st.session_state.accounts:
        if account.name.strip().lower() == name.lower():
            return account.id
    return st.session_state.accounts[-1].id


def parse_pasted_data(text: str) -> pd.DataFrame:
    raw = text.strip()
    if not raw:
        return pd.DataFrame(
            columns=["Date", "Title", "Category", "Account", "Type", "Amount", "Note"]
        )

    # Try CSV first
    try:
        csv_df = pd.read_csv(pd.io.common.StringIO(raw))
        normalized = {c.strip().lower(): c for c in csv_df.columns}
        needed = {"date", "title", "category", "account", "type", "amount"}
        if needed.issubset(set(normalized.keys())):
            df = csv_df.rename(columns={normalized[k]: k.title() for k in normalized.keys()})
            df = df.rename(columns={"Type": "Type", "Amount": "Amount"})
            out = pd.DataFrame(
                {
                    "Date": df["Date"].astype(str),
                    "Title": df["Title"].astype(str).fillna(""),
                    "Category": df["Category"].astype(str).fillna("Other"),
                    "Account": df["Account"].astype(str).fillna("Cash"),
                    "Type": df["Type"].astype(str).str.title(),
                    "Amount": df["Amount"],
                    "Note": df["Note"].astype(str).fillna("") if "Note" in df.columns else "",
                }
            )
            out["Amount"] = out["Amount"].astype(str).apply(parse_amount)
            return out
    except Exception:
        pass

    # Fallback: parse the "Income Expenses Tag Date Account Comment" table
    lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
    if not lines:
        return pd.DataFrame(
            columns=["Date", "Title", "Category", "Account", "Type", "Amount", "Note"]
        )

    # Drop header if present
    header = lines[0].lower().replace("\t", " ")
    if "income" in header and "expenses" in header and "date" in header and "account" in header:
        lines = lines[1:]

    rows = []
    for line in lines:
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 6:
            parts = [p.strip() for p in line.split() if p.strip()]
            if len(parts) < 6:
                continue

        income_str, expense_str, tag, dt, account, comment = parts[:6]
        if income_str and expense_str:
            # ambiguous; skip
            continue
        if not income_str and not expense_str:
            continue

        kind = "Income" if income_str else "Expense"
        amount = parse_amount(income_str or expense_str)
        rows.append(
            {
                "Date": dt,
                "Title": comment,
                "Category": tag,
                "Account": account,
                "Type": kind,
                "Amount": amount,
                "Note": "",
            }
        )

    return pd.DataFrame(rows, columns=["Date", "Title", "Category", "Account", "Type", "Amount", "Note"])


def import_transactions_from_df(df: pd.DataFrame) -> Tuple[int, int]:
    """
    Returns (imported_count, skipped_count).
    """
    imported = 0
    skipped = 0

    for _, row in df.iterrows():
        try:
            dt = parse_ddmmyyyy(str(row["Date"]))
            title = str(row.get("Title", "")).strip()
            category = str(row.get("Category", "Other")).strip() or "Other"
            account_name = str(row.get("Account", "Cash")).strip() or "Cash"
            kind = str(row.get("Type", "")).strip().title()
            amount = float(row.get("Amount"))
            note = str(row.get("Note", "")).strip()

            if kind not in {"Income", "Expense"}:
                raise ValueError("Invalid type")
            if not title:
                title = "Imported"
            if amount <= 0:
                raise ValueError("Amount must be > 0")

            account_id = get_or_create_account_id(account_name)
            add_transaction(dt, title, category, kind, amount, note, account_id)
            imported += 1
        except Exception:
            skipped += 1

    return imported, skipped


def render_summary(df: pd.DataFrame) -> None:
    income_total = float(df.loc[df["Type"] == "Income", "Amount"].sum()) if not df.empty else 0.0
    expense_total = float(df.loc[df["Type"] == "Expense", "Amount"].sum()) if not df.empty else 0.0
    balance = income_total - expense_total

    first, second, third = st.columns(3)
    first.metric("Total income", format_currency(income_total))
    second.metric("Total expenses", format_currency(expense_total))
    third.metric("Balance", format_currency(balance))

    st.markdown("#### Accounts")
    all_df = build_dataframe(st.session_state.transactions)
    balances = compute_account_balances(all_df)
    cols = st.columns(min(4, max(1, len(st.session_state.accounts))))
    for idx, account in enumerate(st.session_state.accounts):
        cols[idx % len(cols)].metric(account.name, format_currency(balances.get(account.id, 0.0)))


def render_add_form() -> None:
    st.subheader("Add a transaction")
    with st.form("add_transaction_form", clear_on_submit=True):
        first, second, third = st.columns(3)
        entry_date = first.date_input("Date", value=date.today())
        kind = second.selectbox("Type", ["Expense", "Income"])
        accounts = st.session_state.accounts
        account_labels = [account.name for account in accounts]
        selected_account_name = third.selectbox("Account/Card", account_labels)
        account_id = next(a.id for a in accounts if a.name == selected_account_name)

        title = st.text_input("Title")
        category = st.selectbox("Category", CATEGORIES)
        amount = st.number_input("Amount", min_value=0.01, step=0.01, format="%.2f")
        note = st.text_area("Note", placeholder="Optional note")

        submitted = st.form_submit_button("Save transaction", use_container_width=True)
        if submitted:
            if not title.strip():
                st.error("Please enter a title.")
                return
            add_transaction(entry_date, title, category, kind, amount, note, account_id)
            st.success("Transaction added.")
            st.rerun()


def render_manage_accounts() -> None:
    st.sidebar.markdown("---")
    st.sidebar.header("Accounts/Cards")

    with st.sidebar.expander("Import (paste table or CSV)", expanded=False):
        st.caption(
            "Paste either your tab-separated table (Income/Expenses/Tag/Date/Account/Comment) "
            "or a CSV with columns Date,Title,Category,Account,Type,Amount[,Note]."
        )
        pasted = st.text_area("Paste here", key="import_paste", height=180)
        preview = parse_pasted_data(pasted) if pasted.strip() else pd.DataFrame()
        if not preview.empty:
            st.dataframe(preview.head(50), use_container_width=True, hide_index=True)
            st.caption(f"Previewing {min(50, len(preview))} of {len(preview)} rows.")
        if st.button("Import pasted data", type="primary", use_container_width=True):
            df = parse_pasted_data(pasted)
            if df.empty:
                st.sidebar.error("Nothing to import.")
            else:
                imported, skipped = import_transactions_from_df(df)
                st.sidebar.success(f"Imported {imported} rows. Skipped {skipped}.")
                st.rerun()

    with st.sidebar.expander("Transfer money", expanded=False):
        accounts = st.session_state.accounts
        if len(accounts) < 2:
            st.info("Add at least 2 accounts to make transfers.")
        else:
            names = [a.name for a in accounts]
            t_date = st.date_input("Date", value=date.today(), key="transfer_date")
            from_name = st.selectbox("From", names, key="transfer_from")
            to_name = st.selectbox("To", names, index=1 if len(names) > 1 else 0, key="transfer_to")
            t_amount = st.number_input(
                "Amount",
                min_value=0.01,
                step=100.0,
                format="%.2f",
                key="transfer_amount",
            )
            t_note = st.text_input("Note", key="transfer_note", placeholder="Optional")

            if st.button("Transfer", type="primary", use_container_width=True):
                if from_name == to_name:
                    st.error("From and To accounts must be different.")
                else:
                    from_id = next(a.id for a in accounts if a.name == from_name)
                    to_id = next(a.id for a in accounts if a.name == to_name)
                    add_transfer(t_date, from_id, to_id, t_amount, t_note.strip())
                    st.success("Transfer added.")
                    st.rerun()

    with st.sidebar.expander("Add account/card", expanded=False):
        name = st.text_input("Name", key="new_account_name", placeholder="Kaspi Card")
        starting_balance = st.number_input(
            "Starting balance",
            key="new_account_starting_balance",
            value=0.0,
            step=100.0,
            format="%.2f",
        )
        if st.button("Add account", use_container_width=True):
            if not name.strip():
                st.sidebar.error("Please enter a name.")
            else:
                add_account(name, starting_balance)
                st.sidebar.success("Account added.")
                st.rerun()

    with st.sidebar.expander("Delete account/card", expanded=False):
        accounts = st.session_state.accounts
        labels = {account_label(a): a.id for a in accounts}
        selected = st.selectbox("Select account", list(labels.keys()), key="delete_account_select")
        if st.button("Delete account", type="secondary", use_container_width=True):
            ok, message = delete_account(labels[selected])
            if ok:
                st.sidebar.success(message)
                st.rerun()
            else:
                st.sidebar.error(message)


def render_transactions(df: pd.DataFrame) -> None:
    st.subheader("Transactions")
    if df.empty:
        st.info("No transactions yet. Add your first income or expense above.")
        return

    drop_cols = [c for c in ["ID", "AccountID", "TransferToAccountID"] if c in df.columns]
    display_df = df.drop(columns=drop_cols).copy()
    display_df["Amount"] = display_df.apply(
        lambda row: format_currency(row["Amount"])
        if row["Type"] == "Income"
        else f"-{format_currency(row['Amount'])}"
        if row["Type"] == "Expense"
        else format_currency(row["Amount"]),
        axis=1,
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("#### Delete an entry")
    options = {
        f"{row['Date']} · {row['Title']} · {row['Type']} · {format_currency(row['Amount'])}": row["ID"]
        for _, row in df.iterrows()
    }
    selected_label = st.selectbox("Choose an entry to delete", list(options.keys()))
    if st.button("Delete selected transaction", type="secondary", use_container_width=True):
        delete_transaction(options[selected_label])
        st.success("Transaction deleted.")
        st.rerun()


def render_category_chart(df: pd.DataFrame) -> None:
    st.subheader("Expenses by category")
    expense_df = df[df["Type"] == "Expense"]
    if expense_df.empty:
        st.caption("Add expense entries to see category insights.")
        return

    summary = (
        expense_df.groupby("Category", as_index=False)["Amount"]
        .sum()
        .sort_values("Amount", ascending=False)
    )
    st.bar_chart(summary.set_index("Category"))


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="💰", layout="wide")

    if not render_login():
        return

    initialize_state()

    st.title(APP_TITLE)
    st.caption("Track your income and expenses in one place.")

    render_logout()
    render_manage_accounts()
    render_add_form()
    df = build_dataframe(st.session_state.transactions)
    filtered_df = filtered_dataframe(df)

    render_summary(filtered_df)
    left, right = st.columns([2, 1])
    with left:
        render_transactions(filtered_df)
    with right:
        render_category_chart(filtered_df)


if __name__ == "__main__":
    main()
