from django.contrib import admin

from .models import Message, MessagingSettings

admin.site.register(Message)
admin.site.register(MessagingSettings)
