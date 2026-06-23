from django.core.management.base import BaseCommand
from django.conf import settings
import requests


class Command(BaseCommand):
    help = "Set Telegram webhook URL"

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stdout.write(self.style.ERROR("TELEGRAM_BOT_TOKEN not set"))
            return

        webhook_url = f"{settings.WEBHOOK_BASE_URL}/telegram/webhook/"
        api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"

        self.stdout.write(f"Setting webhook to: {webhook_url}")

        response = requests.post(api_url, json={
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query", "pre_checkout_query", "successful_payment"],
        })

        data = response.json()
        if data.get("ok"):
            self.stdout.write(self.style.SUCCESS(f"Webhook set: {data}"))
        else:
            self.stdout.write(self.style.ERROR(f"Failed: {data}"))