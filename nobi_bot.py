from flask import Flask, request
import telebot
import os
from telebot import types
from pdf2docx import Converter
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from PIL import Image, ImageEnhance
from docx2pdf import convert
from pdf2image import convert_from_path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import time
import threading
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
bot = telebot.TeleBot("8247281321:AAG7A-D9HFa93-As9eITy8JNotCgYbSC0DM")
MAX_BOT_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
SESSION_TIMEOUT = 2 * 3600  # 2 hours in seconds
# Sticker disabled due to invalid ID; uncomment with valid ID if needed
# STICKER_ID = "CAACAgIAAxkBAAIBKWbF9b7L0o0UAAH3qV8AAQ5rEy3-AAJIAQACWOaOBQz1bJ6WAAHtAAQJ"

user_state = {}
user_files = {}
user_data = {}
user_last_interaction = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("PDF to Word", "Word to PDF")
    markup.add("JPG to PDF", "PDF to JPG")
    markup.add("JPG to PNG", "PNG to JPG")
    markup.add("Merge PDF", "Compress File")
    markup.add("Enhance Image", "Sign PDF")
    markup.add("Edit PDF", "More Tools", "Exit")
    return markup

def more_tools_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Highlight/Add Text", "Fill Forms/E-sign")
    markup.add("Merge/Split/Remove Pages", "Store/Share Files")
    markup.add("Mobile App", "Back to Main Menu")
    return markup

def safe_send_sticker(chat_id):
    # Disabled due to invalid sticker ID; replace with valid ID if re-enabling
    pass
    # try:
    #     bot.send_sticker(chat_id, STICKER_ID)
    # except Exception as e:
    #     logging.error(f"Failed to send sticker: {e}")
    #     bot.send_message(chat_id, "😅 Oops, my sticker got shy! Let's keep going! 💕")

def reset_session(chat_id):
    if chat_id in user_state:
        user_state[chat_id] = "MAIN_MENU"
        for file in user_files.get(chat_id, []):
            if os.path.exists(file):
                os.remove(file)
        user_files[chat_id] = []
        if chat_id in user_data:
            if os.path.exists(user_data[chat_id].get('pdf_file', '')):
                os.remove(user_data[chat_id]['pdf_file'])
            del user_data[chat_id]
        bot.send_message(chat_id, "🌸 Oh, looks like you took a little break! We're back to the main menu, ready for more fun! 😊", reply_markup=main_menu())
        safe_send_sticker(chat_id)

def check_timeout():
    while True:
        current_time = time.time()
        for chat_id, last_time in list(user_last_interaction.items()):
            if current_time - last_time > SESSION_TIMEOUT:
                reset_session(chat_id)
                user_last_interaction.pop(chat_id, None)
        time.sleep(60)

threading.Thread(target=check_timeout, daemon=True).start()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_state[chat_id] = "MAIN_MENU"
    user_last_interaction[chat_id] = time.time()
    safe_send_sticker(chat_id)
    bot.send_message(
        chat_id,
        "🌟 Hiii, cutie! I'm @genius_nobita_45, your magical File Handler Bot! 💖 Pick a task to transform PDFs or images with AI magic! 😘",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda message: user_state.get(message.chat.id) == "MAIN_MENU")
