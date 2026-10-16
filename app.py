
import streamlit as st
import pandas as pd


from database import (
    get_connection,
    initialise_database,
    create_incident,
    update_incident_status,
    get_handover_incidents,
    assign_incident_resource,
)



# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="DispatchDesk",
    page_icon="📋",
    layout="wide",
)

# Ensure the database tables exist before querying them.
initialise_database()


# --------------------------------------------------
# Data loading
# --------------------------------------------------

def load_dashboard_data():
    """Load dashboard metrics, incidents, and recent activity."""

    with get_connection() as connection:
        # Count incidents that are not yet closed.
        open_incidents = connection.execute(
            """
            SELECT COUNT(*)
            FROM incidents
            WHERE status IN ('new', 'assigned', 'in_progress')
            """
        ).fetchone()[0]

        # Count resources currently marked as assigned.
        assigned_resources = connection.execute(
            """
            SELECT COUNT(*)
            FROM resources
            WHERE availability_status = 'assigned'
            """
        ).fetchone()[0]

        # Count incidents resolved today.
        resolved_today = connection.execute(
            """
            SELECT COUNT(*)
            FROM incidents
            WHERE status = 'resolved'
              AND date(resolved_at) = date('now')
            """
        ).fetchone()[0]

        # Fetch the ten most recently created incidents.
        recent_incidents = connection.execute(
            """
            SELECT
                incidents.incident_id,
                incidents.title,
                incidents.category,
                incidents.priority,
                incidents.location_label,
                incidents.status,
                incidents.created_at,
                COALESCE(resources.display_name, 'Unassigned')
                    AS assigned_resource
            FROM incidents
            LEFT JOIN resources
                ON resources.resource_id =
                   incidents.assigned_resource_id
            ORDER BY incidents.incident_id DESC
            LIMIT 10
            """
        ).fetchall()


        # Fetch the ten latest recorded audit events.
        recent_activity = connection.execute(
            """
            SELECT
                audit_events.event_id,
                audit_events.incident_id,
                incidents.title,
                CASE
                    WHEN audit_events.event_type IN (
                        'resource_assigned',
                        'resource_released'
                    )
                    THEN audit_events.new_value
                    ELSE COALESCE(
                        resources.display_name,
                        'Unassigned'
                    )
                END AS assigned_resource,
                audit_events.event_type,
                audit_events.old_value,
                audit_events.new_value,
                audit_events.event_at
            FROM audit_events
            JOIN incidents
                ON incidents.incident_id = audit_events.incident_id
            LEFT JOIN resources
                ON resources.resource_id =
                   incidents.assigned_resource_id
            ORDER BY audit_events.event_id DESC
            LIMIT 10
            """
        ).fetchall()



    incidents_df = pd.DataFrame(
        [dict(row) for row in recent_incidents]
    )

    activity_df = pd.DataFrame(
        [dict(row) for row in recent_activity]
    )

    return (
        open_incidents,
        assigned_resources,
        resolved_today,
        incidents_df,
        activity_df,
    )


(
    open_count,
    assigned_count,
    resolved_count,
    incidents_df,
    activity_df,
) = load_dashboard_data()


# --------------------------------------------------
# Dashboard header
# --------------------------------------------------

st.title("DispatchDesk")
st.caption("Incident Coordination & Operations Dashboard")

st.info(
    "Prototype environment ready. "
    "All operational data is fictional."
)


# --------------------------------------------------
# Summary metrics
# --------------------------------------------------

st.subheader("System overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Open incidents", open_count)

with col2:
    st.metric("Assigned resources", assigned_count)

with col3:
    st.metric("Resolved today", resolved_count)

st.divider()


# --------------------------------------------------
# Create an incident
# --------------------------------------------------

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
                st.error(
                    "Please enter both a title and a description."
                )
            else:
                try:
                    new_id = create_incident(
                        title=title,
                        description=description,
                        category=category,
                        priority=priority,
                        location_label=location_label,
                    )

                    st.success(
                        f"Incident #{new_id} created successfully."
                    )
                    st.rerun()

                except Exception as error:
                    st.error(
                        f"Could not create incident: {error}"
                    )


