import threading
import time
import urllib.request
from django.apps import AppConfig
from django.conf import settings

def start_pinger():
    # Target the production Render URL
    # On local development (running with runserver), this might fail or ping the local app
    # but the primary goal is keeping the Render instance alive.
    keep_alive_url = "https://pro-bank-p1eb.onrender.com/dashboard/health/"
    
    def ping():
        # Delay initial ping to let the server start
        time.sleep(10)
        while True:
            try:
                # Set a reasonable timeout for the ping
                with urllib.request.urlopen(keep_alive_url, timeout=10) as response:
                    if response.getcode() == 200:
                        pass # Ping successful
            except Exception:
                # Silently fail on network issues or local environment
                pass
            time.sleep(240)  # Ping every 4 minutes (well within the 5m limit)
            
    thread = threading.Thread(target=ping, daemon=True)
    thread.start()

class DashboardConfig(AppConfig):
    name = 'dashboard'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # Only start the pinger once
        # In development, RUN_MAIN check prevents the pinger from starting twice
        # In production, this ensures the pinger starts when the app is ready.
        import os
        if os.environ.get('RUN_MAIN') == 'true' or not settings.DEBUG:
            start_pinger()
