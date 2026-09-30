from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    label = "common"

    def ready(self):
        # SQLite has no MySQL collations; models/migrations name utf8mb4_bin (case-sensitive compare).
        from django.db.backends.signals import connection_created

        def register_collation(sender, connection, **kwargs):
            if connection.vendor == "sqlite":
                connection.connection.create_collation("utf8mb4_bin", lambda a, b: (a > b) - (a < b))

        connection_created.connect(register_collation, weak=False)