def handle_main_menu(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    text = message.text

    if text == "PDF to Word":
        user_state[chat_id] = "PDF_TO_WORD"
        bot.send_message(chat_id, "💌 Ooh, wanna turn a PDF into a Word doc? Send me your PDF (up to 20 MB), and I'll work my magic! ✨")
    elif text == "Word to PDF":
        user_state[chat_id] = "WORD_TO_PDF"
        bot.send_message(chat_id, "📜 Got a Word file to transform into a PDF? Drop it here (max 20 MB), and I'll make it super sleek! 😊")
    elif text == "JPG to PDF":
        user_state[chat_id] = "JPG_TO_PDF"
        user_files[chat_id] = []
        bot.send_message(chat_id, "🖼️ Ready to turn your pics into a PDF? Send me your images, and when you're done, just say 'Done'! 💕")
    elif text == "PDF to JPG":
        user_state[chat_id] = "PDF_TO_JPG"
        bot.send_message(chat_id, "🎨 Wanna make your PDF pages into JPGs? Send the PDF (max 20 MB), and I'll paint them pretty! 🌈")
    elif text == "JPG to PNG":
        user_state[chat_id] = "JPG_TO_PNG"
        bot.send_message(chat_id, "🌟 Let's swap that JPG for a PNG! Send your JPG (max 20 MB), and I'll make it happen! 😘")
    elif text == "PNG to JPG":
        user_state[chat_id] = "PNG_TO_JPG"
        bot.send_message(chat_id, "💖 Got a PNG to turn into a JPG? Send it over (max 20 MB), and I'll give it a new look! 😍")
    elif text == "Merge PDF":
        user_state[chat_id] = "MERGE_PDF"
        user_files[chat_id] = []
        bot.send_message(chat_id, "📚 Wanna combine some PDFs? Send them one by one, and say 'Done' when you're ready to merge! 🥰")
    elif text == "Compress File":
        user_state[chat_id] = "COMPRESS_FILE"
        bot.send_message(chat_id, "🗜️ Need to shrink a file? Send me a PDF or image (max 20 MB), and I'll make it super tiny! 💞")
    elif text == "Enhance Image":
        user_state[chat_id] = "ENHANCE_IMAGE"
        bot.send_message(chat_id, "✨ Wanna make your pic pop? Send a JPG or PNG (max 20 MB), and I'll make it sparkle! 😍")
    elif text == "Sign PDF":
        user_state[chat_id] = "SIGN_PDF"
        bot.send_message(chat_id, "🖋️ Ready to sign a PDF? Send it over (max 20 MB), and I'll help you add your special touch! 💖")
    elif text == "Edit PDF":
        user_state[chat_id] = "EDIT_PDF"
        bot.send_message(chat_id, "📝 Wanna add some notes to a PDF? Send it (max 20 MB), and we'll make it your own! 😘")
    elif text == "More Tools":
        user_state[chat_id] = "MORE_TOOLS"
        bot.send_message(chat_id, "🔧 Ooh, more fun tools to explore? Pick one, cutie! 😊", reply_markup=more_tools_menu())
    elif text == "Exit":
        user_state[chat_id] = "MAIN_MENU"
        bot.send_message(chat_id, "🌸 Aww, taking a break? I'm right here at the main menu whenever you need me! 😍", reply_markup=main_menu())
        safe_send_sticker(chat_id)
    else:
        bot.send_message(chat_id, "😉 Hey sweetie, pick something from the menu, and let's have some fun! 💕", reply_markup=main_menu())

@bot.message_handler(func=lambda message: user_state.get(message.chat.id) == "MORE_TOOLS")
def handle_more_tools(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    text = message.text
    if text == "Highlight/Add Text":
        bot.send_message(chat_id, "🌟 Wanna highlight or add text to a PDF? That feature's cooking! Try something else for now! 😘")
    elif text == "Fill Forms/E-sign":
        bot.send_message(chat_id, "📜 Forms and e-signing? It's on the way! Pick another tool, cutie! 😊")
    elif text == "Merge/Split/Remove Pages":
        bot.send_message(chat_id, "📚 Merge, split, or remove pages? Coming soon! Let's try another trick! 💖")
    elif text == "Store/Share Files":
        bot.send_message(chat_id, "💾 Storing or sharing files? Not yet, but soon! Pick something fun for now! 😍")
    elif text == "Mobile App":
        bot.send_message(chat_id, "📱 A mobile app for scanning? It's in the works! Try another tool, sweetie! 😘")
    elif text == "Back to Main Menu":
        user_state[chat_id] = "MAIN_MENU"
        bot.send_message(chat_id, "🌸 Back to the main menu, ready for more adventures! 😊", reply_markup=main_menu())
        safe_send_sticker(chat_id)
    else:
        bot.send_message(chat_id, "😉 Pick a tool from the menu, cutie! Let's make some magic! 💕", reply_markup=more_tools_menu())

@bot.message_handler(content_types=['document'], func=lambda m: user_state.get(m.chat.id) == "PDF_TO_WORD")
def pdf_to_word(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    if message.document.file_size > MAX_BOT_FILE_SIZE:
        bot.send_message(chat_id, "😓 Oh no, that file's too big! Keep it under 20 MB, okay? Back to menu! 💖", reply_markup=main_menu())
        user_state[chat_id] = "MAIN_MENU"
        return
    file_info = bot.get_file(message.document.file_id)
    file_name = message.document.file_name
    downloaded = bot.download_file(file_info.file_path)
    with open(file_name, 'wb') as f:
        f.write(downloaded)
    try:
        docx_name = file_name.replace('.pdf', '.docx')
        cv = Converter(file_name)
        cv.convert(docx_name)
        cv.close()
        with open(docx_name, 'rb') as f:
            bot.send_document(chat_id, f)
        bot.send_message(chat_id, "🎉 Ta-da! Your PDF is now a Word doc! @genius_nobita_45 worked its magic! 😘", reply_markup=main_menu())
        safe_send_sticker(chat_id)
        os.remove(docx_name)
    except Exception as e:
        bot.send_message(chat_id, f"😢 Oops, something went wrong: {e}. Let's try again! 💕", reply_markup=main_menu())
    os.remove(file_name)
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())

@bot.message_handler(content_types=['document'], func=lambda m: user_state.get(m.chat.id) == "WORD_TO_PDF")
def word_to_pdf(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    if message.document.file_size > MAX_BOT_FILE_SIZE:
        bot.send_message(chat_id, "😓 That file's a bit too chubby! Keep it under 20 MB, okay? Back to menu! 💖", reply_markup=main_menu())
        user_state[chat_id] = "MAIN_MENU"
        return
    file_info = bot.get_file(message.document.file_id)
    file_name = message.document.file_name
    downloaded = bot.download_file(file_info.file_path)
    with open(file_name, 'wb') as f:
        f.write(downloaded)
    try:
        pdf_name = file_name.replace('.docx', '.pdf')
        convert(file_name, pdf_name)
        with open(pdf_name, 'rb') as f:
            bot.send_document(chat_id, f)
        bot.send_message(chat_id, "🎉 Yay, your Word file is now a sleek PDF! @genius_nobita_45 did it! 😘", reply_markup=main_menu())
        safe_send_sticker(chat_id)
        os.remove(pdf_name)
    except Exception as e:
        bot.send_message(chat_id, f"😢 Oh no, something broke: {e}. Let's try again! 💕", reply_markup=main_menu())
    os.remove(file_name)
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())

@bot.message_handler(content_types=['document'], func=lambda m: user_state.get(m.chat.id) == "PDF_TO_JPG")
def pdf_to_jpg(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    if message.document.file_size > MAX_BOT_FILE_SIZE:
        bot.send_message(chat_id, "😓 That PDF's too big! Keep it under 20 MB, okay? Back to menu! 💖", reply_markup=main_menu())
        user_state[chat_id] = "MAIN_MENU"
        return
    file_info = bot.get_file(message.document.file_id)
    file_name = message.document.file_name
    downloaded = bot.download_file(file_info.file_path)
    with open(file_name, 'wb') as f:
        f.write(downloaded)
    try:
        images = convert_from_path(file_name)
        for i, img in enumerate(images):
            jpg_name = f"{file_name.replace('.pdf', '')}_page_{i+1}.jpg"
            img.save(jpg_name, 'JPEG')
            with open(jpg_name, 'rb') as f:
                bot.send_document(chat_id, f)
            os.remove(jpg_name)
        bot.send_message(chat_id, "🎨 Your PDF pages are now JPGs! @genius_nobita_45 made them pretty! 😘", reply_markup=main_menu())
        safe_send_sticker(chat_id)
    except Exception as e:
        bot.send_message(chat_id, f"😢 Oops, something went wrong: {e}. Let's try again! 💕", reply_markup=main_menu())
    os.remove(file_name)
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())

@bot.message_handler(content_types=['photo', 'document'], func=lambda m: user_state.get(m.chat.id) == "JPG_TO_PNG")
def jpg_to_png(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
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
        bot.send_message(chat_id, "😉 Sweetie, I need a JPG for this! Try again! 💕", reply_markup=main_menu())
        return
    try:
        png_name = file_name.replace('.jpg', '.png').replace('.jpeg', '.png')
        img = Image.open(file_name)
        img.save(png_name, 'PNG')
        with open(png_name, 'rb') as f:
            bot.send_document(chat_id, f)
        bot.send_message(chat_id, "🌟 Your JPG is now a PNG! @genius_nobita_45 made it shiny! 😘", reply_markup=main_menu())
        safe_send_sticker(chat_id)
        os.remove(png_name)
    except Exception as e:
        bot.send_message(chat_id, f"😢 Oh no, something broke: {e}. Let's try again! 💕", reply_markup=main_menu())
    os.remove(file_name)
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())

@bot.message_handler(content_types=['photo', 'document'], func=lambda m: user_state.get(m.chat.id) == "PNG_TO_JPG")
def png_to_jpg(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    file_name = None
    if message.content_type == 'photo':
        file_info = bot.get_file(message.photo[-1].file_id)
        file_name = 'temp.png'
        downloaded = bot.download_file(file_info.file_path)
        with open(file_name, 'wb') as f:
            f.write(downloaded)
    elif message.content_type == 'document' and message.document.file_name.lower().endswith('.png'):
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        downloaded = bot.download_file(file_info.file_path)
        with open(file_name, 'wb') as f:
            f.write(downloaded)
    else:
        bot.send_message(chat_id, "😉 Sweetie, I need a PNG for this! Try again! 💕", reply_markup=main_menu())
        return
    try:
        jpg_name = file_name.replace('.png', '.jpg')
        img = Image.open(file_name)
        img.convert('RGB').save(jpg_name, 'JPEG')
        with open(jpg_name, 'rb') as f:
            bot.send_document(chat_id, f)
        bot.send_message(chat_id, "💖 Your PNG is now a JPG! @genius_nobita_45 gave it a new look! 😘", reply_markup=main_menu())
        safe_send_sticker(chat_id)
        os.remove(jpg_name)
    except Exception as e:
        bot.send_message(chat_id, f"😢 Oh no, something broke: {e}. Let's try again! 💕", reply_markup=main_menu())
    os.remove(file_name)
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())

@bot.message_handler(content_types=['document'], func=lambda m: user_state.get(m.chat.id) == "MERGE_PDF")
def merge_pdf_collect(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    if message.document.file_size > MAX_BOT_FILE_SIZE:
        bot.send_message(chat_id, "😓 That PDF's too big! Keep it under 20 MB, okay? 💕", reply_markup=main_menu())
        return
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.send_message(chat_id, "😉 Sweetie, I need PDFs only! Try again! 💖", reply_markup=main_menu())
        return
    file_info = bot.get_file(message.document.file_id)
    file_name = f"{chat_id}_{message.document.file_name}"
    downloaded = bot.download_file(file_info.file_path)
    with open(file_name, 'wb') as f:
        f.write(downloaded)
    user_files[chat_id].append(file_name)
    bot.send_message(chat_id, f"📚 Got it! Added your PDF! Send more or say 'Done' to merge them! 😘", reply_markup=main_menu())
    safe_send_sticker(chat_id)

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "MERGE_PDF" and m.text.lower() == "done")
def merge_pdf_done(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    files = user_files.get(chat_id, [])
    if len(files) < 2:
        bot.send_message(chat_id, "😉 Sweetie, I need at least two PDFs to merge! Send more! 💕", reply_markup=main_menu())
        return
    try:
        merger = PdfMerger()
        for pdf in files:
            merger.append(pdf)
        merged_name = f"{chat_id}_merged.pdf"
        merger.write(merged_name)
        merger.close()
        with open(merged_name, 'rb') as f:
            bot.send_document(chat_id, f)
        bot.send_message(chat_id, "🎉 Yay, your PDFs are now one big happy file! @genius_nobita_45 did it! 😘", reply_markup=main_menu())
        safe_send_sticker(chat_id)
        os.remove(merged_name)
        for pdf in files:
            os.remove(pdf)
        user_files[chat_id] = []
    except Exception as e:
        bot.send_message(chat_id, f"😢 Oh no, something broke: {e}. Let's try again! 💕", reply_markup=main_menu())
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())

@bot.message_handler(content_types=['photo', 'document'], func=lambda m: user_state.get(m.chat.id) == "JPG_TO_PDF")
def jpg_to_pdf_collect(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    file_name = None
    if message.content_type == 'photo':
        file_info = bot.get_file(message.photo[-1].file_id)
        file_name = f"{chat_id}_img_{len(user_files.get(chat_id, []))+1}.jpg"
        downloaded = bot.download_file(file_info.file_path)
        with open(file_name, 'wb') as f:
            f.write(downloaded)
    elif message.content_type == 'document':
        if not message.document.file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')):
            bot.send_message(chat_id, "😉 Sweetie, I need images only! Try again! 💕", reply_markup=main_menu())
            return
        file_info = bot.get_file(message.document.file_id)
        file_name = f"{chat_id}_{message.document.file_name}"
        downloaded = bot.download_file(file_info.file_path)
        with open(file_name, 'wb') as f:
            f.write(downloaded)
    if file_name:
        user_files[chat_id].append(file_name)
        bot.send_message(chat_id, f"🖼️ Got your image! So pretty! Send more or say 'Done' to make a PDF! 😘", reply_markup=main_menu())
        safe_send_sticker(chat_id)

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "JPG_TO_PDF" and m.text.lower() == "done")
def jpg_to_pdf_done(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    files = user_files.get(chat_id, [])
    if not files:
        bot.send_message(chat_id, "😉 Sweetie, I need at least one image! Send one! 💕", reply_markup=main_menu())
        return
    try:
        images = [Image.open(f).convert("RGB") for f in files]
        pdf_name = f"{chat_id}_images.pdf"
        images[0].save(pdf_name, save_all=True, append_images=images[1:])
        with open(pdf_name, 'rb') as f:
            bot.send_document(chat_id, f)
        bot.send_message(chat_id, "🎉 Your images are now a super cute PDF! @genius_nobita_45 worked its magic! 😘", reply_markup=main_menu())
        safe_send_sticker(chat_id)
        os.remove(pdf_name)
        for img in files:
            os.remove(img)
        user_files[chat_id] = []
    except Exception as e:
        bot.send_message(chat_id, f"😢 Oh no, something broke: {e}. Let's try again! 💕", reply_markup=main_menu())
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())

@bot.message_handler(content_types=['photo', 'document'], func=lambda m: user_state.get(m.chat.id) == "COMPRESS_FILE")
def compress_file(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    file_name = None
    if message.content_type == 'photo':
        file_info = bot.get_file(message.photo[-1].file_id)
        file_name = 'temp.jpg'
        downloaded = bot.download_file(file_info.file_path)
        with open(file_name, 'wb') as f:
            f.write(downloaded)
    elif message.content_type == 'document':
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        downloaded = bot.download_file(file_info.file_path)
        with open(file_name, 'wb') as f:
            f.write(downloaded)
    if not file_name:
        bot.send_message(chat_id, "😉 Sweetie, send a PDF or image! Try again! 💕", reply_markup=main_menu())
        return
    try:
        if file_name.lower().endswith('.pdf'):
            reader = PdfReader(file_name)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.add_metadata(reader.metadata)
            compressed_name = file_name.replace('.pdf', '_compressed.pdf')
            with open(compressed_name, 'wb') as f:
                writer.write(f)
            with open(compressed_name, 'rb') as f:
                bot.send_document(chat_id, f)
            bot.send_message(chat_id, "🗜️ Your PDF is now super tiny! @genius_nobita_45 did it! 😘", reply_markup=main_menu())
            safe_send_sticker(chat_id)
            os.remove(compressed_name)
        else:
            img = Image.open(file_name)
            compressed_name = file_name.rsplit('.', 1)[0] + '_compressed.' + file_name.rsplit('.', 1)[1]
            img.save(compressed_name, quality=50, optimize=True)
            with open(compressed_name, 'rb') as f:
                bot.send_document(chat_id, f)
            bot.send_message(chat_id, "🗜️ Your image is now super slim! @genius_nobita_45 worked its magic! 😘", reply_markup=main_menu())
            safe_send_sticker(chat_id)
            os.remove(compressed_name)
    except Exception as e:
        bot.send_message(chat_id, f"😢 Oh no, something broke: {e}. Let's try again! 💕", reply_markup=main_menu())
    os.remove(file_name)
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())

@bot.message_handler(content_types=['photo', 'document'], func=lambda m: user_state.get(m.chat.id) == "ENHANCE_IMAGE")
def enhance_image(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    file_name = None
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
        bot.send_message(chat_id, "✨ Your pic is now sparkling bright! @genius_nobita_45 made it pop! 😘", reply_markup=main_menu())
        safe_send_sticker(chat_id)
        os.remove(enhanced_name)
    except Exception as e:
        bot.send_message(chat_id, f"😢 Oh no, something broke: {e}. Let's try again! 💕", reply_markup=main_menu())
    os.remove(file_name)
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())

@bot.message_handler(content_types=['document'], func=lambda m: user_state.get(m.chat.id) == "SIGN_PDF")
def sign_pdf(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    if message.document.file_size > MAX_BOT_FILE_SIZE:
        bot.send_message(chat_id, "😓 That PDF's too big! Keep it under 20 MB, okay? Back to menu! 💖", reply_markup=main_menu())
        user_state[chat_id] = "MAIN_MENU"
        return
    file_info = bot.get_file(message.document.file_id)
    file_name = message.document.file_name
    if not file_name.lower().endswith('.pdf'):
        bot.send_message(chat_id, "😉 Sweetie, I need a PDF! Try again! 💕", reply_markup=main_menu())
        user_state[chat_id] = "MAIN_MENU"
        bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())
        return
    downloaded = bot.download_file(file_info.file_path)
    with open(file_name, 'wb') as f:
        f.write(downloaded)
    user_data[chat_id] = {'pdf_file': file_name}
    user_state[chat_id] = "SIGN_PDF_TEXT"
    bot.send_message(chat_id, "🖋️ Ooh, time to add your special signature! Type your name or a cute message! 😘")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "SIGN_PDF_TEXT")
def sign_pdf_text(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    signature_text = message.text
    pdf_file = user_data.get(chat_id, {}).get('pdf_file')
    if not pdf_file or not os.path.exists(pdf_file):
        bot.send_message(chat_id, "😢 Oh no, the PDF got lost! Start over, sweetie! 💕", reply_markup=main_menu())
        user_state[chat_id] = "MAIN_MENU"
        bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())
        return
    try:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(100, 100, signature_text)
        c.showPage()
        c.save()
        buffer.seek(0)
        signature_pdf = PdfReader(buffer)
        reader = PdfReader(pdf_file)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.get_page(0).merge_page(signature_pdf.pages[0])
        signed_name = pdf_file.replace('.pdf', '_signed.pdf')
        with open(signed_name, 'wb') as f:
            writer.write(f)
        with open(signed_name, 'rb') as f:
            bot.send_document(chat_id, f)
        bot.send_message(chat_id, f"🎉 Your PDF is signed with '{signature_text}'! @genius_nobita_45 made it official! 😘", reply_markup=main_menu())
        safe_send_sticker(chat_id)
        os.remove(signed_name)
        os.remove(pdf_file)
        del user_data[chat_id]
    except Exception as e:
        bot.send_message(chat_id, f"😢 Oh no, something broke: {e}. Let's try again! 💕", reply_markup=main_menu())
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())

