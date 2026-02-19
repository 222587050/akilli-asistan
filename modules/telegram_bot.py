async def help_command(self, update, context):
    help_text = "<b>Available Commands:</b>\n"  
    help_text += "<i>/start</i> - Start the bot\n"  
    help_text += "<i>/help</i> - Show this help message\n"  
    help_text += "<i>/other_command</i> - Description of other command\n"  
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text, parse_mode='HTML')


    
def _register_handlers(self):
    self.dispatcher.add_handler(CommandHandler("help", self.help_command))
