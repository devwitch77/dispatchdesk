
import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).parent / "data" / "dispatchdesk.db"

PRIORITY_ORDER_SQL = """
    CASE incidents.priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
        ELSE 5
    END
"""


# These are approximate area reference points, not exact incident addresses.
# Response-unit coordinates are simulated and do not represent real vehicles.
ABU_DHABI_LOCATIONS = [
    {
        "location_label": "Abu Dhabi Corniche",
        "area": "Corniche",
        "latitude": 24.473493,
        "longitude": 54.340563,
    },
    {
        "location_label": "Al Hisn",
        "area": "Central Abu Dhabi",
        "latitude": 24.47987,
        "longitude": 54.3532,
    },
    {
        "location_label": "Al Reem Island",
        "area": "Al Reem Island",
        "latitude": 24.4941,
        "longitude": 54.4079,
    },

    
    {
        "location_label": "Al Khalidiyah",
        "area": "Al Khalidiyah",
        "latitude": 24.4695,
        "longitude": 54.3548,
    },
    {
        "location_label": "Al Zahiyah",
        "area": "Al Zahiyah",
        "latitude": 24.5005,
        "longitude": 54.3725,
    },

]


# Fictional demonstration units. Their positions are illustrative.
SIMULATED_UNITS = [
    {
        "unit_code": "AD-PATROL-01",
        "resource_type": "Patrol Vehicle",
        "latitude": 24.4790,
        "longitude": 54.3510,
    },
    {
        "unit_code": "AD-PATROL-02",
        "resource_type": "Patrol Vehicle",
        "latitude": 24.4920,
        "longitude": 54.4050,
    },
    {
        "unit_code": "AD-TRAFFIC-01",
        "resource_type": "Traffic Response Vehicle",
        "latitude": 24.4720,
        "longitude": 54.3420,
    },
    {
        "unit_code": "AD-SUPPORT-01",
        "resource_type": "Support Vehicle",
        "latitude": 24.4850,
        "longitude": 54.3750,
    },
]


