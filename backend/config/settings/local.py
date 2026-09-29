from .base import *  # noqa: F401,F403
from .base import env_bool, env_list

DEBUG = env_bool("DEBUG", default=True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