@bot.message_handler(content_types=['document'], func=lambda m: user_state.get(m.chat.id) == "EDIT_PDF")
def edit_pdf(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    if message.document.file_size > MAX_BOT_FILE_SIZE:
        bot.send_message(chat_id, "😓 That PDF's too big! Keep it under 20 MB, okay? Back to menu! 💖", reply_markup=main_menu())
        user_state[chat_id] = "MAIN_MENU"
        return
    file_info = bot.get_file(message.document.file_id)
    file_name = message.document.file_name
    if not file_name.lower().endswith('.pdf'):
        bot.send_message(chat_id, "😉 Sweetie, I need a PDF! Try again! 💕", reply_markup=main_menu())
        user_state[chat_id] = "MAIN_MENU"
        bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())
        return
    downloaded = bot.download_file(file_info.file_path)
    with open(file_name, 'wb') as f:
        f.write(downloaded)
    user_data[chat_id] = {'pdf_file': file_name}
    user_state[chat_id] = "EDIT_PDF_TEXT"
    bot.send_message(chat_id, "📝 Time to make this PDF your own! Type a cute note to add! 😘")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "EDIT_PDF_TEXT")
def edit_pdf_text(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    annotation_text = message.text
    pdf_file = user_data.get(chat_id, {}).get('pdf_file')
    if not pdf_file or not os.path.exists(pdf_file):
        bot.send_message(chat_id, "😢 Oh no, the PDF got lost! Start over, sweetie! 💕", reply_markup=main_menu())
        user_state[chat_id] = "MAIN_MENU"
        bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())
        return
    try:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.setFillColorRGB(1, 0, 0)
        c.drawString(100, 150, annotation_text)
        c.showPage()
        c.save()
        buffer.seek(0)
        annotation_pdf = PdfReader(buffer)
        reader = PdfReader(pdf_file)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.get_page(0).merge_page(annotation_pdf.pages[0])
        edited_name = pdf_file.replace('.pdf', '_edited.pdf')
        with open(edited_name, 'wb') as f:
            writer.write(f)
        with open(edited_name, 'rb') as f:
            bot.send_document(chat_id, f)
        bot.send_message(chat_id, f"🎉 Your PDF now has a cute note: '{annotation_text}'! @genius_nobita_45 made it adorable! 😘", reply_markup=main_menu())
        safe_send_sticker(chat_id)
        os.remove(edited_name)
        os.remove(pdf_file)
        del user_data[chat_id]
    except Exception as e:
        bot.send_message(chat_id, f"😢 Oh no, something broke: {e}. Let's try again! 💕", reply_markup=main_menu())
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "🌸 Back to the menu, cutie! What's next? 😊", reply_markup=main_menu())