# --------------------------------------------------
# Update incident status
# --------------------------------------------------

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
        st.info(
            "Create an incident before updating its status."
        )

    else:
        incident_lookup = {
            f"#{row['incident_id']} — "
            f"{row['title']} [{row['status']}]":
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
                        st.rerun()
                    else:
                        st.info(
                            "The incident already has that status."
                        )

                except ValueError as error:
                    st.error(
                        f"Could not update incident: {error}"
                    )

                except Exception as error:
                    st.error(
                        f"An unexpected error occurred: {error}"
                    )




# --------------------------------------------------
# Assign a resource to an incident
# --------------------------------------------------

with st.expander("👥 Assign a resource", expanded=False):
    with get_connection() as connection:
        assignable_incidents = connection.execute(
            """
            SELECT incident_id, title, status
            FROM incidents
            WHERE status NOT IN ('resolved', 'cancelled')
            ORDER BY incident_id DESC
            """
        ).fetchall()

        available_resources = connection.execute(
            """
            SELECT resource_id, display_name, resource_type
            FROM resources
            WHERE availability_status = 'available'
            ORDER BY display_name
            """
        ).fetchall()

    if not assignable_incidents:
        st.info("There are no open incidents to assign.")

    elif not available_resources:
        st.warning(
            "No resources are currently available. "
            "Release or add a resource before assigning one."
        )

    else:
        incident_lookup = {
            f"#{row['incident_id']} — {row['title']} "
            f"[{row['status']}]": row["incident_id"]
            for row in assignable_incidents
        }

        resource_lookup = {
            f"{row['display_name']} — {row['resource_type']}":
                row["resource_id"]
            for row in available_resources
        }

        with st.form("assign_resource_form"):
            selected_incident = st.selectbox(
                "Select an open incident",
                options=list(incident_lookup.keys()),
            )

            selected_resource = st.selectbox(
                "Select an available resource",
                options=list(resource_lookup.keys()),
            )

            assignment_submitted = st.form_submit_button(
                "Assign resource",
                type="primary",
            )

            if assignment_submitted:
                try:
                    assigned = assign_incident_resource(
                        incident_lookup[selected_incident],
                        resource_lookup[selected_resource],
                    )

                    if assigned:
                        st.success("Resource assigned successfully.")
                        st.rerun()
                    else:
                        st.info(
                            "This resource is already assigned "
                            "to that incident."
                        )

                except ValueError as error:
                    st.error(f"Assignment failed: {error}")

                except Exception as error:
                    st.error(
                        f"An unexpected error occurred: {error}"
                    )




# --------------------------------------------------
# Incident register, search, and filters
# --------------------------------------------------

st.divider()
st.subheader("Incident register")

if incidents_df.empty:
    st.info("No incidents have been recorded yet.")

else:
    search_col, priority_col, status_col = st.columns(
        [2, 1, 1]
    )

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

    # Work on a copy so the original data remains unchanged.
    filtered_df = incidents_df.copy()

    if search_text:
        search_mask = (
            filtered_df["title"].str.contains(
                search_text,
                case=False,
                na=False,
            )
            | filtered_df["location_label"].str.contains(
                search_text,
                case=False,
                na=False,
            )
        )

        filtered_df = filtered_df[search_mask]

    if selected_priority != "All":
        filtered_df = filtered_df[
            filtered_df["priority"]
            == selected_priority.lower()
        ]

    if selected_status != "All":
        status_value = selected_status.lower().replace(
            " ",
            "_",
        )

        filtered_df = filtered_df[
            filtered_df["status"] == status_value
        ]

    st.caption(
        f"Showing {len(filtered_df)} of "
        f"{len(incidents_df)} incidents"
    )

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------
# Recent activity / audit trail
# --------------------------------------------------

st.divider()
st.subheader("Recent activity")
st.caption(
    "Latest status changes recorded in the fictional demo database."
)

if activity_df.empty:
    st.info("No activity has been recorded yet.")

else:
    # Make event names easier to read.
    display_activity = activity_df.copy()

    display_activity["event_type"] = (
        display_activity["event_type"]
        .str.replace("_", " ")
        .str.title()
    )

    display_activity = display_activity.rename(
        columns={
            "event_id": "Event ID",
            "incident_id": "Incident ID",
            "title": "Incident",
            "event_type": "Event",
            "old_value": "Previous status",
            "new_value": "New status",
            "event_at": "Recorded at (UTC)",
        }
    )

    # Present the newest activity first.
    st.dataframe(
        display_activity,
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------
# Footer
# --------------------------------------------------



# --------------------------------------------------
# Shift handover report
# --------------------------------------------------

st.divider()
st.subheader("Shift handover report")

st.write(
    "Review outstanding incidents and export a report "
    "for the incoming shift."
)

handover_records = get_handover_incidents()
handover_df = pd.DataFrame(handover_records)

if handover_df.empty:
    st.success("No outstanding incidents. Handover is clear.")

else:
    # Summary metrics
    critical_count = int(
        (handover_df["priority"] == "critical").sum()
    )
    high_count = int(
        (handover_df["priority"] == "high").sum()
    )
    in_progress_count = int(
        (handover_df["status"] == "in_progress").sum()
    )
    unassigned_count = int(
        handover_df["assigned_resource"].isna().sum()
    )

    st.markdown("### Handover summary")

    metric1, metric2, metric3, metric4 = st.columns(4)

    with metric1:
        st.metric("Outstanding incidents", len(handover_df))

    with metric2:
        st.metric("Critical priority", critical_count)

    with metric3:
        st.metric("High priority", high_count)

    with metric4:
        st.metric("Unassigned incidents", unassigned_count)

    st.info(
        f"{in_progress_count} incident(s) are currently in progress."
    )

    # Prepare a readable report table.
    report_df = handover_df.rename(
        columns={
            "incident_id": "Incident ID",
            "title": "Title",
            "description": "Description",
            "category": "Category",
            "priority": "Priority",
            "location_label": "Location",
            "status": "Status",
            "created_at": "Created at (UTC)",
            "updated_at": "Last updated (UTC)",
            "assigned_resource": "Assigned resource",
        }
    )

    st.dataframe(
        report_df,
        use_container_width=True,
        hide_index=True,
    )

    # Download the report as a CSV file.
    csv_data = report_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="Download handover report (CSV)",
        data=csv_data,
        file_name="dispatchdesk_handover_report.csv",
        mime="text/csv",
        type="primary",
    )


st.divider()
st.caption("DispatchDesk · Development prototype")
