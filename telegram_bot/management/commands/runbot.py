from django.core.management.base import BaseCommand
from django.conf import settings
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, PreCheckoutQueryHandler, filters
from telegram_bot.handlers import start, handle_message, handle_callback, precheckout_callback, successful_payment


class Command(BaseCommand):
    help = "Run bot in polling mode (for local development)"

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stdout.write(self.style.ERROR("TELEGRAM_BOT_TOKEN not set"))
            return

        self.stdout.write(self.style.SUCCESS("Starting bot in polling mode..."))

        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
        app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

        app.run_polling(allowed_updates=["message", "callback_query", "pre_checkout_query", "successful_payment"])