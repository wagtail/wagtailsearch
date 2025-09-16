"""
Django settings for temp project.

For more information on this file, see
https://docs.djangoproject.com/en/stable/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/stable/ref/settings/
"""

import os

import dj_database_url


# Build paths inside the project like this: os.path.join(PROJECT_DIR, ...)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "not-a-secure-key"  # noqa: S105

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "testserver"]


# Application definition

INSTALLED_APPS = [
    "wagtailsearch",
    "wagtailsearch.test",
    "taggit",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wagtailsearch.test.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]


# Using DatabaseCache to make sure that the cache is cleared between tests.
# This prevents false-positives in some wagtail core tests where we are
# changing the 'wagtail_root_paths' key which may cause future tests to fail.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache",
    }
}


# don't use the intentionally slow default password hasher
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)


# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases

DATABASES = {
    "default": dj_database_url.config(default="sqlite:///test_wagtailsearch.db"),
}


# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# STATICFILES_DIRS = [os.path.join(PROJECT_DIR, "static")]

STATIC_ROOT = os.path.join(BASE_DIR, "test-static")
STATIC_URL = "/static/"

MEDIA_ROOT = os.path.join(BASE_DIR, "test-media")

WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtailsearch.backends.database.fallback",
    }
}

if os.environ.get("DATABASE_ENGINE") == "django.db.backends.postgresql":
    INSTALLED_APPS.append("django.contrib.postgres")
    WAGTAILSEARCH_BACKENDS["postgresql"] = {
        "BACKEND": "wagtailsearch.backends.database",
        "AUTO_UPDATE": False,
        "SEARCH_CONFIG": "english",
    }

if "ELASTICSEARCH_URL" in os.environ:
    if os.environ.get("ELASTICSEARCH_VERSION") == "8":
        backend = "wagtailsearch.backends.elasticsearch8"
    elif os.environ.get("ELASTICSEARCH_VERSION") == "7":
        backend = "wagtailsearch.backends.elasticsearch7"

    WAGTAILSEARCH_BACKENDS["elasticsearch"] = {
        "BACKEND": backend,
        "URLS": [os.environ["ELASTICSEARCH_URL"]],
        "TIMEOUT": 10,
        "max_retries": 1,
        "AUTO_UPDATE": False,
        "INDEX_SETTINGS": {"settings": {"index": {"number_of_shards": 1}}},
        "OPTIONS": {
            "ca_certs": os.environ.get("ELASTICSEARCH_CA_CERTS"),
        },
    }

if "OPENSEARCH_URL" in os.environ:
    if os.environ.get("OPENSEARCH_VERSION") == "2":
        backend = "wagtailsearch.backends.opensearch2"
    elif os.environ.get("OPENSEARCH_VERSION") == "3":
        backend = "wagtailsearch.backends.opensearch3"

    WAGTAILSEARCH_BACKENDS["opensearch"] = {
        "BACKEND": backend,
        "URLS": [os.environ["OPENSEARCH_URL"]],
        "TIMEOUT": 10,
        "max_retries": 1,
        "AUTO_UPDATE": False,
        "INDEX_SETTINGS": {"settings": {"index": {"number_of_shards": 1}}},
        "OPTIONS": {
            "ca_certs": os.environ.get("OPENSEARCH_CA_CERTS"),
        },
    }
