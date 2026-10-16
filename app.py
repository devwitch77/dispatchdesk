
import streamlit as st
import pandas as pd
import pydeck as pdk


from database import (
    get_connection,
    initialise_database,
    create_incident,
    update_incident_status,
    get_handover_incidents,
    assign_incident_resource,
    get_locations,
    get_resources,
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

LOCATIONS = get_locations()

PRIORITY_ORDER_SQL = """
    CASE LOWER(priority)
        WHEN 'critical' THEN 0
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
        ELSE 4
    END
"""


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
                description,
                category,
                priority,
                status,
                location_label,
                latitude,
                longitude,
                assigned_resource_id,
                created_at,
                ROUND(
                    (julianday('now') - julianday(created_at)) * 24,
                    1
                ) AS age_hours
            FROM incidents
            ORDER BY
                CASE LOWER(priority)
                    WHEN 'critical' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END,
                created_at ASC,
                incident_id ASC
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
# Interactive Abu Dhabi operations map
# --------------------------------------------------

st.header("Live Operations Map")
st.caption(
    "Incident and fleet positions use prototype data. "
    "Vehicle locations are simulated, not live emergency-service tracking."
)

show_resolved = st.checkbox(
    "Show resolved incidents",
    value=False,
)

# --------------------------------------------------
# Prepare incident data
# --------------------------------------------------

map_incidents = incidents_df.copy()

if not map_incidents.empty:
    map_incidents["latitude"] = pd.to_numeric(
        map_incidents["latitude"], errors="coerce"
    )
    map_incidents["longitude"] = pd.to_numeric(
        map_incidents["longitude"], errors="coerce"
    )

    map_incidents = map_incidents.dropna(
        subset=["latitude", "longitude"]
    ).copy()

    map_incidents["status"] = (
        map_incidents["status"].astype(str).str.strip().str.lower()
    )
    map_incidents["priority"] = (
        map_incidents["priority"].astype(str).str.strip().str.lower()
    )

    if not show_resolved:
        map_incidents = map_incidents[
            map_incidents["status"] != "resolved"
        ].copy()

# --------------------------------------------------
# Cluster incidents sharing nearby approximate
# coordinates. Three decimal places groups points
# into roughly 100-metre coordinate grid cells.
# These are visual clusters, not exact addresses.
# --------------------------------------------------

map_clusters = []

if not map_incidents.empty:
    priority_colors = {
        "critical": [220, 38, 38, 230],
        "high": [234, 88, 12, 230],
        "medium": [202, 138, 4, 230],
        "low": [22, 163, 74, 230],
    }

    priority_order = ["critical", "high", "medium", "low"]

    map_incidents["cluster_lat"] = (
        map_incidents["latitude"].round(3)
    )
    map_incidents["cluster_lon"] = (
        map_incidents["longitude"].round(3)
    )

    for (cluster_lat, cluster_lon), group in map_incidents.groupby(
        ["cluster_lat", "cluster_lon"],
        sort=False,
    ):
        incident_count = len(group)

        # Use the most urgent active priority for the cluster colour.
        present_priorities = set(group["priority"])
        highest_priority = next(
            (
                priority
                for priority in priority_order
                if priority in present_priorities
            ),
            "low",
        )

        all_resolved = group["status"].eq("resolved").all()

        marker_color = (
            [107, 114, 128, 220]
            if all_resolved
            else priority_colors[highest_priority]
        )

        location_names = sorted(
            group["location_label"].dropna().astype(str).unique()
        )
        location_text = (
            ", ".join(location_names)
            if location_names
            else "Unknown location"
        )

        incident_summaries = [
            f"#{row.incident_id} {row.title}"
            for row in group.itertuples()
        ]

        # Keep the tooltip readable for larger clusters.
        visible_summaries = incident_summaries[:4]
        summary_text = "; ".join(visible_summaries)

        if incident_count > 4:
            summary_text += f"; and {incident_count - 4} more"

        priority_counts = group["priority"].value_counts()
        priority_text = ", ".join(
            f"{priority.title()}: {priority_counts[priority]}"
            for priority in priority_order
            if priority in priority_counts.index
        )

        status_counts = group["status"].value_counts()
        status_text = ", ".join(
            f"{status.replace('_', ' ').title()}: {count}"
            for status, count in status_counts.items()
        )

        map_clusters.append(
            {
                "latitude": float(group["latitude"].mean()),
                "longitude": float(group["longitude"].mean()),
                "incident_count": incident_count,
                "marker_color": marker_color,
                "marker_radius": min(
                    150 + (incident_count - 1) * 35,
                    500,
                ),
                "map_title": (
                    f"{incident_count} incident(s) — {location_text}"
                ),
                "map_line_1": f"Reports: {summary_text}",
                "map_line_2": f"Priority mix: {priority_text}",
                "map_line_3": (
                    f"Status: {status_text}. "
                    "Approximate grouped coordinates."
                ),
            }
        )

cluster_df = pd.DataFrame(map_clusters)

# --------------------------------------------------
# Prepare simulated fleet data
# --------------------------------------------------

map_resources = pd.DataFrame(get_resources())

if not map_resources.empty:
    map_resources["latitude"] = pd.to_numeric(
        map_resources["latitude"], errors="coerce"
    )
    map_resources["longitude"] = pd.to_numeric(
        map_resources["longitude"], errors="coerce"
    )

    map_resources = map_resources.dropna(
        subset=["latitude", "longitude"]
    ).copy()

    map_resources["map_title"] = (
        map_resources["unit_code"].fillna("Unknown unit").astype(str)
        + " — "
        + map_resources["display_name"].fillna("Unnamed vehicle").astype(str)
    )

    map_resources["map_line_1"] = (
        "Type: "
        + map_resources["resource_type"].fillna("Unknown").astype(str)
    )

    map_resources["map_line_2"] = (
        "Availability: "
        + map_resources["availability_status"].fillna("Unknown").astype(str)
    )

    map_resources["map_line_3"] = (
        "Position: Simulated coordinates, not live tracking."
    )

# --------------------------------------------------
# Build map layers
# --------------------------------------------------

layers = []

# Incident cluster circles
if not cluster_df.empty:
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            id="incident-clusters",
            data=cluster_df,
            get_position="[longitude, latitude]",
            get_fill_color="marker_color",
            get_radius="marker_radius",
            radius_min_pixels=12,
            radius_max_pixels=28,
            get_line_color=[255, 255, 255, 240],
            line_width_min_pixels=2,
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
        )
    )

    # Show the number of incidents in each cluster.
    layers.append(
        pdk.Layer(
            "TextLayer",
            id="incident-cluster-counts",
            data=cluster_df,
            get_position="[longitude, latitude]",
            get_text="incident_count",
            get_size=16,
            size_units="pixels",
            get_color=[255, 255, 255, 255],
            get_angle=0,
            get_pixel_offset=[0, 0],
            pickable=False,
        )
    )

