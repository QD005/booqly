import json
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

_bot_app = None


def get_bot():
    global _bot_app
    if _bot_app is None:
        _bot_app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).updater(None).build()
        _bot_app.add_handler(CommandHandler("start", start))
        _bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        _bot_app.add_handler(CallbackQueryHandler(handle_callback))
        _bot_app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
        _bot_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    return _bot_app


@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(View):
    async def post(self, request, *args, **kwargs):
        app = get_bot()
        if not getattr(app, "_initialized", False):
            await app.initialize()
            app._initialized = True
        try:
            data = json.loads(request.body)
            update = Update.de_json(data, app.bot)
            await app.process_update(update)
            return JsonResponse({"status": "ok"})
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)