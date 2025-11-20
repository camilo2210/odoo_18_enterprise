from typing import Optional


def _column_exists(cr, table: str, column: str) -> bool:
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cr.fetchone() is not None


def _rename_column_if_exists(cr, table: str, old: str, new: str) -> Optional[bool]:
    if _column_exists(cr, table, new):
        return False
    if not _column_exists(cr, table, old):
        return False
    cr.execute(f'ALTER TABLE "{table}" RENAME COLUMN "{old}" TO "{new}"')
    return True


def migrate(cr, version):
    # domain.access table - rename perm_* fields to restrict_*
    _rename_column_if_exists(cr, 'domain_access', 'perm_read', 'restrict_read')
    _rename_column_if_exists(cr, 'domain_access', 'perm_write', 'restrict_write')
    _rename_column_if_exists(cr, 'domain_access', 'perm_create', 'restrict_create')
    _rename_column_if_exists(cr, 'domain_access', 'perm_unlink', 'restrict_unlink')
