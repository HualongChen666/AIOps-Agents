# -*- coding: utf-8 -*-
"""P0 #3 SQL injection defense: identifier whitelist validator.

Used to validate user-supplied table/column identifiers before they are
interpolated into SQL strings. Rejects anything that is not a valid
PostgreSQL / ClickHouse identifier (letters, digits, underscores;
must start with letter or underscore; max 63 chars).
"""

import re

_PG_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")

# Reserved schemas that must never be referenced as data tables.
_RESERVED_SCHEMAS = frozenset({"pg_catalog", "information_schema", "pg_toast"})

# ClickHouse reserved database names.
_CLICKHOUSE_RESERVED_DBS = frozenset(
    {"system", "information_schema", "default", "_temporary_and_external_tables"}
)


def validate_pg_identifier(identifier: str, *, kind: str = "table") -> str:
    """Validate and return a safe PostgreSQL identifier.

    Args:
        identifier: candidate table / column / schema name.
        kind: informational label for error messages ("table", "schema", ...)

    Returns:
        The same identifier, validated.

    Raises:
        ValueError: if the identifier contains anything other than
            letters, digits, and underscores, or is empty, or matches
            a reserved schema name.
    """
    if not isinstance(identifier, str) or not identifier:
        raise ValueError(f"{kind} identifier must be a non-empty string")
    if not _PG_IDENT_RE.match(identifier):
        raise ValueError(
            f"invalid {kind} identifier {identifier!r}: "
            "must match [A-Za-z_][A-Za-z0-9_]* with max 63 chars"
        )
    if identifier.lower() in _RESERVED_SCHEMAS:
        raise ValueError(
            f"refusing to reference reserved {kind} {identifier!r}"
        )
    return identifier


def validate_clickhouse_identifier(identifier: str, *, kind: str = "table") -> str:
    """Validate and return a safe ClickHouse identifier (database or table)."""
    if not isinstance(identifier, str) or not identifier:
        raise ValueError(f"{kind} identifier must be a non-empty string")
    if not _PG_IDENT_RE.match(identifier):
        raise ValueError(
            f"invalid {kind} identifier {identifier!r}: "
            "must match [A-Za-z_][A-Za-z0-9_]* with max 63 chars"
        )
    if identifier.lower() in _CLICKHOUSE_RESERVED_DBS:
        raise ValueError(
            f"refusing to reference reserved ClickHouse {kind} {identifier!r}"
        )
    return identifier


__all__ = [
    "validate_pg_identifier",
    "validate_clickhouse_identifier",
]