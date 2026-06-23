import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.conf import settings

from .models import TelegramUser, Conversation, Product, Order
from .services.gemini_service import GeminiService
from .services.product_service import MockProductService, RainforestAPIProductService
from .services.payment_service import PaymentService

gemini = GeminiService(settings.GEMINI_API_KEY)
product_service = MockProductService() if settings.USE_MOCK_PRODUCTS else RainforestAPIProductService(settings.RAINFOREST_API_KEY)
payment_service = PaymentService()

STATE_IDLE = "idle"
STATE_AWAITING_CLARIFICATION = "awaiting_clarification"
STATE_SHOWING_RESULTS = "showing_results"

SHOPPING_KEYWORDS = ["want", "need", "buy", "get", "looking for", "show me", "find me",
                     "purchase", "order", "shop for", "recommend", "best", "cheapest", "top"]


async def persist_user(update: Update):
    u = update.effective_user
    tg_user, _ = await sync_to_async(TelegramUser.objects.get_or_create)(
        user_id=u.id, defaults={"username": u.username, "first_name": u.first_name, "last_name": u.last_name})
    return tg_user


async def persist_message(tg_user, text, direction="incoming"):
    await sync_to_async(Conversation.objects.create)(user=tg_user, message=text, direction=direction)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = STATE_IDLE
    context.user_data["pending_intent"] = None
    context.user_data["last_products"] = {}
    context.user_data["last_query"] = None
    context.user_data["message_product_map"] = {}

    welcome = (
        "Hi, I'm Booqly AI, your personal shopping assistant.\n\n"
        "I can help you:\n"
        "- Find products\n"
        "- Compare prices and features\n"
        "- Buy directly in this chat\n\n"
        "Try saying:\n"
        "- I want a double-sided refrigerator\n"
        "- What are the best wireless headphones?\n"
        "- Show me gaming laptops under $1000\n\n"
        "What can I help you find?"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = await persist_user(update)
    text = update.message.text.strip()
    await persist_message(tg_user, text, "incoming")
    state = context.user_data.get("state", STATE_IDLE)

    # Handle reply to a product message
    if update.message.reply_to_message:
        last_products = context.user_data.get("last_products", {})
        if last_products:
            await handle_product_followup(update, context, tg_user, text, last_products)
            return

    if state == STATE_AWAITING_CLARIFICATION:
        await handle_clarification(update, context, tg_user, text)
        return

    await update.message.chat.send_action(action="typing")

    try:
        analysis = gemini.analyze_intent(text)
    except Exception as e:
        print(f"Gemini intent error: {e}")
        analysis = {"intent_type": "ambiguous", "confidence": 0.3, "product_type": None, "attributes": {}}

    intent_type = analysis.get("intent_type", "ambiguous")
    confidence = analysis.get("confidence", 0.0)
    product_type = analysis.get("product_type")

    text_lower = text.lower()
    is_obvious_shopping = (
        intent_type == "shopping" and
        any(kw in text_lower for kw in SHOPPING_KEYWORDS)
    )

    if confidence < 0.45 and not is_obvious_shopping:
        question = gemini.generate_clarification_question(text)
        context.user_data["state"] = STATE_AWAITING_CLARIFICATION
        context.user_data["pending_intent"] = analysis
        await update.message.reply_text(question, parse_mode="Markdown")
        await persist_message(tg_user, question, "outgoing")
        return

    if intent_type == "greeting":
        await _send(update, tg_user, "greeting", text)
    elif intent_type == "small_talk":
        await _send(update, tg_user, "small_talk", text)
    elif intent_type == "goodbye":
        await _send(update, tg_user, "goodbye", text)
    elif intent_type == "help":
        await _send(update, tg_user, "help", text)
    elif intent_type == "general_question":
        r = gemini.generate_response("general_question", text)
        await update.message.reply_text(r, parse_mode="Markdown")
        await persist_message(tg_user, r, "outgoing")
    elif intent_type == "product_question":
        r = gemini.generate_response("product_question", text, product_type=product_type)
        await update.message.reply_text(r, parse_mode="Markdown")
        await persist_message(tg_user, r, "outgoing")
        if product_type:
            await update.message.chat.send_action(action="typing")
            await search_products(update, context, product_type, analysis, tg_user, show_buy=False)
    elif intent_type == "shopping":
        await search_products(update, context, product_type or text, analysis, tg_user, show_buy=True)
        context.user_data["state"] = STATE_SHOWING_RESULTS
    else:
        r = gemini.generate_response("ambiguous", text)
        await update.message.reply_text(r, parse_mode="Markdown")
        await persist_message(tg_user, r, "outgoing")


async def handle_clarification(update, context, tg_user, text):
    pending = context.user_data.get("pending_intent", {})
    try:
        analysis = gemini.analyze_intent_with_context(text, pending)
    except Exception as e:
        print(f"Gemini context error: {e}")
        analysis = {"intent_type": "ambiguous", "confidence": 0.4, "product_type": text, "attributes": {}}

    intent_type = analysis.get("intent_type", "ambiguous")
    confidence = analysis.get("confidence", 0.0)

    if confidence < 0.5:
        r = "I'm still not sure. Are you here to shop for something, or do you have a question?"
        kb = [
            [InlineKeyboardButton("I want to shop", callback_data="intent:shop")],
            [InlineKeyboardButton("I have a question", callback_data="intent:question")],
        ]
        await update.message.reply_text(r, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        await persist_message(tg_user, r, "outgoing")
        context.user_data["state"] = STATE_IDLE
        context.user_data["pending_intent"] = None
        return

    context.user_data["state"] = STATE_IDLE
    context.user_data["pending_intent"] = None

    if intent_type == "shopping":
        await search_products(update, context, analysis.get("product_type") or text, analysis, tg_user, show_buy=True)
        context.user_data["state"] = STATE_SHOWING_RESULTS
    elif intent_type == "product_question":
        r = gemini.generate_response("product_question", text, product_type=analysis.get("product_type"))
        await update.message.reply_text(r, parse_mode="Markdown")
        await persist_message(tg_user, r, "outgoing")
        if analysis.get("product_type"):
            await search_products(update, context, analysis["product_type"], analysis, tg_user, show_buy=False)
    else:
        r = gemini.generate_response(intent_type, text)
        await update.message.reply_text(r, parse_mode="Markdown")
        await persist_message(tg_user, r, "outgoing")


async def search_products(update, context, query, intent_data, tg_user, show_buy=True):
    msg = await update.message.reply_text(f"Searching for '{query}'...", parse_mode="Markdown")
    products = product_service.search(query, intent_data.get("attributes"))

    if not products:
        r = "Couldn't find anything matching that. Try being more specific, like 'Samsung double-door refrigerator' or 'Wireless headphones under $150'."
        await msg.edit_text(r)
        await persist_message(tg_user, r, "outgoing")
        context.user_data["state"] = STATE_IDLE
        return

    product_map = {}
    for p in products:
        await sync_to_async(Product.objects.update_or_create)(
            external_id=p["id"],
            defaults={"name": p["name"], "price": p["price"], "rating": p.get("rating"),
                      "image_url": p.get("image"), "product_url": p.get("url"), "features": json.dumps(p.get("features", []))})
        product_map[p["id"]] = p

    context.user_data["last_products"] = product_map
    context.user_data["last_query"] = query

    summary = gemini.generate_product_summary(products, query)
    await msg.edit_text(summary, parse_mode="Markdown")
    await persist_message(tg_user, summary, "outgoing")

    for i, p in enumerate(products):
        feats = "\n".join([f"- {f}" for f in p.get("features", [])[:2]])
        cap = f"*{i+1}. {p['name']}*\nPrice: `{p['price']}`\n"
        if p.get("rating"):
            cap += f"Rating: {p['rating']}/5\n"
        if feats:
            cap += f"\n{feats}\n"

        kb = []
        if show_buy:
            kb.append([InlineKeyboardButton("Select & Buy", callback_data=f"buy:{p['id']}")])
        else:
            kb.append([InlineKeyboardButton("Buy This", callback_data=f"buy:{p['id']}")])
            kb.append([InlineKeyboardButton("Ask About This", callback_data=f"ask:{p['id']}")])

        img = p.get("image")
        if img:
            try:
                sent_msg = await update.message.reply_photo(
                    photo=img, caption=cap,
                    reply_markup=InlineKeyboardMarkup(kb),
                    parse_mode="Markdown")
                context.user_data["message_product_map"][sent_msg.message_id] = p["id"]
            except Exception as e:
                print(f"Photo error: {e}")
                await update.message.reply_text(cap, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        else:
            await update.message.reply_text(cap, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def handle_product_followup(update, context, tg_user, text, last_products):
    text_lower = text.lower()

    product_id = None
    if update.message.reply_to_message:
        replied_msg_id = update.message.reply_to_message.message_id
        msg_map = context.user_data.get("message_product_map", {})
        product_id = msg_map.get(replied_msg_id)

    if not product_id and last_products:
        product_id = list(last_products.keys())[0]

    product = last_products.get(product_id, {})
    product_name = product.get("name", "this product")

    if any(w in text_lower for w in ["more image", "another image", "more photo", "other image", "another photo", "different angle"]):
        request_type = "more_images"
        response = gemini.generate_product_followup(product_name, request_type)
        img = product.get("image")
        if img:
            await update.message.reply_photo(photo=img, caption=response, parse_mode="Markdown")
        else:
            await update.message.reply_text(response, parse_mode="Markdown")

    elif any(w in text_lower for w in ["review", "rating", "what do people say", "feedback", "opinion", "good"]):
        request_type = "reviews"
        response = gemini.generate_product_followup(product_name, request_type)
        await update.message.reply_text(response, parse_mode="Markdown")

    elif any(w in text_lower for w in ["description", "spec", "detail", "feature", "what does it have", "info", "about this"]):
        request_type = "description"
        response = gemini.generate_product_followup(product_name, request_type)
        features = product.get("features", [])
        if features:
            response += "\n\nKey features:\n" + "\n".join([f"- {f}" for f in features])
        await update.message.reply_text(response, parse_mode="Markdown")

    elif any(w in text_lower for w in ["cheaper", "lower price", "discount", "under", "less expensive", "affordable", "budget"]):
        request_type = "cheaper"
        response = gemini.generate_product_followup(product_name, request_type)
        await update.message.reply_text(response, parse_mode="Markdown")
        query = context.user_data.get("last_query", product_name)
        await update.message.chat.send_action(action="typing")
        analysis = {"intent_type": "shopping", "confidence": 0.9, "product_type": query, "attributes": {}}
        await search_products(update, context, f"cheap {query}", analysis, tg_user, show_buy=True)

    else:
        response = gemini.generate_response("product_question", text, product_type=product_name)
        await update.message.reply_text(response, parse_mode="Markdown")

    await persist_message(tg_user, response, "outgoing")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data.startswith("buy:"):
        await initiate_purchase(q, context, q.data.split(":")[1])
    elif q.data.startswith("ask:"):
        await handle_product_question(q, context, q.data.split(":")[1])
    elif q.data == "intent:shop":
        r = "Great. What are you looking for? Describe it and I'll find the best options."
        await q.edit_message_text(r)
        await persist_message(await persist_user(update), r, "outgoing")
        context.user_data["state"] = STATE_IDLE
    elif q.data == "intent:question":
        r = "Sure. Ask me anything about products, recommendations, or comparisons."
        await q.edit_message_text(r)
        await persist_message(await persist_user(update), r, "outgoing")
        context.user_data["state"] = STATE_IDLE


async def handle_product_question(q, context, product_id):
    try:
        product = await sync_to_async(Product.objects.get)(external_id=product_id)
    except Product.DoesNotExist:
        await _safe_edit(q, "Product not found.")
        return
    r = f"You picked: *{product.name}*\n\nPrice: `{product.price}`\nRating: {product.rating or 'N/A'}/5\n\nWhat do you want to know? Or click buy below."
    kb = [[InlineKeyboardButton("Buy Now", callback_data=f"buy:{product_id}")]]
    await _safe_edit(q, r, reply_markup=InlineKeyboardMarkup(kb))


async def initiate_purchase(q, context, product_id):
    try:
        product = await sync_to_async(Product.objects.get)(external_id=product_id)
        user = await sync_to_async(TelegramUser.objects.get)(user_id=q.from_user.id)
    except Exception:
        await _safe_send(q, context, "Product not found. Try searching again.")
        return

    order = await sync_to_async(Order.objects.create)(user=user, product=product, status="pending")
    amount = payment_service.parse_price_to_cents(product.price)
    prices = [LabeledPrice(label=product.name[:30], amount=amount)]

    try:
        await context.bot.send_invoice(
            chat_id=q.from_user.id, title=product.name[:32],
            description=f"Order #{order.id} — {product.name[:120]}",
            payload=str(order.id), provider_token=settings.PAYMENT_PROVIDER_TOKEN,
            currency="USD", prices=prices, start_parameter=f"order_{order.id}",
            photo_url=product.image_url or "", photo_size=512, photo_width=512, photo_height=512)
        await _safe_edit(q, "Invoice sent. Check above to complete payment.")
    except Exception as e:
        print(f"Invoice error: {e}")
        await _safe_send(q, context, "Couldn't start payment. Make sure PAYMENT_PROVIDER_TOKEN is set up correctly.")


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.answer_pre_checkout_query(update.pre_checkout_query.id, ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    order_id = int(payment.invoice_payload)
    try:
        order = await sync_to_async(Order.objects.select_related("product").get)(id=order_id)
        order.status = "completed"
        order.payment_id = payment.telegram_payment_charge_id
        await sync_to_async(order.save)()
        order_data = {"order_id": order.id, "product": order.product.name,
                      "amount": f"{payment.total_amount / 100:.2f} {payment.currency}",
                      "customer": update.effective_user.first_name or "Customer"}
        confirmation = gemini.generate_order_confirmation(order_data)
        await update.message.reply_text(confirmation, parse_mode="Markdown")
        user = await sync_to_async(TelegramUser.objects.get)(user_id=update.effective_user.id)
        await sync_to_async(Conversation.objects.create)(user=user, message=f"ORDER CONFIRMED #{order.id}", direction="outgoing")
    except Order.DoesNotExist:
        await update.message.reply_text("Payment went through but order record not found. Contact support.")
    except Exception as e:
        print(f"Success handler error: {e}")
        await update.message.reply_text("Payment received. Processing your order...")


async def _safe_edit(query, text, reply_markup=None):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        try:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e2:
            print(f"Safe edit failed: {e2}")


async def _safe_send(query, context, text):
    try:
        await context.bot.send_message(chat_id=query.from_user.id, text=text, parse_mode="Markdown")
    except Exception as e:
        print(f"Safe send failed: {e}")


async def _send(update, tg_user, intent_type, msg, product_type=None):
    r = gemini.generate_response(intent_type, msg, product_type=product_type)
    await update.message.reply_text(r, parse_mode="Markdown")
    await persist_message(tg_user, r, "outgoing")