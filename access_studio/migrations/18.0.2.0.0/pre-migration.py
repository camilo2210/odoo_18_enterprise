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


def _deduplicate_user_group_names(cr):
    # Ensure names are unique before a unique(name) constraint is enforced
    # Strategy: append the record id for any duplicated name
    cr.execute(
        """
        WITH d AS (
            SELECT name
            FROM user_group
            WHERE name IS NOT NULL AND name != ''
            GROUP BY name
            HAVING COUNT(*) > 1
        )
        UPDATE user_group ug
        SET name = ug.name || ' (' || ug.id || ')'
        FROM d
        WHERE ug.name = d.name
        """
    )


def migrate(cr, version):
    # access.studio table
    _rename_column_if_exists(cr, 'access_studio', 'access_by_user_group', 'apply_by_user_groups')
    _rename_column_if_exists(cr, 'access_studio', 'apply_without_company', 'apply_without_companies')
    _rename_column_if_exists(cr, 'access_studio', 'hide_delete', 'hide_unlink')
    _rename_column_if_exists(cr, 'access_studio', 'hide_delete_in_favorites', 'hide_unlink_in_favorites')

    # model.access table
    _rename_column_if_exists(cr, 'model_access', 'hide_delete', 'hide_unlink')
    # hide_read is new in 18.0.2.0.0 and will be created by ORM during upgrade

    # search.panel.access table
    _rename_column_if_exists(cr, 'search_panel_access', 'hide_delete_in_favorites', 'hide_unlink_in_favorites')

    # Prepare for unique(name) on user_group
    _deduplicate_user_group_names(cr)


