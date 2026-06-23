import json
import re
from google import genai
from google.genai import types


class GeminiService:
    MODEL_NAME = "gemini-2.5-flash"

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def analyze_intent(self, message: str) -> dict:
        prompt = f"""You are a message classifier for Booqly AI, a shopping assistant.

Analyze this user message and classify it into exactly ONE category:
- "shopping" — user wants to find, compare, or buy a product
- "product_question" — user asks about a product category but hasn't said they want to buy
- "greeting" — hello, hi, hey, good morning
- "small_talk" — casual chat, jokes, "how are you"
- "general_question" — factual questions NOT about shopping
- "goodbye" — bye, see you, thanks I'm done
- "help" — user asks what the bot can do
- "ambiguous" — vague, unclear, or nonsensical

User message: "{message}"

Return ONLY this JSON (no markdown, no explanation):
{{"intent_type": "...", "confidence": 0.0 to 1.0, "product_type": "product name if shopping/product_question, else null", "attributes": {{}}}}

Rules:
- If the user says "I want [product]", "I need [product]", "buy [product]", "get [product]" -> "shopping", confidence >= 0.85
- If clearly about buying/finding a product -> "shopping", confidence >= 0.7
- If asking about products but not buying -> "product_question", confidence 0.6-0.8
- Greetings -> "greeting", confidence 0.95+
- Random words -> "ambiguous", confidence 0.2-0.4
- General knowledge -> "general_question", confidence 0.7+
"""
        return self._call_json(prompt)

    def analyze_intent_with_context(self, message: str, previous_intent: dict) -> dict:
        prompt = f"""The user previously gave an ambiguous message. Context:

Previous intent: {json.dumps(previous_intent)}
User's follow-up: "{message}"

Re-classify using the same rules and JSON format.
"""
        return self._call_json(prompt)

    def generate_response(self, intent_type: str, user_message: str,
                          product_type: str = None, products: list = None) -> str:
        ctx = []
        if product_type:
            ctx.append(f"Product context: user is interested in '{product_type}'")
        if products:
            ctx.append(f"Available products: {json.dumps(products[:3])}")
        extra = "\n".join(ctx) if ctx else "No product context."

        prompt = f"""You are Booqly AI, a professional shopping assistant inside Telegram.

Your tone:
- Professional and helpful
- Concise — 1-2 sentences max
- No emojis unless the user uses them first
- No jokes, no excessive friendliness
- Get straight to the point
- If off-topic, briefly redirect: "I'm Booqly AI, your shopping assistant. I can help you find and buy products."

User just said: "{user_message}"
Detected intent: {intent_type}
{extra}

Write a concise, professional response (1-2 sentences max).

Examples:
- Greeting: "Hi, I'm Booqly AI. What product can I help you find?"
- Off-topic: "I'm focused on helping you shop. Want me to find something for you?"
- Vague: "Could you clarify what you're looking for?"
- Shopping: "Got it. What type of laptop are you after — gaming, business, or budget?"
- Product question: "Top gaming laptops feature RTX 50-series GPUs and high-refresh displays. Want me to show options?"
- Goodbye: "Thanks for chatting. Come back anytime you need something."
- Help: "I'm Booqly AI. I help you find products, compare options, and buy directly in Telegram. What do you need?"

Now write YOUR response:
"""
        return self._call_text(prompt)

    def generate_product_summary(self, products: list, user_query: str) -> str:
        prompt = f"""You are Booqly AI. The user asked: "{user_query}"

Products found:
{json.dumps(products, indent=2)}

Write a brief, professional summary (1-2 sentences) introducing these products. No emojis. Be concise.
Example: "Here are the top options for your search. Each product includes a buy button if you want to purchase."
"""
        return self._call_text(prompt)

    def generate_order_confirmation(self, order_data: dict) -> str:
        prompt = f"""You are Booqly AI. A user just completed a purchase.

Order: {json.dumps(order_data)}

Write a brief, professional confirmation message (1-2 sentences). No emojis.
Example: "Your order has been confirmed. Thank you for shopping with Booqly AI."
"""
        return self._call_text(prompt)

    def generate_clarification_question(self, user_message: str) -> str:
        prompt = f"""You are Booqly AI. The user said something vague: "{user_message}"

Write a brief, professional follow-up question. No emojis. 1 sentence max.
Examples:
- "Could you tell me what product you're looking for?"
- "Are you here to shop, or do you have a question I can help with?"
"""
        return self._call_text(prompt)

    def generate_product_followup(self, product_name: str, request_type: str) -> str:
        prompt = f"""You are Booqly AI. A user is asking about a product they previously viewed.

Product: {product_name}
Request type: {request_type} (reviews, description, more images, cheaper alternative, etc.)

Write a brief, helpful response (1-2 sentences). No emojis. Be factual and concise.
Examples:
- reviews: "This product has a 4.7/5 rating based on 1,200+ reviews. Customers praise the build quality and battery life."
- description: "This product features a high-resolution display, all-day battery, and premium build materials. Full specs are available on the product page."
- more_images: "Here is another view of the product."
- cheaper: "Let me find a more affordable alternative for you."
"""
        return self._call_text(prompt)

    def _call_json(self, prompt: str) -> dict:
        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
            return json.loads(text)
        except Exception as e:
            print(f"Gemini JSON error: {e}")
            return {"intent_type": "ambiguous", "confidence": 0.3, "product_type": None, "attributes": {}}

    def _call_text(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
            )
            return response.text.strip().strip('"')
        except Exception as e:
            print(f"Gemini text error: {e}")
            return "I'm Booqly AI. How can I help you shop today?"