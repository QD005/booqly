import os
import json
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# -----------------------------
# AI FUNCTION (REPLACE WITH YOUR MODEL)
# -----------------------------
def ai_chatbot_response(user_message):
    """
    Replace this with your custom AI logic
    """
    # Example simple logic
    return f"You said: {user_message}"

# -----------------------------
# SEND MESSAGE TO WHATSAPP
# -----------------------------
def send_whatsapp_message(to, message):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": message
        }
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()

# -----------------------------
# WEBHOOK VERIFICATION (GET)
# -----------------------------
@csrf_exempt
def webhook(request):
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return HttpResponse(challenge)
        else:
            return HttpResponse("Verification failed", status=403)

    elif request.method == "POST":
        try:
            body = json.loads(request.body)

            # Extract message
            entry = body.get("entry", [])
            if entry:
                changes = entry[0].get("changes", [])
                if changes:
                    value = changes[0].get("value", {})
                    messages = value.get("messages")

                    if messages:
                        message = messages[0]
                        from_number = message["from"]

                        # Handle text message
                        if message["type"] == "text":
                            user_text = message["text"]["body"]

                            # Get AI response
                            bot_reply = ai_chatbot_response(user_text)

                            # Send reply
                            send_whatsapp_message(from_number, bot_reply)

        except Exception as e:
            print("Error:", str(e))

        return JsonResponse({"status": "ok"})