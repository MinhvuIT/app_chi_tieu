"""Streamlit dashboard for personal finance tracking."""

import hmac

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

import database


EXPENSE_TYPE = "Chi tiêu"
INCOME_TYPE = "Thu nhập"
TRANSACTION_TYPES = [EXPENSE_TYPE, INCOME_TYPE]
CATEGORIES = {
    EXPENSE_TYPE: [
        "Ăn uống",
        "Di chuyển",
        "Nhà ở",
        "Hóa đơn",
        "Mua sắm",
        "Sức khỏe",
        "Giải trí",
        "Giáo dục",
        "Khác",
    ],
    INCOME_TYPE: [
        "Lương",
        "Thưởng",
        "Đầu tư",
        "Kinh doanh",
        "Quà tặng",
        "Khác",
    ],
}


def format_vnd(amount: float) -> str:
    """Format an amount as Vietnamese đồng without decimal places."""
    return f"{amount:,.0f}".replace(",", ".") + " ₫"


st.set_page_config(page_title="Quản lý chi tiêu", page_icon="💰", layout="wide")

try:
    app_password = st.secrets["APP_PASSWORD"]
except (KeyError, StreamlitSecretNotFoundError):
    st.error("Hãy cấu hình APP_PASSWORD trong Streamlit secrets trước khi sử dụng.")
    st.stop()

if not isinstance(app_password, str) or not app_password:
    st.error("APP_PASSWORD phải là một chuỗi không rỗng trong Streamlit secrets.")
    st.stop()

if not st.session_state.get("authenticated", False):
    st.title("Đăng nhập")
    with st.form("login_form"):
        entered_password = st.text_input("Mật khẩu", type="password")
        login_submitted = st.form_submit_button("Đăng nhập", type="primary")
    if login_submitted:
        if hmac.compare_digest(entered_password, app_password):
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Mật khẩu không đúng.")
    st.stop()

st.title("💰 Quản lý tài chính cá nhân")
st.caption("Theo dõi thu nhập, chi tiêu và tiến độ mục tiêu tài chính của bạn.")

with st.sidebar:
    if st.button("Đăng xuất"):
        st.session_state["authenticated"] = False
        st.rerun()

    st.header("Mục tiêu tài chính")
    saving_goal = st.number_input(
        "Mục tiêu tiết kiệm (₫)",
        min_value=0,
        value=5_000_000,
        step=500_000,
        format="%d",
        help="Số dư ròng mong muốn đạt được.",
    )
    budget_limit = st.number_input(
        "Hạn mức chi tiêu (₫)",
        min_value=0,
        value=10_000_000,
        step=500_000,
        format="%d",
        help="Tổng chi tiêu được phép trong kỳ đang theo dõi.",
    )

st.subheader("Thêm giao dịch")
form_column, guidance_column = st.columns([2, 1])

with form_column:
    transaction_type = st.selectbox("Loại giao dịch", TRANSACTION_TYPES)
    with st.form("add_transaction_form", clear_on_submit=True):
        category = st.selectbox("Danh mục", CATEGORIES[transaction_type])
        amount = st.number_input(
            "Số tiền (₫)",
            min_value=0,
            value=0,
            step=10_000,
            format="%d",
        )
        note = st.text_input("Ghi chú")
        submitted = st.form_submit_button("Thêm giao dịch", type="primary")

    if submitted:
        if amount <= 0:
            st.error("Số tiền phải lớn hơn 0.")
        elif not note.strip():
            st.error("Vui lòng nhập ghi chú cho giao dịch.")
        else:
            try:
                database.add_transaction(
                    amount=amount,
                    category=category,
                    transaction_type=transaction_type,
                    note=note,
                )
            except ValueError as error:
                st.error(str(error))
            else:
                st.session_state["transaction_notice"] = "Đã thêm giao dịch."
                st.rerun()

with guidance_column:
    st.info(
        "Chọn loại giao dịch để xem các danh mục phù hợp. "
        "Giao dịch mới được lưu vào Supabase."
    )

