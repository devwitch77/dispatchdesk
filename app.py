
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
# Page configuration and initialization
# --------------------------------------------------

st.set_page_config(
    page_title="DispatchDesk",
    page_icon="📋",
    layout="wide",
)

initialise_database()


# --------------------------------------------------
# Data loading
# --------------------------------------------------

def load_dashboard_data():
    with get_connection() as connection:
        open_incidents = connection.execute(
            """
            SELECT COUNT(*) FROM incidents
            WHERE status IN ('new', 'assigned', 'in_progress')
            """
        ).fetchone()[0]

        assigned_resources = connection.execute(
            """
            SELECT COUNT(*) FROM resources
            WHERE availability_status = 'assigned'
            """
        ).fetchone()[0]

        resolved_today = connection.execute(
            """
            SELECT COUNT(*) FROM incidents
            WHERE status = 'resolved'
              AND date(resolved_at) = date('now', 'localtime')
            """
        ).fetchone()[0]

        priority_counts = connection.execute(
            """
            SELECT priority, COUNT(*) AS incident_count
            FROM incidents
            GROUP BY priority
            """
        ).fetchall()

        status_counts = connection.execute(
            """
            SELECT status, COUNT(*) AS incident_count
            FROM incidents
            GROUP BY status
            """
        ).fetchall()

        daily_counts = connection.execute(
            """
            SELECT
                date(created_at) AS incident_date,
                COUNT(*) AS incident_count
            FROM incidents
            GROUP BY date(created_at)
            ORDER BY incident_date
            """
        ).fetchall()

        incidents = connection.execute(
            """
            SELECT
                incident_id,
                title,
                category,
                priority,
                status,
                location_label,
                assigned_resource_id,
                created_at,
                ROUND(
                    (julianday('now') - julianday(created_at)) * 24,
                    1
                ) AS age_hours
            FROM incidents
            ORDER BY created_at DESC
            LIMIT 10
            """
        ).fetchall()

        activity = connection.execute(
            """
            SELECT
                audit_events.event_id,
                audit_events.incident_id,
                audit_events.event_type,
                audit_events.old_value,
                audit_events.new_value,
                audit_events.event_at,
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
                END AS assigned_resource
            FROM audit_events
            LEFT JOIN incidents
                ON audit_events.incident_id = incidents.incident_id
            LEFT JOIN resources
                ON incidents.assigned_resource_id = resources.resource_id
            ORDER BY
                audit_events.event_at DESC,
                audit_events.event_id DESC
            LIMIT 10
            """
        ).fetchall()

    incidents_df = pd.DataFrame([dict(row) for row in incidents])
    activity_df = pd.DataFrame([dict(row) for row in activity])
    priority_df = pd.DataFrame([dict(row) for row in priority_counts])
    status_df = pd.DataFrame([dict(row) for row in status_counts])
    daily_df = pd.DataFrame([dict(row) for row in daily_counts])

    return (
        open_incidents,
        assigned_resources,
        resolved_today,
        incidents_df,
        activity_df,
        priority_df,
        status_df,
        daily_df,
    )


(
    open_count,
    assigned_count,
    resolved_count,
    incidents_df,
    activity_df,
    priority_df,
    status_df,
    daily_df,
) = load_dashboard_data()


# --------------------------------------------------
# Dashboard header
# --------------------------------------------------

st.title("DispatchDesk")
st.caption("Incident Coordination & Operations Dashboard")

