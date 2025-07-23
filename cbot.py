import asyncio
import sys
import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, CommandHandler, filters

# Windows compatibility
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

print("Bot starting up...")

# Load environment variables
load_dotenv()

# Fetch API keys
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Verify tokens are loaded
print(f"Cohere API Key loaded: {bool(COHERE_API_KEY)}")
print(f"Telegram Bot Token loaded: {bool(TELEGRAM_BOT_TOKEN)}")

if not COHERE_API_KEY or not TELEGRAM_BOT_TOKEN:
    print("ERROR: Missing API keys! Please check your .env file.")
    sys.exit(1)

# Debug: Show first/last few characters of API key (for verification)
if COHERE_API_KEY:
    masked_key = COHERE_API_KEY[:8] + "..." + COHERE_API_KEY[-8:] if len(COHERE_API_KEY) > 16 else "***"
    print(f"Cohere API Key preview: {masked_key}")
else:
    print("WARNING: Cohere API Key is empty!")

# Function to get response from Cohere API
def get_cohere_response(user_input: str) -> str:
    url = "https://api.cohere.ai/v1/generate"
    headers = {
        "Authorization": f"Bearer {COHERE_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "command",
        "prompt": user_input,
        "max_tokens": 150,
        "temperature": 0.7
    }

    try:
        print(f"Making request to Cohere API...")
        response = requests.post(url, headers=headers, json=data, timeout=15)
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 401:
            print("ERROR: 401 Unauthorized - Check your Cohere API key!")
            print("Make sure your API key is valid and has the correct permissions.")
            return "❌ **API Key Error**: Your Cohere API key appears to be invalid or expired. Please check your API key in the .env file."
        
        if response.status_code == 429:
            print("ERROR: 429 Rate Limited")
            return "⏳ **Rate Limited**: Too many requests. Please wait a moment and try again."
        
        response.raise_for_status()
        result = response.json()
        
        if "generations" in result and len(result["generations"]) > 0:
            generated_text = result["generations"][0]["text"].strip()
            print(f"Successfully received response from Cohere (length: {len(generated_text)})")
            return generated_text
        else:
            print("ERROR: Unexpected response structure from Cohere")
            print(f"Response: {result}")
            return "⚠️ Error: Cohere response is missing expected data."
            
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out")
        return "⏳ **Timeout Error**: Request took too long. Please try again."
    except requests.exceptions.ConnectionError:
        print("ERROR: Connection failed")
        return "🌐 **Connection Error**: Could not connect to Cohere API. Check your internet connection."
    except requests.exceptions.RequestException as req_err:
        print(f"ERROR: Request failed: {req_err}")
        if hasattr(req_err.response, 'text'):
            print(f"Error response: {req_err.response.text}")
        return f"⚠️ **API Error**: {str(req_err)}"
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return "⚠️ An unexpected error occurred while generating a response."

# Start command handler
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "🤖 Hello! I'm your Cohere AI bot.\n\n"
        "Send me any message and I'll respond using AI!\n"
        "Just type your question or message below."
    )
    await update.message.reply_text(welcome_message)
    print(f"Start command sent to user {update.effective_user.id}")

# Help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "ℹ️ How to use this bot:\n\n"
        "• Just send me any text message\n"
        "• I'll use Cohere AI to generate a response\n"
        "• Use /start to see the welcome message\n"
        "• Use /help to see this help message"
    )
    await update.message.reply_text(help_message)

# Message handler function
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_message = update.message.text
        chat_id = update.message.chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        print(f"Received message from {username} ({user_id}): {user_message}")
        
        # Send typing action
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        # Get response from Cohere
        response = get_cohere_response(user_message)
        print(f"Cohere response: {response[:100]}...")  # Log first 100 chars
        
        # Send response
        await context.bot.send_message(chat_id=chat_id, text=response)
        
    except Exception as e:
        print(f"Error handling message: {e}")
        error_message = "⚠️ An error occurred while processing your message. Please try again."
        await context.bot.send_message(chat_id=chat_id, text=error_message)

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")

# Main function - simplified for Windows
def main():
    print("Building application...")
    
    # Create application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    print("Bot is running and ready to receive messages...")
    print("Press Ctrl+C to stop the bot")
    
    # Start polling - this handles the event loop automatically
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        main()  # Call main directly - no asyncio.run needed
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")