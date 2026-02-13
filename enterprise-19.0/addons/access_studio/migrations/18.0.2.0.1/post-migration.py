def migrate(cr, version):
    # Cleanup discovered view node data to align with new grouping and
    # enforcement logic. This avoids stale entries from previous versions.
    cr.execute("DELETE FROM view_node_data")


