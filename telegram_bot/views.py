import json
import asyncio
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, PreCheckoutQueryHandler, filters,
)
from .handlers import (
    start, handle_message, handle_callback,
    precheckout_callback, successful_payment,
)


def _build_app():
    """Build a fresh Application instance."""
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    return app


async def _process_update(data: dict):
    """Process a single Telegram update in an isolated async context."""
    app = _build_app()
    await app.initialize()
    try:
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
    finally:
        await app.shutdown()


@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

        # Each request gets its own event loop + Application
        # This prevents "Event loop is closed" across Gunicorn workers
        asyncio.run(_process_update(data))

        return JsonResponse({"status": "ok"})