import openai
import os
from telegram import Update
import os
from telegram.ext import (ApplicationBuilder, 
                          CommandHandler, 
                          ContextTypes, 
                          MessageHandler, 
                          filters 
                          
                          )
from telegram.constants import ChatAction
from functools import wraps

#from pydub import AudioSegment



my_token = os.getenv('TELEGRAM_TOKEN')
openai.organization = os.getenv('OPENAI_ORG')
openai.api_key = os.getenv('OPENAI_KEY')
authorized_users = os.getenv('users')

names_list = authorized_users.split(',')
user_list = [name.strip() for name in names_list]

logs = {}
counter = {}
counter_limit = {}
for user_name in user_list:
    
    logs[user_name] = str()
    counter[user_name] = 0
    counter_limit[user_name] = 10

def send_message(message):
    """Send a message to Chat-GPT for completion

        This is the basic functionality that sends a message to Chat-GPT and 
        expects a response to start a new conversation

        Args:
            message (srt): The message to send

        Returns:
            str: The completion message returned by Chat-GPT
    """
    response = openai.ChatCompletion.create(
        #model="gpt-4",
        model="gpt-3.5-turbo",
        temperature=0.6,
        messages=[
            {"role": "user", "content": message}
        ]
    )
    return response['choices'][0]['message']['content']


def fix_spelling_mistakes(text):
        """Fix spelling mistakes

            This function receives a text with gramatical errors and returns the same text but corrected

            Args:
                text (str): The input text to be corrected

            Returns:
                str: The corrected text
        """
        result = openai.Edit.create(
            model="text-davinci-edit-001",
            input=text,
            instruction="Fix the spelling mistakes"
        )
        return result['choices'][0]['text']

def translate_audio(audio_file):
        """Translates a voice message to english

            This function receives an audio file in any language and translates it into english

            Args:
                audio_file (File): The audio file that has to be translated

            Returns:
                str: The text message translated from the voice message
        """
        translation = openai.Audio.translate("whisper-1", audio_file)
        return translation['text']

def generate_image_from_text(message):
        """Generates a picture based on a text

            This uses OpenAI integration with Dall-E to generate a picture
            based on the description used as input

            Args:
                message (str): The message to generate a picture from

            Returns:
                str: The url of picture generated
        """
        response = openai.Image.create(
            prompt=message,
            n=1,
            size="512x512",
        )
        return (response['data'][0].url)

#Дальше идет бот


def send_action(action):
    """Sends typing action while processing func command."""
    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return await func(update, context,  *args, **kwargs)
        return command_func

    return decorator

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await context.bot.send_message(chat_id=update.effective_chat.id, 
                                   text=f"""Привет {user.first_name}, это персональный бот на основе Chat GPT! \n\n
Просто введи сообщение, чтобы получить ответ от GPT 3,5\n
Генерация  фото - /generate_image описание фото, которое тебе нужно\n
Проверка англ - /fix_spelling твой текст
                                    """)
@send_action(ChatAction.TYPING)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user = update.message.from_user.username
    if update.message.from_user.username in user_list:
        if counter[user] < counter_limit[user]:
            logs[user] += ('-'+user_message +f'\n')
            counter[user] += 1
            response = send_message(message=logs[user])
            logs[user] += ('-'+response +f'\n')
        else: 
            logs[user] = ('-'+user_message +f'\n')
            counter[user] = 0
            response = send_message(message=logs[user])
            logs[user] += ('-'+response +f'\n')
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    
    else:
        response_failed = '''
        Вы не авторизованы :( 
        Обратитесь к администратору.
        '''
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response_failed)
        
@send_action(ChatAction.UPLOAD_PHOTO)
async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.from_user.username in user_list:
            text = ' '.join(context.args)
            img_url = generate_image_from_text(message=text)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_url)

        else:
                response_failed = '''
                Вы не авторизованы :( 
                Обратитесь к администратору.
                '''
                await context.bot.send_message(chat_id=update.effective_chat.id, text=response_failed)

@send_action(ChatAction.TYPING)
async def fix_spelling(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = ' '.join(context.args)
        response = fix_spelling_mistakes(text=text)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# Обновить историю, которую видит бот
async def refresh_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.message.from_user.username
        counter[user] = 0
        logs[user] = ''
        await context.bot.send_message(chat_id=update.effective_chat.id, 
                                       text=f'Количество последних сообщений: {counter[user]}')

# установить счетчик пар сообщение пользователя+ответ, которые видит бот
async def set_counter(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.message.from_user.username
        value = int(context.args[0]) - 1
        counter_limit[user] = value
        
        await context.bot.send_message(chat_id=update.effective_chat.id, 
                                       text=f'Количество сообщений, которые помнит бот: {counter_limit[user]+1}')

if __name__ == '__main__':
    application = ApplicationBuilder().token(my_token).build()
    
    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, echo)


    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(CommandHandler(
            'generate_image', generate_image))
    application.add_handler(CommandHandler(
            'fix_spelling', fix_spelling))
    application.add_handler(CommandHandler(
            'refresh_prompt', refresh_prompt))
    application.add_handler(CommandHandler(
            'set_counter', set_counter))
        
    application.run_polling()