# Simulated squad cars / fleet units
if not map_resources.empty:
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            id="simulated-fleet",
            data=map_resources,
            get_position="[longitude, latitude]",
            get_fill_color=[14, 165, 233, 240],
            get_radius=200,
            radius_min_pixels=7,
            radius_max_pixels=18,
            get_line_color=[255, 255, 255, 240],
            line_width_min_pixels=2,
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
        )
    )

# Both layers use the same tooltip field names, but their
# row data provides different incident or vehicle details.
tooltip = {
    "html": (
        "<b>{map_title}</b>"
        "<br/>{map_line_1}"
        "<br/>{map_line_2}"
        "<br/>{map_line_3}"
    ),
    "style": {
        "backgroundColor": "#111827",
        "color": "white",
        "fontSize": "12px",
        "padding": "10px",
    },
}

# --------------------------------------------------
# Render map
# --------------------------------------------------

if layers:
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=24.486,
            longitude=54.375,
            zoom=11.5,
            pitch=0,
            bearing=0,
        ),
        map_style=(
            "https://basemaps.cartocdn.com/gl/"
            "positron-gl-style/style.json"
        ),
        tooltip=tooltip,
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
        height=600,
    )
else:
    st.info(
        "No incidents or simulated vehicles with valid coordinates."
    )