notice = st.session_state.pop("transaction_notice", None)
if notice:
    st.success(notice)

transactions = database.get_transactions()
income_total = transactions.loc[
    transactions["type"] == INCOME_TYPE, "amount"
].sum()
expense_total = transactions.loc[
    transactions["type"] == EXPENSE_TYPE, "amount"
].sum()
net_balance = income_total - expense_total

st.subheader("Tổng quan tài chính")
income_metric, expense_metric, balance_metric = st.columns(3)
income_metric.metric("Tổng thu nhập", format_vnd(income_total))
expense_metric.metric("Tổng chi tiêu", format_vnd(expense_total))
balance_metric.metric("Số dư hiện tại", format_vnd(net_balance))

progress_column, budget_column = st.columns(2)
with progress_column:
    st.subheader("Tiến độ tiết kiệm")
    if saving_goal == 0:
        st.info("Đặt mục tiêu tiết kiệm lớn hơn 0 để theo dõi tiến độ.")
    else:
        progress = min(max(net_balance / saving_goal, 0.0), 1.0)
        st.progress(progress)
        st.write(
            f"Đã đạt **{format_vnd(max(net_balance, 0))}** trên "
            f"mục tiêu **{format_vnd(saving_goal)}** "
            f"({progress:.0%})."
        )
        if net_balance >= saving_goal:
            st.success("Tuyệt vời! Bạn đã đạt mục tiêu tiết kiệm.")
        elif net_balance >= 0:
            st.info(f"Còn {format_vnd(saving_goal - net_balance)} để đạt mục tiêu.")
        else:
            st.warning("Chi tiêu hiện đang cao hơn thu nhập; hãy xem lại ngân sách.")

with budget_column:
    st.subheader("Hạn mức chi tiêu")
    if budget_limit == 0:
        st.info("Đặt hạn mức lớn hơn 0 để theo dõi ngân sách.")
    else:
        budget_usage = expense_total / budget_limit
        st.progress(min(max(budget_usage, 0.0), 1.0))
        st.write(
            f"Đã chi **{format_vnd(expense_total)}** trên "
            f"hạn mức **{format_vnd(budget_limit)}** "
            f"({budget_usage:.0%})."
        )
        if budget_usage >= 1:
            st.error("Bạn đã vượt hạn mức chi tiêu.")
        elif budget_usage >= 0.8:
            st.warning("Bạn đã sử dụng ít nhất 80% hạn mức chi tiêu.")
        else:
            st.success("Chi tiêu vẫn nằm trong hạn mức.")

st.subheader("Cơ cấu chi tiêu theo danh mục")
expenses = transactions.loc[transactions["type"] == EXPENSE_TYPE]
if expenses.empty:
    st.info("Chưa có dữ liệu chi tiêu để vẽ biểu đồ.")
else:
    expense_by_category = (
        expenses.groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
    )
    figure = px.pie(
        expense_by_category,
        names="category",
        values="amount",
        hole=0.35,
        title="Tỷ trọng chi tiêu",
    )
    figure.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="%{label}<br>%{value:,.0f} ₫<extra></extra>",
    )
    figure.update_layout(margin=dict(t=55, b=10, l=10, r=10))
    st.plotly_chart(figure, width="stretch")

st.subheader("Lịch sử giao dịch")
if transactions.empty:
    st.info("Chưa có giao dịch nào. Hãy thêm giao dịch đầu tiên ở phía trên.")
else:
    history = transactions.sort_values("id", ascending=False).copy()
    history["date"] = pd.to_datetime(history["date"]).dt.strftime("%Y-%m-%d")
    st.dataframe(
        history,
        width="stretch",
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("Mã", format="%d"),
            "date": st.column_config.TextColumn("Ngày"),
            "amount": st.column_config.NumberColumn("Số tiền (₫)", format="%.0f"),
            "category": st.column_config.TextColumn("Danh mục"),
            "type": st.column_config.TextColumn("Loại"),
            "note": st.column_config.TextColumn("Ghi chú"),
        },
    )
