from datetime import timedelta
from telegram import Update
from telegram import Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import json
from healthChecker import HealthChecker


class MyBot:
    def __init__(self, settings):
        self.settings = settings
        self.token = self.settings['bot-token']
        self.application = ApplicationBuilder().token(self.token).build()
        self.subscribers = set()
        self.bot = Bot(self.token)
        with open('subscribers.json') as f:
            self.subscribers = set(json.loads(' '.join(f.readlines())))
        self.healthChecker = HealthChecker()


        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('subscribe', self.subscribe))
        self.application.add_handler(CommandHandler('unsubscribe', self.unsubscribe))
        self.application.add_handler(CommandHandler('status', self.status))
        self.application.add_handler(CommandHandler('details', self.details))

        self.application.job_queue.run_repeating(callback=lambda x: self.notify(), interval=timedelta(seconds=60))



    def run(self):
        self.application.run_polling()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

    async def subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        id = update.effective_chat.id
        if id not in self.subscribers:
            self.subscribers.add(id)
        with open('subscribers.json', 'w') as f:
            f.write(json.dumps(list(self.subscribers)))
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You have been subscribed")

    async def unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        id = update.effective_chat.id
        if id in self.subscribers:
            self.subscribers.remove(id)
        with open('subscribers.json', 'w') as f:
            f.write(json.dumps(list(self.subscribers)))
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You have been unsubscribed")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.healthChecker.ping()
        statuses = await self.healthChecker.get_statuses()

        if statuses:
            msg = ""
            for stat in statuses:
                msg += "\n"
                if stat.is_up:
                    msg += "✔️ "
                else:
                    msg += "❌ "
                msg += stat.config.name
            msg = msg[1:]
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No services registered")

    async def details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.healthChecker.ping()
        statuses = await self.healthChecker.get_statuses()

        if statuses:
            msg = ""
            for stat in statuses:
                msg += "\n"
                if stat.is_up:
                    msg += "✔️ "
                    msg += stat.config.name
                else:
                    msg += "❌ "
                    msg += stat.config.name + ":"
                    if stat.errors:
                        msg += ''.join(['\n\t\t' + i for i in stat.errors])
                    else:
                        msg += '\nNo errors.'
            msg = msg[1:]
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No services registered")

    async def notify(self):
        await self.healthChecker.ping()
        errors = await self.healthChecker.get_errors()
        if errors:
            for subscriber in self.subscribers:
                await self.bot.send_message(chat_id=subscriber, text=errors)


def main():
    settings = None
    with open('settings.json') as f:
        settings = json.loads(' '.join(f.readlines()))
    MyBot(settings).run()

if __name__ == "__main__":
    main()
