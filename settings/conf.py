"""Environment values; operating-system variables take precedence over .env."""

from pathlib import Path

from decouple import Config, Csv, RepositoryEnv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / "settings" / ".env"
config = Config(RepositoryEnv(str(ENV_FILE)) if ENV_FILE.exists() else {})

LOCAL_ENV = "local"
PROD_ENV = "prod"
ENV_MODULES = {LOCAL_ENV: "settings.env.local", PROD_ENV: "settings.env.prod"}
BLOG_ENV_ID = config("BLOG_ENV_ID", default=LOCAL_ENV)
BLOG_SECRET_KEY = config("BLOG_SECRET_KEY")
BLOG_ALLOWED_HOSTS = config(
    "BLOG_ALLOWED_HOSTS", default="localhost,127.0.0.1,[::1]", cast=Csv()
)
BLOG_CSRF_TRUSTED_ORIGINS = config("BLOG_CSRF_TRUSTED_ORIGINS", default="", cast=Csv())


def get_settings_module() -> str:
    """Reject misspelled environments rather than silently using local settings."""
    if BLOG_ENV_ID not in ENV_MODULES:
        raise ValueError("BLOG_ENV_ID must be 'local' or 'prod'.")
    return ENV_MODULES[BLOG_ENV_ID]
