from decimal import Decimal


class PaymentService:
    @staticmethod
    def parse_price_to_cents(price_str: str) -> int:
        try:
            return int(Decimal(price_str.replace("$", "").replace(",", "").replace("USD", "").strip()) * 100)
        except Exception:
            return 100

    @staticmethod
    def format_price_for_display(cents: int) -> str:
        return f"${cents / 100:.2f}"