@bot.message_handler(func=lambda message: True)
def fallback(message):
    chat_id = message.chat.id
    user_last_interaction[chat_id] = time.time()
    state = user_state.get(chat_id)
    if state is None:
        bot.send_message(chat_id, "🌟 Hiii, cutie! Type /start to begin our little adventure! 😘", reply_markup=types.ReplyKeyboardRemove())
        safe_send_sticker(chat_id)
    elif state == "MAIN_MENU":
        bot.send_message(chat_id, "😉 Sweetie, pick something from the menu! Let's make some magic! 💕", reply_markup=main_menu())
    elif state == "MORE_TOOLS":
        bot.send_message(chat_id, "😊 Cutie, choose a tool from the menu! Ready for fun? 💖", reply_markup=more_tools_menu())
    elif message.text.lower() == "exit":
        user_state[chat_id] = "MAIN_MENU"
        bot.send_message(chat_id, "🌸 Aww, taking a break? I'm right here at the main menu, cutie! 😍", reply_markup=main_menu())
        safe_send_sticker(chat_id)
    else:
        bot.send_message(chat_id, "😉 Follow the steps or type 'Exit' to go back, sweetie! I'm here for you! 💕")

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Unauthorized', 403

if __name__ == '__main__':
    bot.remove_webhook()
    webhook_url = os.environ.get('WEBHOOK_URL', 'https://your-app.onrender.com/webhook')
    bot.set_webhook(url=webhook_url)
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))