def get_connection():
    """Open a connection to the DispatchDesk SQLite database."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=10,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _ensure_column(connection, table_name, column_name, definition):
    """Add a column to an existing table when it is missing."""
    existing_columns = {
        row["name"]
        for row in connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }

    if column_name not in existing_columns:
        connection.execute(
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN {column_name} {definition}"
        )


def initialise_database():
    """
    Create tables, safely add new columns, and seed demo data.

    Existing incidents and resources are preserved.
    """
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS resources (
                resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL UNIQUE,
                resource_type TEXT NOT NULL,
                availability_status TEXT NOT NULL DEFAULT 'available'
                    CHECK (
                        availability_status IN (
                            'available',
                            'assigned',
                            'unavailable'
                        )
                    )
            );

            CREATE TABLE IF NOT EXISTS incidents (
                incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL
                    CHECK (
                        priority IN ('low', 'medium', 'high', 'critical')
                    ),
                location_label TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new'
                    CHECK (
                        status IN (
                            'new',
                            'assigned',
                            'in_progress',
                            'resolved',
                            'cancelled'
                        )
                    ),
                assigned_resource_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT,
                FOREIGN KEY (assigned_resource_id)
                    REFERENCES resources(resource_id)
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                actor_label TEXT NOT NULL DEFAULT 'Demo Operator',
                event_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (incident_id)
                    REFERENCES incidents(incident_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS locations (
                location_id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_label TEXT NOT NULL UNIQUE,
                area TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_incidents_status
                ON incidents(status);

            CREATE INDEX IF NOT EXISTS idx_incidents_priority
                ON incidents(priority);

            CREATE INDEX IF NOT EXISTS idx_audit_incident
                ON audit_events(incident_id, event_at);
            """
        )

        # Migrate existing databases without deleting their data.
        _ensure_column(
            connection,
            "incidents",
            "latitude",
            "REAL",
        )
        _ensure_column(
            connection,
            "incidents",
            "longitude",
            "REAL",
        )
        _ensure_column(
            connection,
            "resources",
            "latitude",
            "REAL",
        )
        _ensure_column(
            connection,
            "resources",
            "longitude",
            "REAL",
        )
        _ensure_column(
            connection,
            "resources",
            "unit_code",
            "TEXT",
        )

        # Existing resources receive a stable code based on their name.
        connection.execute(
            """
            UPDATE resources
            SET unit_code = display_name
            WHERE unit_code IS NULL OR TRIM(unit_code) = ''
            """
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_resources_unit_code
            ON resources(unit_code)
            WHERE unit_code IS NOT NULL
            """
        )

        # Add or refresh the curated location reference points.
        for location in ABU_DHABI_LOCATIONS:
            connection.execute(
                """
                INSERT INTO locations (
                    location_label,
                    area,
                    latitude,
                    longitude
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(location_label) DO UPDATE SET
                    area = excluded.area,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude
                """,
                (
                    location["location_label"],
                    location["area"],
                    location["latitude"],
                    location["longitude"],
                ),
            )


        # Migrate legacy demonstration fleet units in place.
        # Resource IDs, availability, and incident assignments are preserved.
        legacy_units = [
            {
                "old_name": "Team Alpha",
                "new_code": "AD-RESPONSE-01",
                "resource_type": "Response Vehicle",
                "latitude": 24.4678,
                "longitude": 54.3560,
            },
            {
                "old_name": "Team Bravo",
                "new_code": "AD-RESPONSE-02",
                "resource_type": "Response Vehicle",
                "latitude": 24.5000,
                "longitude": 54.3750,
            },
            {
                "old_name": "Support Unit 1",
                "new_code": "AD-SUPPORT-02",
                "resource_type": "Support Vehicle",
                "latitude": 24.4770,
                "longitude": 54.3600,
            },
            {
                "old_name": "Support Unit 2",
                "new_code": "AD-SUPPORT-03",
                "resource_type": "Support Vehicle",
                "latitude": 24.4890,
                "longitude": 54.3900,
            },
        ]

        for unit in legacy_units:
            connection.execute(
                """
                UPDATE resources
                SET display_name = ?,
                    unit_code = ?,
                    resource_type = ?,
                    latitude = ?,
                    longitude = ?
                WHERE display_name = ?
                """,
                (
                    unit["new_code"],
                    unit["new_code"],
                    unit["resource_type"],
                    unit["latitude"],
                    unit["longitude"],
                    unit["old_name"],
                ),
            )

        # Map legacy placeholder zones to curated Abu Dhabi locations.
        legacy_location_mapping = {
            "Demo Zone A": "Abu Dhabi Corniche",
            "Demo Zone B": "Al Hisn",
            "Demo Zone C": "Al Khalidiyah",
            "Demo Zone D": "Al Zahiyah",
            "Demo Zone E": "Al Reem Island",
            "Demo Zone F": "Abu Dhabi Corniche",
        }

        for old_label, new_label in legacy_location_mapping.items():
            connection.execute(
                """
                UPDATE incidents
                SET location_label = ?,
                    latitude = (
                        SELECT latitude
                        FROM locations
                        WHERE location_label = ?
                    ),
                    longitude = (
                        SELECT longitude
                        FROM locations
                        WHERE location_label = ?
                    )
                WHERE location_label = ?
                """,
                (
                    new_label,
                    new_label,
                    new_label,
                    old_label,
                ),
            )


        # Add the fictional units only when their unit codes are new.
        for unit in SIMULATED_UNITS:
            connection.execute(
                """
                INSERT OR IGNORE INTO resources (
                    display_name,
                    resource_type,
                    availability_status,
                    latitude,
                    longitude,
                    unit_code
                )
                VALUES (?, ?, 'available', ?, ?, ?)
                """,
                (
                    unit["unit_code"],
                    unit["resource_type"],
                    unit["latitude"],
                    unit["longitude"],
                    unit["unit_code"],
                ),
            )


def get_locations():
    """Return locations suitable for an incident-location selector."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                location_id,
                location_label,
                area,
                latitude,
                longitude
            FROM locations
            ORDER BY area, location_label
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_resources():
    """Return fleet units and their current simulated positions."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                resource_id,
                unit_code,
                display_name,
                resource_type,
                availability_status,
                latitude,
                longitude
            FROM resources
            ORDER BY unit_code
            """
        ).fetchall()

    return [dict(row) for row in rows]


def create_incident(
    title,
    description,
    category,
    priority,
    location_label,
):
    """Create an incident and store coordinates when its location is known."""
    with get_connection() as connection:
        location = connection.execute(
            """
            SELECT latitude, longitude
            FROM locations
            WHERE location_label = ?
            """,
            (location_label.strip(),),
        ).fetchone()

        latitude = location["latitude"] if location else None
        longitude = location["longitude"] if location else None

        cursor = connection.execute(
            """
            INSERT INTO incidents (
                title,
                description,
                category,
                priority,
                location_label,
                latitude,
                longitude
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title.strip(),
                description.strip(),
                category,
                priority,
                location_label.strip(),
                latitude,
                longitude,
            ),
        )

        incident_id = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO audit_events (
                incident_id,
                event_type,
                old_value,
                new_value
            )
            VALUES (?, 'incident_created', NULL, ?)
            """,
            (incident_id, title.strip()),
        )

        return incident_id


def update_incident_status(incident_id, new_status):
    """Update incident status, log the change, and release closed resources."""
    allowed_statuses = {
        "new",
        "in_progress",
        "resolved",
        "cancelled",
    }

    if new_status not in allowed_statuses:
        raise ValueError("Invalid incident status.")

    with get_connection() as connection:
        incident = connection.execute(
            """
            SELECT status, assigned_resource_id
            FROM incidents
            WHERE incident_id = ?
            """,
            (incident_id,),
        ).fetchone()

        if incident is None:
            raise ValueError("Incident not found.")

        old_status = incident["status"]

        if old_status == new_status:
            return False

        connection.execute(
            """
            UPDATE incidents
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP,
                resolved_at = CASE
                    WHEN ? = 'resolved' THEN CURRENT_TIMESTAMP
                    ELSE NULL
                END
            WHERE incident_id = ?
            """,
            (new_status, new_status, incident_id),
        )

        connection.execute(
            """
            INSERT INTO audit_events (
                incident_id,
                event_type,
                old_value,
                new_value
            )
            VALUES (?, 'status_changed', ?, ?)
            """,
            (incident_id, old_status, new_status),
        )

        # Release the unit when its incident is closed, provided no other
        # active incident is using that unit.
        if new_status in {"resolved", "cancelled"}:
            resource_id = incident["assigned_resource_id"]

            if resource_id is not None:
                other_active_incidents = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM incidents
                    WHERE assigned_resource_id = ?
                      AND incident_id != ?
                      AND status NOT IN ('resolved', 'cancelled')
                    """,
                    (resource_id, incident_id),
                ).fetchone()[0]

                if other_active_incidents == 0:
                    connection.execute(
                        """
                        UPDATE resources
                        SET availability_status = 'available'
                        WHERE resource_id = ?
                        """,
                        (resource_id,),
                    )

    return True


def assign_incident_resource(incident_id, resource_id):
    """Assign an available unit and record the assignment in the audit log."""
    with get_connection() as connection:
        # Lock the SQLite write transaction before checking availability.
        # This helps avoid two concurrent operations assigning one unit twice.
        connection.execute("BEGIN IMMEDIATE")

        incident = connection.execute(
            """
            SELECT incident_id, status, assigned_resource_id
            FROM incidents
            WHERE incident_id = ?
            """,
            (incident_id,),
        ).fetchone()

        if incident is None:
            raise ValueError("Incident not found.")

        resource = connection.execute(
            """
            SELECT
                resource_id,
                display_name,
                availability_status
            FROM resources
            WHERE resource_id = ?
            """,
            (resource_id,),
        ).fetchone()

        if resource is None:
            raise ValueError("Resource not found.")

        if incident["status"] in ("resolved", "cancelled"):
            raise ValueError(
                "Cannot assign a resource to a closed incident."
            )

        old_resource_id = incident["assigned_resource_id"]

        if old_resource_id == resource_id:
            return False

        if resource["availability_status"] != "available":
            raise ValueError(
                "This resource is not available. Choose another resource."
            )

        old_resource = None

        if old_resource_id is not None:
            old_resource = connection.execute(
                """
                SELECT display_name
                FROM resources
                WHERE resource_id = ?
                """,
                (old_resource_id,),
            ).fetchone()

        old_resource_name = (
            old_resource["display_name"]
            if old_resource
            else "Unassigned"
        )

        old_status = incident["status"]
        new_status = (
            "assigned" if old_status == "new" else old_status
        )

        connection.execute(
            """
            UPDATE incidents
            SET assigned_resource_id = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE incident_id = ?
            """,
            (resource_id, new_status, incident_id),
        )

        connection.execute(
            """
            UPDATE resources
            SET availability_status = 'assigned'
            WHERE resource_id = ?
            """,
            (resource_id,),
        )

        # Release the previous unit if no other active incident uses it.
        if old_resource_id is not None:
            other_assignments = connection.execute(
                """
                SELECT COUNT(*)
                FROM incidents
                WHERE assigned_resource_id = ?
                  AND incident_id != ?
                  AND status NOT IN ('resolved', 'cancelled')
                """,
                (old_resource_id, incident_id),
            ).fetchone()[0]

            if other_assignments == 0:
                connection.execute(
                    """
                    UPDATE resources
                    SET availability_status = 'available'
                    WHERE resource_id = ?
                    """,
                    (old_resource_id,),
                )

        connection.execute(
            """
            INSERT INTO audit_events (
                incident_id,
                event_type,
                old_value,
                new_value
            )
            VALUES (?, 'resource_assigned', ?, ?)
            """,
            (
                incident_id,
                old_resource_name,
                resource["display_name"],
            ),
        )

        if old_status != new_status:
            connection.execute(
                """
                INSERT INTO audit_events (
                    incident_id,
                    event_type,
                    old_value,
                    new_value
                )
                VALUES (?, 'status_changed', ?, ?)
                """,
                (incident_id, old_status, new_status),
            )

    return True


def get_handover_incidents():
    """Return unresolved incidents, ordered by criticality then age."""
    with get_connection() as connection:
        incidents = connection.execute(
            f"""
            SELECT
                incidents.incident_id,
                incidents.title,
                incidents.description,
                incidents.category,
                incidents.priority,
                incidents.location_label,
                incidents.latitude,
                incidents.longitude,
                incidents.status,
                incidents.created_at,
                incidents.updated_at,
                resources.display_name AS assigned_resource
            FROM incidents
            LEFT JOIN resources
                ON incidents.assigned_resource_id =
                   resources.resource_id
            WHERE incidents.status IN (
                'new',
                'assigned',
                'in_progress'
            )
            ORDER BY
                {PRIORITY_ORDER_SQL},
                incidents.created_at ASC,
                incidents.incident_id ASC
            """
        ).fetchall()

    return [dict(incident) for incident in incidents]


if __name__ == "__main__":
    initialise_database()

    print(f"Database initialised at: {DATABASE_PATH}")
    print(f"Locations available: {len(get_locations())}")
    print(f"Simulated fleet units: {len(get_resources())}")
