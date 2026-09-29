"""Settings load like cnext-backend-deb: python-dotenv + MASTER_DB_* / SLAVE_DB_* aliases."""

from django.conf import settings

from config.settings.database import mysql_alias


def test_database_aliases_default_and_slave():
    assert set(settings.DATABASES) == {"default", "slave"}
    default, slave = settings.DATABASES["default"], settings.DATABASES["slave"]
    for alias in (default, slave):
        assert alias["ENGINE"] == "django.db.backends.mysql"
        assert alias["PORT"] == "3306"
        assert alias["CONN_MAX_AGE"] == 60
        assert alias["OPTIONS"] == {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    assert default["TEST"]["NAME"] == "test_counselqueue"
    assert slave["TEST"]["MIRROR"] == "default"


def test_mysql_alias_reads_prefixed_env(monkeypatch):
    monkeypatch.setenv("SLAVE_DB_NAME", "cq_read")
    monkeypatch.setenv("SLAVE_DB_USER", "reader")
    monkeypatch.setenv("SLAVE_DB_PASSWORD", "pw")
    monkeypatch.setenv("SLAVE_DB_HOST", "replica.local")
    alias = mysql_alias("SLAVE_DB", test={"MIRROR": "default"})
    assert (alias["NAME"], alias["USER"], alias["PASSWORD"], alias["HOST"]) == (
        "cq_read",
        "reader",
        "pw",
        "replica.local",
    )
    assert alias["TEST"] == {"MIRROR": "default"}


def test_mysql_alias_defaults_to_empty_strings(monkeypatch):
    for key in ("NAME", "USER", "PASSWORD", "HOST"):
        monkeypatch.delenv(f"MASTER_DB_{key}", raising=False)
    alias = mysql_alias("MASTER_DB")
    assert (alias["NAME"], alias["USER"], alias["PASSWORD"], alias["HOST"]) == ("", "", "", "")


def test_env_is_loaded_with_dotenv_not_django_environ():
    import config.settings.base as base

    assert not hasattr(base, "environ")
    assert base.load_dotenv.__module__.startswith("dotenv")


def test_no_trailing_slash_routes():
    assert settings.APPEND_SLASH is False
