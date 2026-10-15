
import streamlit as st
import pandas as pd

from database import get_connection, initialise_database


st.set_page_config(
    page_title="DispatchDesk",
    page_icon="📋",
    layout="wide",
)

# Make sure the database tables exist before querying them.
initialise_database()


def load_dashboard_data():
    """Load summary metrics and recent incidents from SQLite."""
    with get_connection() as connection:
        open_incidents = connection.execute(
            """
            SELECT COUNT(*)
            FROM incidents
            WHERE status IN ('new', 'assigned', 'in_progress')
            """
        ).fetchone()[0]

        assigned_resources = connection.execute(
            """
            SELECT COUNT(*)
            FROM resources
            WHERE availability_status = 'assigned'
            """
        ).fetchone()[0]

        resolved_today = connection.execute(
            """
            SELECT COUNT(*)
            FROM incidents
            WHERE status = 'resolved'
              AND date(resolved_at) = date('now')
            """
        ).fetchone()[0]

        recent_incidents = connection.execute(
            """
            SELECT
                incident_id,
                title,
                category,
                priority,
                location_label,
                status,
                created_at
            FROM incidents
            ORDER BY incident_id DESC
            LIMIT 10
            """
        ).fetchall()

    incidents_df = pd.DataFrame(
        [dict(row) for row in recent_incidents]
    )

    return (
        open_incidents,
        assigned_resources,
        resolved_today,
        incidents_df,
    )


open_count, assigned_count, resolved_count, incidents_df = (
    load_dashboard_data()
)


st.title("DispatchDesk")
st.caption("Incident Coordination & Operations Dashboard")

st.info(
    "Prototype environment ready. "
    "All operational data is fictional."
)

st.subheader("System overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Open incidents", open_count)

with col2:
    st.metric("Assigned resources", assigned_count)

with col3:
    st.metric("Resolved today", resolved_count)

st.divider()

st.subheader("Incident register")

if incidents_df.empty:
    st.info("No incidents have been recorded yet.")
else:
    st.dataframe(
        incidents_df,
        use_container_width=True,
        hide_index=True,
    )

st.caption("DispatchDesk · Development prototype")

import streamlit as st
import pandas as pd

from database import get_connection, initialise_database


st.set_page_config(
    page_title="DispatchDesk",
    page_icon="📋",
    layout="wide",
)

# Make sure the database tables exist before querying them.
initialise_database()


def load_dashboard_data():
    """Load summary metrics and recent incidents from SQLite."""
    with get_connection() as connection:
        open_incidents = connection.execute(
            """
            SELECT COUNT(*)
            FROM incidents
            WHERE status IN ('new', 'assigned', 'in_progress')
            """
        ).fetchone()[0]

        assigned_resources = connection.execute(
            """
            SELECT COUNT(*)
            FROM resources
            WHERE availability_status = 'assigned'
            """
        ).fetchone()[0]

        resolved_today = connection.execute(
            """
            SELECT COUNT(*)
            FROM incidents
            WHERE status = 'resolved'
              AND date(resolved_at) = date('now')
            """
        ).fetchone()[0]

        recent_incidents = connection.execute(
            """
            SELECT
                incident_id,
                title,
                category,
                priority,
                location_label,
                status,
                created_at
            FROM incidents
            ORDER BY incident_id DESC
            LIMIT 10
            """
        ).fetchall()

    incidents_df = pd.DataFrame(
        [dict(row) for row in recent_incidents]
    )

    return (
        open_incidents,
        assigned_resources,
        resolved_today,
        incidents_df,
    )


open_count, assigned_count, resolved_count, incidents_df = (
    load_dashboard_data()
)


st.title("DispatchDesk")
st.caption("Incident Coordination & Operations Dashboard")

st.info(
    "Prototype environment ready. "
    "All operational data is fictional."
)

st.subheader("System overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Open incidents", open_count)

with col2:
    st.metric("Assigned resources", assigned_count)

with col3:
    st.metric("Resolved today", resolved_count)

st.divider()

st.subheader("Incident register")

if incidents_df.empty:
    st.info("No incidents have been recorded yet.")
else:
    st.dataframe(
        incidents_df,
        use_container_width=True,
        hide_index=True,
    )

st.caption("DispatchDesk · Development prototype")
