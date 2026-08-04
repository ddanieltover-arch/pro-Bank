from django.apps import AppConfig
from django.conf import settings


class DashboardConfig(AppConfig):
    name = 'dashboard'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # Render keep-alive pinger removed — this project deploys on Vercel
        # (serverless), where a long-lived ping thread is unnecessary and harmful.
        pass
