from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import List
from uuid import uuid4

import pandas as pd
import streamlit as st


APP_TITLE = "Finance Tracker"
DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "transactions.json"
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


@dataclass
class Transaction:
    id: str
    entry_date: str
    title: str
    category: str
    kind: str
    amount: float
    note: str


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def load_transactions() -> List[Transaction]:
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
            )
        )
    return transactions


def save_transactions(transactions: List[Transaction]) -> None:
    ensure_storage()
    payload = [asdict(transaction) for transaction in transactions]
    DATA_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def initialize_state() -> None:
    if "transactions" not in st.session_state:
        st.session_state.transactions = load_transactions()


def add_transaction(
    entry_date: date,
    title: str,
    category: str,
    kind: str,
    amount: float,
    note: str,
) -> None:
    transaction = Transaction(
        id=str(uuid4()),
        entry_date=entry_date.isoformat(),
        title=title.strip(),
        category=category,
        kind=kind,
        amount=round(float(amount), 2),
        note=note.strip(),
    )
    st.session_state.transactions.insert(0, transaction)
    save_transactions(st.session_state.transactions)


def delete_transaction(transaction_id: str) -> None:
    st.session_state.transactions = [
        item for item in st.session_state.transactions if item.id != transaction_id
    ]
    save_transactions(st.session_state.transactions)


def build_dataframe(transactions: List[Transaction]) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame(
            columns=["Date", "Title", "Category", "Type", "Amount", "Note"]
        )

    rows = []
    for item in transactions:
        rows.append(
            {
                "ID": item.id,
                "Date": datetime.fromisoformat(item.entry_date).strftime("%Y-%m-%d"),
                "Title": item.title,
                "Category": item.category,
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
    selected_type = st.sidebar.selectbox("Transaction type", ["All", "Income", "Expense"])
    categories = ["All"] + sorted(df["Category"].dropna().unique().tolist())
    selected_category = st.sidebar.selectbox("Category", categories)
    search_text = st.sidebar.text_input("Search title or note")

    filtered = df.copy()
    if selected_type != "All":
        filtered = filtered[filtered["Type"] == selected_type]
    if selected_category != "All":
        filtered = filtered[filtered["Category"] == selected_category]
    if search_text.strip():
        query = search_text.strip().lower()
        filtered = filtered[
            filtered["Title"].str.lower().str.contains(query)
            | filtered["Note"].fillna("").str.lower().str.contains(query)
        ]

    return filtered


def render_summary(df: pd.DataFrame) -> None:
    income_total = float(df.loc[df["Type"] == "Income", "Amount"].sum()) if not df.empty else 0.0
    expense_total = float(df.loc[df["Type"] == "Expense", "Amount"].sum()) if not df.empty else 0.0
    balance = income_total - expense_total

    first, second, third = st.columns(3)
    first.metric("Total income", format_currency(income_total))
    second.metric("Total expenses", format_currency(expense_total))
    third.metric("Balance", format_currency(balance))


def render_add_form() -> None:
    st.subheader("Add a transaction")
    with st.form("add_transaction_form", clear_on_submit=True):
        first, second = st.columns(2)
        entry_date = first.date_input("Date", value=date.today())
        kind = second.selectbox("Type", ["Expense", "Income"])

        title = st.text_input("Title")
        category = st.selectbox("Category", CATEGORIES)
        amount = st.number_input("Amount", min_value=0.01, step=0.01, format="%.2f")
        note = st.text_area("Note", placeholder="Optional note")

        submitted = st.form_submit_button("Save transaction", use_container_width=True)
        if submitted:
            if not title.strip():
                st.error("Please enter a title.")
                return
            add_transaction(entry_date, title, category, kind, amount, note)
            st.success("Transaction added.")
            st.rerun()


def render_transactions(df: pd.DataFrame) -> None:
    st.subheader("Transactions")
    if df.empty:
        st.info("No transactions yet. Add your first income or expense above.")
        return

    display_df = df.drop(columns=["ID"]).copy()
    display_df["Amount"] = display_df.apply(
        lambda row: format_currency(row["Amount"]) if row["Type"] == "Income" else f"-{format_currency(row['Amount'])}",
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
    initialize_state()

    st.title(APP_TITLE)
    st.caption("Track your income and expenses in one place.")

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
