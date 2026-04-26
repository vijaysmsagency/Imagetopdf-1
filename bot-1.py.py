import os
from PIL import Image
import img2pdf
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# Constants for Conversation states
PHOTO, CONVERT = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Create a temporary folder for the user's images
    user_id = update.message.from_user.id
    if not os.path.exists(str(user_id)):
        os.makedirs(str(user_id))
    
    await update.message.reply_text(
        "Hi! Send me the images you want to convert to PDF one by one.\n"
        "When you're done, type /done or click the button below.",
        reply_markup=ReplyKeyboardMarkup([['/done']], one_time_keyboard=True)
    )
    # Clear any old images from previous sessions
    context.user_data['images'] = []
    return PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo_file = await update.message.photo[-1].get_file()
    
    # Save image with a unique name
    img_path = f"{user_id}/img_{len(context.user_data['images'])}.jpg"
    await photo_file.download_to_drive(img_path)
    
    # Optional: Compress image using Pillow immediately
    with Image.open(img_path) as img:
        img = img.convert("RGB")
        # Reducing quality to 70% to save space
        img.save(img_path, "JPEG", quality=70, optimize=True)
        
    context.user_data['images'].append(img_path)
    await update.message.reply_text(f"Image {len(context.user_data['images'])} received!")
    return PHOTO

async def convert_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    images = context.user_data.get('images', [])
    
    if not images:
        await update.message.reply_text("You haven't sent any images yet!")
        return PHOTO

    await update.message.reply_text("Converting to PDF... please wait.", reply_markup=ReplyKeyboardRemove())
    
    pdf_path = f"{user_id}/output.pdf"
    
    # Convert images to PDF bytes using img2pdf
    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert(images))
    
    # Send the PDF to the user
    await update.message.reply_document(document=open(pdf_path, 'rb'), filename="converted.pdf")
    
    # Cleanup: Delete images and the PDF file
    for img in images:
        os.remove(img)
    os.remove(pdf_path)
    os.rmdir(str(user_id))
    
    context.user_data['images'] = []
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == '__main__':
    # Replace 'YOUR_TOKEN_HERE' with your actual BotFather token
    app = ApplicationBuilder().token("YOUR_TOKEN_HERE").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler('done', convert_to_pdf)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(conv_handler)
    print("Bot is running...")
    app.run_polling()