st.info(
    "Prototype environment ready. All operational data is fictional."
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
# Operational analytics
# --------------------------------------------------

st.header("Operational Analytics")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Incidents by Priority")

    if not priority_df.empty:
        st.bar_chart(
            priority_df.set_index("priority")["incident_count"]
        )
    else:
        st.info("No incident data available yet.")

with chart_col2:
    st.subheader("Incidents by Status")

    if not status_df.empty:
        st.bar_chart(
            status_df.set_index("status")["incident_count"]
        )
    else:
        st.info("No incident data available yet.")

st.subheader("Daily Incident Volume")

if not daily_df.empty:
    daily_chart = daily_df.copy()
    daily_chart["incident_date"] = pd.to_datetime(
        daily_chart["incident_date"]
    )
    daily_chart = daily_chart.set_index("incident_date")
    daily_chart = daily_chart[["incident_count"]]

    today_utc = (
        pd.Timestamp.now(tz="UTC")
        .normalize()
        .tz_localize(None)
    )

    last_seven_days = pd.date_range(
        end=today_utc,
        periods=7,
        freq="D",
    )

    daily_chart = daily_chart.reindex(
        last_seven_days,
        fill_value=0,
    )
    daily_chart.index.name = "Date"

    st.line_chart(
        daily_chart["incident_count"],
        x_label="Date (UTC)",
        y_label="Incidents created",
    )

    st.caption(
        "Daily incident counts for the last seven UTC calendar days. "
        "Missing dates are shown as zero."
    )
else:
    st.info("No incident history is available yet.")


# --------------------------------------------------
# Create an incident with NLP assistance
# --------------------------------------------------

with st.expander("＋ Create a new incident", expanded=False):
    st.write("Enter the details of a fictional incident.")

    title = st.text_input(
        "Incident title",
        max_chars=120,
        key="new_incident_title",
    )

    description = st.text_area(
        "Description",
        max_chars=1000,
        key="new_incident_description",
        help="Describe the fictional incident in ordinary language.",
    )

    # The description associated with a suggestion is tracked so an old
    # suggestion is not silently treated as a prediction for new text.
    if st.button(
        "Suggest category with NLP",
        key="suggest_incident_category",
    ):
        if not description.strip():
            st.warning(
                "Enter a description before requesting a suggestion."
            )
        else:
            try:
                from incident_classifier import suggest_category

                suggestion = suggest_category(description.strip())

                st.session_state["incident_category_suggestion"] = (
                    suggestion["category"]
                )
                st.session_state["incident_category_confidence"] = (
                    suggestion["confidence"]
                )
                st.session_state["incident_category_needs_review"] = (
                    suggestion["needs_review"]
                )
                st.session_state["incident_category_suggestion_for"] = (
                    description.strip()
                )

                # Update the category widget before it is rendered
                # on this rerun.
                st.session_state["new_incident_category"] = (
                    suggestion["category"]
                )

            except Exception as error:
                st.error(
                    f"Could not generate a suggestion: {error}"
                )

    suggestion_exists = (
        "incident_category_suggestion" in st.session_state
    )

    suggestion_matches_description = (
        suggestion_exists
        and st.session_state.get("incident_category_suggestion_for")
        == description.strip()
        and bool(description.strip())
    )

    if suggestion_matches_description:
        suggested_category = st.session_state[
            "incident_category_suggestion"
        ]
        confidence = st.session_state[
            "incident_category_confidence"
        ]
        needs_review = st.session_state.get(
            "incident_category_needs_review",
            confidence < 0.45,
        )

        st.info(
            f"NLP suggestion: {suggested_category} "
            f"(model score: {confidence:.1%})"
        )

        if needs_review:
            st.warning(
                "Low model score. Review the description carefully "
                "and choose the category manually if needed."
            )
        else:
            st.success(
                "The suggestion passed the prototype score threshold. "
                "Verify the category before submitting."
            )

        st.caption(
            "Experimental classifier trained on fictional data. "
            "The model score is not a calibrated probability of correctness. "
            "It does not determine priority or trigger dispatch."
        )

    elif suggestion_exists and description.strip():
        st.warning(
            "The description has changed since the last suggestion. "
            "Generate a new suggestion before relying on the NLP result."
        )

    with st.form("create_incident_form", clear_on_submit=True):
        category_options = [
            "Traffic",
            "Infrastructure",
            "Public Assistance",
            "Public Safety",
            "Other",
        ]

        current_category = st.session_state.get(
            "new_incident_category",
            "Traffic",
        )

        if current_category not in category_options:
            current_category = "Traffic"

        form_col1, form_col2 = st.columns(2)

        with form_col1:
            category = st.selectbox(
                "Confirm incident category",
                category_options,
                index=category_options.index(current_category),
                key="new_incident_category",
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
                        title=title.strip(),
                        description=description.strip(),
                        category=category,
                        priority=priority,
                        location_label=location_label,
                    )

                    for key in (
                        "incident_category_suggestion",
                        "incident_category_confidence",
                        "incident_category_needs_review",
                        "incident_category_suggestion_for",
                    ):
                        st.session_state.pop(key, None)

                    st.session_state.pop(
                        "new_incident_category",
                        None,
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
        st.info("Create an incident before updating its status.")
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

    filtered_df = incidents_df.copy()

    if search_text:
        search_mask = (
            filtered_df["title"].str.contains(
                search_text,
                case=False,
                na=False,
                regex=False,
            )
            | filtered_df["location_label"].str.contains(
                search_text,
                case=False,
                na=False,
                regex=False,
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

    st.caption(
        f"Showing {len(filtered_df)} of {len(incidents_df)} incidents"
    )

    if "age_hours" in filtered_df.columns:
        filtered_df["Age"] = filtered_df["age_hours"].apply(
            lambda hours: (
                f"{hours / 24:.1f} days"
                if hours >= 24
                else f"{hours:.1f} hours"
            )
        )

        filtered_df["Age indicator"] = filtered_df["age_hours"].apply(
            lambda hours: (
                "🔴 Long open"
                if hours >= 4
                else "🟡 Aging"
                if hours >= 1
                else "🟢 Recent"
            )
        )

        filtered_df = filtered_df.drop(columns=["age_hours"])

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
    "Latest events recorded in the fictional demo database."
)

if activity_df.empty:
    st.info("No activity has been recorded yet.")
else:
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
            "event_type": "Event",
            "old_value": "Previous value",
            "new_value": "New value",
            "event_at": "Recorded at (UTC)",
            "assigned_resource": "Resource",
        }
    )

    st.dataframe(
        display_activity,
        use_container_width=True,
        hide_index=True,
    )


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

    csv_data = report_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="Download handover report (CSV)",
        data=csv_data,
        file_name="dispatchdesk_handover_report.csv",
        mime="text/csv",
        type="primary",
    )


# --------------------------------------------------
# Footer
# --------------------------------------------------

st.divider()
st.caption("DispatchDesk · Development prototype")
