import streamlit as st

st.set_page_config(
    page_title="DispatchDesk",
    page_icon="📋",
    layout="wide",
)

st.title("DispatchDesk")
st.caption("Incident Coordination & Operations Dashboard")

st.info(
    "Prototype environment ready. "
    "All operational data will be fictional."
)

st.subheader("System overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Open incidents", "—")

with col2:
    st.metric("Assigned resources", "—")

with col3:
    st.metric("Resolved today", "—")

st.divider()

st.subheader("Recent activity")
st.write(
    "Incident records and operational activity "
    "will appear here as we build the application."
)

st.caption("DispatchDesk · Development prototype")
