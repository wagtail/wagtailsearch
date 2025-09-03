from django.apps import AppConfig


class WagtailSearchTestAppConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    label = "searchtests"
    name = "wagtailsearch.test"
    verbose_name = "Wagtail Search tests"
