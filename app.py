
import streamlit as st
import pandas as pd

from database import (
    get_connection,
    initialise_database,
    create_incident,
    update_incident_status,
)


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


with st.expander("＋ Create a new incident", expanded=False):
    st.write("Enter the details of a fictional incident.")

    with st.form("create_incident_form", clear_on_submit=True):
        title = st.text_input(
            "Incident title",
            max_chars=120,
        )

        description = st.text_area(
            "Description",
            max_chars=1000,
        )

        form_col1, form_col2 = st.columns(2)

        with form_col1:
            category = st.selectbox(
                "Category",
                [
                    "Traffic",
                    "Infrastructure",
                    "Public Assistance",
                    "Public Safety",
                    "Other",
                ],
            )

            priority = st.selectbox(
                "Priority",
                ["low", "medium", "high", "critical"],
                index=1,
            )

        with form_col2:
            location_label = st.selectbox(
                "Fictional location",
                [
                    "Demo Zone A",
                    "Demo Zone B",
                    "Demo Zone C",
                    "Demo Zone D",
                    "Demo Zone E",
                    "Demo Zone F",
                ],
            )

        submitted = st.form_submit_button(
            "Create incident",
            type="primary",
        )

        if submitted:
            if not title.strip() or not description.strip():
                st.error("Please enter both a title and a description.")
            else:
                try:
                    new_id = create_incident(
                        title=title,
                        description=description,
                        category=category,
                        priority=priority,
                        location_label=location_label,
                    )
                    st.success(f"Incident #{new_id} created successfully.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Could not create incident: {error}")

with st.expander("↻ Update incident status", expanded=False):
    with get_connection() as connection:
        status_options = connection.execute(
            """
            SELECT incident_id, title, status
            FROM incidents
            ORDER BY incident_id DESC
            """
        ).fetchall()

    if not status_options:
        st.info("Create an incident before updating its status.")
    else:
        incident_lookup = {
            f"#{row['incident_id']} — {row['title']} [{row['status']}]":
                row["incident_id"]
            for row in status_options
        }

        with st.form("update_incident_status_form"):
            selected_incident = st.selectbox(
                "Select incident",
                options=list(incident_lookup.keys()),
            )

            new_status = st.selectbox(
                "New status",
                [
                    "new",
                    "assigned",
                    "in_progress",
                    "resolved",
                    "cancelled",
                ],
            )

            update_submitted = st.form_submit_button(
                "Update status",
                type="primary",
            )

            if update_submitted:
                try:
                    changed = update_incident_status(
                        incident_lookup[selected_incident],
                        new_status,
                    )

                    if changed:
                        st.success("Incident status updated.")
                    else:
                        st.info("The incident already has that status.")

                    st.rerun()

                except (ValueError, Exception) as error:
                    st.error(f"Could not update incident: {error}")



st.subheader("Incident register")

if incidents_df.empty:
    st.info("No incidents have been recorded yet.")
else:
    # Search and filter controls
    search_col, priority_col, status_col = st.columns([2, 1, 1])

    with search_col:
        search_text = st.text_input(
            "Search incidents",
            placeholder="Search by title or location...",
        )

    with priority_col:
        selected_priority = st.selectbox(
            "Priority",
            ["All", "Critical", "High", "Medium", "Low"],
        )

    with status_col:
        selected_status = st.selectbox(
            "Status",
            [
                "All",
                "New",
                "Assigned",
                "In Progress",
                "Resolved",
                "Cancelled",
            ],
        )

    # Start with all records, then narrow the displayed results.
    filtered_df = incidents_df.copy()

    if search_text:
        search_mask = (
            filtered_df["title"].str.contains(
                search_text, case=False, na=False
            )
            | filtered_df["location_label"].str.contains(
                search_text, case=False, na=False
            )
        )
        filtered_df = filtered_df[search_mask]

    if selected_priority != "All":
        filtered_df = filtered_df[
            filtered_df["priority"] == selected_priority.lower()
        ]

    if selected_status != "All":
        status_value = selected_status.lower().replace(" ", "_")
        filtered_df = filtered_df[
            filtered_df["status"] == status_value
        ]

    st.caption(f"Showing {len(filtered_df)} of {len(incidents_df)} incidents")

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
    )

st.caption("DispatchDesk · Development prototype")
