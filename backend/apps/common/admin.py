class NoDeleteAdminMixin:
    """Nothing is deleted in this release (history rows are PROTECTed); hide delete in admin."""

    def has_delete_permission(self, request, obj=None):
        return False