# --------------------------------------------------
# Map legend and counts
# --------------------------------------------------

legend_col1, legend_col2 = st.columns(2)

with legend_col1:
    st.markdown(
        "**Incident priority**  \n"
        "🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Low  \n"
        "⚪ Grey · Resolved-only cluster"
    )

with legend_col2:
    st.markdown(
        "**Fleet**  \n"
        "🔵 Blue markers · Simulated response vehicles"
    )

active_count = (
    int((map_incidents["status"] != "resolved").sum())
    if not map_incidents.empty
    else 0
)

resolved_count_on_map = (
    int((map_incidents["status"] == "resolved").sum())
    if not map_incidents.empty
    else 0
)

st.caption(
    f"Incidents displayed: {len(map_incidents)} "
    f"({active_count} active, {resolved_count_on_map} resolved) · "
    f"Incident clusters: {len(cluster_df)} · "
    f"Simulated fleet units displayed: {len(map_resources)}"
)

st.divider()

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
            location_options = [
                location["location_label"]
                for location in LOCATIONS
            ]

            if not location_options:
                st.error(
                    "No locations are configured. "
                    "Please initialise the database."
                )
                location_label = None
            else:
                location_label = st.selectbox(
                    "Incident location",
                    options=location_options,
                    format_func=lambda label: (
                        f"{label} — "
                        + next(
                            (
                                location["area"]
                                for location in LOCATIONS
                                if location["location_label"] == label
                            ),
                            "Abu Dhabi",
                        )
                    ),
                )


        submitted = st.form_submit_button(
            "Create incident",
            type="primary",
        )


        if submitted:
            if (
                not title.strip()
                or not description.strip()
                or not location_label
            ):
                st.error(
                    "Please enter both a title and a description, "
                    "and select a location."
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
            SELECT incident_id, title, status, priority, created_at
            FROM incidents
            ORDER BY
                CASE LOWER(priority)
                    WHEN 'critical' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END,
                created_at ASC,
                incident_id ASC
            """
        ).fetchall()

    if not status_options:
        st.info("Create an incident before updating its status.")
    else:
        incident_lookup = {
            f"#{row['incident_id']} — "
            f"{row['title']} [{row['priority'].upper()} | "
            f"{row['status']}]": row["incident_id"]
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
            SELECT incident_id, title, status, priority, created_at
            FROM incidents
            WHERE status NOT IN ('resolved', 'cancelled')
            ORDER BY
                CASE LOWER(priority)
                    WHEN 'critical' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END,
                created_at ASC,
                incident_id ASC
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
            f"[{row['priority'].upper()} | {row['status']}]":
                row["incident_id"]
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
                    assign_incident_resource(
                        incident_lookup[selected_incident],
                        resource_lookup[selected_resource],
                    )

                    st.success(
                        f"Resource assigned to {selected_incident}."
                    )
                    st.rerun()

                except ValueError as error:
                    st.error(
                        f"Could not assign resource: {error}"
                    )
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
        (handover_df["priority"].str.lower() == "critical").sum()
    )

    high_count = int(
        (handover_df["priority"].str.lower() == "high").sum()
    )

    in_progress_count = int(
        (handover_df["status"].str.lower() == "in_progress").sum()
    )

    unassigned_count = int(
        handover_df["assigned_resource"].isna().sum()
    )

    unassigned_high_count = int(
        (
            (handover_df["priority"].str.lower() == "high")
            & handover_df["assigned_resource"].isna()
        ).sum()
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

    if critical_count > 0:
        st.error(
            f"URGENT: {critical_count} unresolved critical "
            "incident(s) require attention."
        )

    if unassigned_high_count > 0:
        st.warning(
            f"Action required: {unassigned_high_count} "
            "unassigned high-priority incident(s)."
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
            "assigned_resource": "Assigned resource",
        }
    )

    csv_data = report_df.to_csv(index=False).encode("utf-8")

    st.dataframe(
        report_df,
        use_container_width=True,
        hide_index=True,
    )

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
