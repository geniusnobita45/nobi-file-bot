import telebot
import os
import time
import logging
from flask import Flask, request
from pdf2docx import Converter
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image, ImageEnhance
from docx2pdf import convert
from pdf2image import convert_from_path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = telebot.TeleBot("8201009198:AAGhsiDkPtAxcLmw1gIvbz7gnX9mFAeQudk")
user_state = {}
user_last_interaction = {}
user_images = {}
webhook_url = os.getenv('WEBHOOK_URL', 'https://nobi-file-bot.onrender.com/webhook')

def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("PDF to Word"), telebot.types.KeyboardButton("Word to PDF"))
    markup.add(telebot.types.KeyboardButton("Enhance Image"), telebot.types.KeyboardButton("Sign PDF"))
    markup.add(telebot.types.KeyboardButton("JPG to PDF"))
    markup.add(telebot.types.KeyboardButton("PNG to JPG"), telebot.types.KeyboardButton("JPG to PNG"))
    return markup

@app.route('/')
def health_check():
    logger.info("Health check accessed")
    return 'Bot is running', 200

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_state[chat_id] = "MAIN_MENU"
    user_last_interaction[chat_id] = time.time()
    logger.info(f"Received /start from chat_id: {chat_id}")
    try:
        bot.send_message(chat_id, "🌟 Hiii, cutie! I'm @genius_nobita_45, your file helper! 😘\nSelect a task:", reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Error sending /start response to chat_id {chat_id}: {e}")

@bot.message_handler(content_types=['text'])
def debug_text(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    text = message.text.lower()
    logger.info(f"Received text: {text}, chat_id: {chat_id}, state: {user_state.get(chat_id)}")
    try:
        bot.reply_to(message, f"Received: {message.text}\nState: {user_state.get(chat_id)}")
        if text == "pdf to word":
            user_state[chat_id] = "PDF_TO_WORD"
            bot.send_message(chat_id, "😉 Upload a PDF (<20 MB), sweetie! 💕")
        elif text == "word to pdf":
            user_state[chat_id] = "WORD_TO_PDF"
            bot.send_message(chat_id, "😍 Send me a Word doc (.docx), darling! 💖")
        elif text == "enhance image":
            user_state[chat_id] = "ENHANCE_IMAGE"
            bot.send_message(chat_id, "🥰 Upload a JPG or PNG to enhance, cutie! ✨")
        elif text == "sign pdf":
            user_state[chat_id] = "SIGN_PDF"
            bot.send_message(chat_id, "😚 Upload a PDF to sign, love! ✍️")
        elif text == "jpg to pdf":
            user_state[chat_id] = "JPG_TO_PDF"
            bot.send_message(chat_id, "🌸 Send JPGs one by one, then type 'Done' when ready, honey! 😊")
        elif text == "png to jpg":
            user_state[chat_id] = "PNG_TO_JPG"
            bot.send_message(chat_id, "😊 Upload a PNG to convert to JPG, darling! 💖")
        elif text == "jpg to png":
            user_state[chat_id] = "JPG_TO_PNG"
            bot.send_message(chat_id, "😊 Upload a JPG to convert to PNG, cutie! ✨")
        else:
            bot.send_message(chat_id, "😜 Pick an option from the menu, cutie! 💞", reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Error handling text message from chat_id {chat_id}: {e}")

@bot.message_handler(content_types=['photo', 'document'], func=lambda m: user_state.get(m.chat.id) == "ENHANCE_IMAGE")
def enhance_image(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    file_name = None
    logger.info(f"Enhance image request from chat_id: {chat_id}")
    if message.content_type == 'photo':
        file_info = bot.get_file(message.photo[-1].file_id)
        file_name = 'temp.jpg'
        downloaded = bot.download_file(file_info.file_path)
        with open(file_name, 'wb') as f:
            f.write(downloaded)
    elif message.content_type == 'document' and message.document.file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        downloaded = bot.download_file(file_info.file_path)
        with open(file_name, 'wb') as f:
            f.write(downloaded)
    else:
        bot.send_message(chat_id, "😉 Sweetie, I need a JPG or PNG! Try again! 💕", reply_markup=main_menu())
        logger.info(f"Invalid file type for enhance image, chat_id: {chat_id}")
        return
    try:
        img = Image.open(file_name)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.5)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.2)
        enhanced_name = file_name.rsplit('.', 1)[0] + '_enhanced.' + file_name.rsplit('.', 1)[1]
        img.save(enhanced_name)
        with open(enhanced_name, 'rb') as f:
            bot.send_document(chat_id, f)
        bot.send_message(chat_id, "✨ Enhanced your image, cutie! What's next? 😘", reply_markup=main_menu())
        os.remove(enhanced_name)
    except Exception as e:
        bot.send_message(chat_id, f"😢 Enhancement failed: {e}. Try again, love! 💕", reply_markup=main_menu())
        logger.error(f"Image enhancement failed for chat_id {chat_id}: {e}")
    os.remove(file_name)
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())

@bot.message_handler(content_types=['document'], func=lambda m: user_state.get(m.chat.id) == "PNG_TO_JPG")
def png_to_jpg(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    logger.info(f"PNG to JPG request from chat_id: {chat_id}")
    if message.document.file_name.lower().endswith('.png'):
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        png_path = "temp.png"
        jpg_path = "converted.jpg"
        with open(png_path, 'wb') as f:
            f.write(downloaded)
        try:
            img = Image.open(png_path).convert('RGB')
            img.save(jpg_path, 'JPEG')
            with open(jpg_path, 'rb') as f:
                bot.send_document(chat_id, f)
            os.remove(png_path)
            os.remove(jpg_path)
            bot.send_message(chat_id, "🌟 Here's your JPG, darling! What's next? 😘", reply_markup=main_menu())
        except Exception as e:
            bot.send_message(chat_id, f"😢 Oops, conversion failed: {e}. Try another PNG, love! 💖", reply_markup=main_menu())
            logger.error(f"PNG to JPG failed for chat_id {chat_id}: {e}")
            os.remove(png_path)
    else:
        bot.send_message(chat_id, "😉 I need a PNG, cutie! Try again! 💕", reply_markup=main_menu())
        logger.info(f"Invalid file type for PNG to JPG, chat_id: {chat_id}")
    user_state[chat_id] = "MAIN_MENU"

@bot.message_handler(content_types=['photo', 'document'], func=lambda m: user_state.get(m.chat.id) == "JPG_TO_PNG")
def jpg_to_png(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    logger.info(f"JPG to PNG request from chat_id: {chat_id}")
    file_name = None
    if message.content_type == 'photo':
        file_info = bot.get_file(message.photo[-1].file_id)
        file_name = 'temp.jpg'
        downloaded = bot.download_file(file_info.file_path)
        with open(file_name, 'wb') as f:
            f.write(downloaded)
    elif message.content_type == 'document' and message.document.file_name.lower().endswith(('.jpg', '.jpeg')):
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        downloaded = bot.download_file(file_info.file_path)
        with open(file_name, 'wb') as f:
            f.write(downloaded)
    else:
        bot.send_message(chat_id, "😉 I need a JPG, sweetie! Try again! 💕", reply_markup=main_menu())
        logger.info(f"Invalid file type for JPG to PNG, chat_id: {chat_id}")
        return
    try:
        img = Image.open(file_name).convert('RGBA')
        png_path = file_name.rsplit('.', 1)[0] + '.png'
        img.save(png_path, 'PNG')
        with open(png_path, 'rb') as f:
            bot.send_document(chat_id, f)
        os.remove(file_name)
        os.remove(png_path)
        bot.send_message(chat_id, "🌟 Here's your PNG, cutie! What's next? 😘", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(chat_id, f"😢 Oops, conversion failed: {e}. Try another JPG, love! 💖", reply_markup=main_menu())
        logger.error(f"JPG to PNG failed for chat_id {chat_id}: {e}")
        os.remove(file_name)
    user_state[chat_id] = "MAIN_MENU"

@bot.message_handler(content_types=['document'], func=lambda m: user_state.get(m.chat.id) == "PDF_TO_WORD")
def pdf_to_word(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    logger.info(f"PDF to Word request from chat_id: {chat_id}")
    if message.document.file_name.lower().endswith('.pdf'):
        file_info = bot.get_file(message.document.file_id)
        if file_info.file_size > 20 * 1024 * 1024:
            bot.send_message(chat_id, "😅 PDF too big, sweetie! Keep it under 20 MB, okay? 💕", reply_markup=main_menu())
            logger.info(f"PDF too large for chat_id: {chat_id}, size: {file_info.file_size}")
            return
        downloaded = bot.download_file(file_info.file_path)
        pdf_path = "temp.pdf"
        docx_path = "converted.docx"
        with open(pdf_path, 'wb') as f:
            f.write(downloaded)
        try:
            cv = Converter(pdf_path)
            cv.convert(docx_path)
            cv.close()
            with open(docx_path, 'rb') as f:
                bot.send_document(chat_id, f)
            os.remove(pdf_path)
            os.remove(docx_path)
            bot.send_message(chat_id, "🌟 Here's your Word doc, darling! What's next? 😘", reply_markup=main_menu())
        except Exception as e:
            bot.send_message(chat_id, f"😢 Oops, something went wrong: {e}. Try another PDF, love! 💖", reply_markup=main_menu())
            logger.error(f"PDF to Word failed for chat_id {chat_id}: {e}")
            os.remove(pdf_path)
    else:
        bot.send_message(chat_id, "😉 I need a PDF, cutie! Try again! 💕", reply_markup=main_menu())
        logger.info(f"Invalid file type for PDF to Word, chat_id: {chat_id}")
    user_state[chat_id] = "MAIN_MENU"

@bot.message_handler(content_types=['document'], func=lambda m: user_state.get(m.chat.id) == "WORD_TO_PDF")
def word_to_pdf(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    logger.info(f"Word to PDF request from chat_id: {chat_id}")
    if message.document.file_name.lower().endswith('.docx'):
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        docx_path = "temp.docx"
        pdf_path = "converted.pdf"
        with open(docx_path, 'wb') as f:
            f.write(downloaded)
        try:
            convert(docx_path, pdf_path)
            with open(pdf_path, 'rb') as f:
                bot.send_document(chat_id, f)
            os.remove(docx_path)
            os.remove(pdf_path)
            bot.send_message(chat_id, "🌟 Here's your PDF, sweetie! What's next? 😍", reply_markup=main_menu())
        except Exception as e:
            bot.send_message(chat_id, f"😢 Oops, something went wrong: {e}. Try another Word doc, love! 💖", reply_markup=main_menu())
            logger.error(f"Word to PDF failed for chat_id {chat_id}: {e}")
            os.remove(docx_path)
    else:
        bot.send_message(chat_id, "😉 I need a .docx file, darling! Try again! 💕", reply_markup=main_menu())
        logger.info(f"Invalid file type for Word to PDF, chat_id: {chat_id}")
    user_state[chat_id] = "MAIN_MENU"

@bot.message_handler(content_types=['document'], func=lambda m: user_state.get(m.chat.id) == "SIGN_PDF")
def sign_pdf(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    logger.info(f"Sign PDF request from chat_id: {chat_id}")
    if message.document.file_name.lower().endswith('.pdf'):
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        pdf_path = "temp.pdf"
        signed_pdf_path = "signed.pdf"
        with open(pdf_path, 'wb') as f:
            f.write(downloaded)
        try:
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            c = canvas.Canvas(signed_pdf_path, pagesize=letter)
            c.drawString(50, 50, "Signed by @genius_nobita_45")
            c.showPage()
            c.save()
            signed_reader = PdfReader(signed_pdf_path)
            writer.add_page(signed_reader.pages[0])
            with open(signed_pdf_path, 'wb') as f:
                writer.write(f)
            with open(signed_pdf_path, 'rb') as f:
                bot.send_document(chat_id, f)
            os.remove(pdf_path)
            os.remove(signed_pdf_path)
            bot.send_message(chat_id, "✍️ Signed your PDF, love! What's next? 😘", reply_markup=main_menu())
        except Exception as e:
            bot.send_message(chat_id, f"😢 Oops, something went wrong: {e}. Try another PDF, cutie! 💖", reply_markup=main_menu())
            logger.error(f"Sign PDF failed for chat_id {chat_id}: {e}")
            os.remove(pdf_path)
    else:
        bot.send_message(chat_id, "😉 I need a PDF, sweetie! Try again! 💕", reply_markup=main_menu())
        logger.info(f"Invalid file type for Sign PDF, chat_id: {chat_id}")
    user_state[chat_id] = "MAIN_MENU"

@bot.message_handler(content_types=['photo'], func=lambda m: user_state.get(m.chat.id) == "JPG_TO_PDF")
def jpg_to_pdf(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    logger.info(f"JPG to PDF image upload from chat_id: {chat_id}")
    if chat_id not in user_images:
        user_images[chat_id] = []
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded = bot.download_file(file_info.file_path)
    img_path = f"temp_{chat_id}_{len(user_images[chat_id])}.jpg"
    with open(img_path, 'wb') as f:
        f.write(downloaded)
    user_images[chat_id].append(img_path)
    bot.send_message(chat_id, "🌟 Got your image, cutie! Send more or type 'Done' to make the PDF! 😘")

@bot.message_handler(content_types=['text'], func=lambda m: user_state.get(m.chat.id) == "JPG_TO_PDF" and m.text.lower() == 'done')
def create_pdf_from_images(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    logger.info(f"JPG to PDF 'Done' request from chat_id: {chat_id}")
    if chat_id not in user_images or not user_images[chat_id]:
        bot.send_message(chat_id, "😅 No images yet, darling! Send some JPGs first! 💕", reply_markup=main_menu())
        logger.info(f"No images for JPG to PDF, chat_id: {chat_id}")
        user_state[chat_id] = "MAIN_MENU"
        return
    pdf_path = f"output_{chat_id}.pdf"
    c = canvas.Canvas(pdf_path, pagesize=letter)
    for img_path in user_images[chat_id]:
        try:
            img = Image.open(img_path)
            img_width, img_height = img.size
            aspect = img_height / float(img_width)
            target_width = 500
            target_height = target_width * aspect
            c.drawImage(img_path, 50, 300, width=target_width, height=target_height)
            c.showPage()
        except Exception as e:
            bot.send_message(chat_id, f"😢 Error with an image: {e}. Skipping it, love! 💖")
            logger.error(f"JPG to PDF image processing failed for chat_id {chat_id}: {e}")
        os.remove(img_path)
    c.save()
    with open(pdf_path, 'rb') as f:
        bot.send_document(chat_id, f)
    os.remove(pdf_path)
    user_images[chat_id] = []
    bot.send_message(chat_id, "🌟 Here's your PDF, sweetie! What's next? 😍", reply_markup=main_menu())
    user_state[chat_id] = "MAIN_MENU"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_json())
        logger.info(f"Webhook received update: {update}")
        bot.process_new_updates([update])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return '', 500

if __name__ == '__main__':
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=webhook_url)
    logger.info(f"Setting webhook to {webhook_url}")
    app.run(host='0.0.0.0', port=5000)