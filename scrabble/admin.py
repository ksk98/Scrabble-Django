from django.contrib import admin

# Register your models here.
from scrabble.models import Room, UserProfile

admin.site.register(Room)
admin.site.register(UserProfile)
