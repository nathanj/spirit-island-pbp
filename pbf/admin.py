from django.contrib import admin
from .models import *

class CardAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    search_fields = ('name',)

class GameAdmin(admin.ModelAdmin):
    search_fields = ('id', 'name')
    search_help_text = 'Search by ID or name'
    list_display = ('id', 'created_at', 'name', 'discord_channel')
    ordering = ('-created_at', )
    filter_horizontal = ('minor_deck', 'major_deck', 'discard_pile')
    def has_delete_permission(self, request, obj=None):
        return False

class GamePlayerAdmin(admin.ModelAdmin):
    search_fields = ('game__id', 'name')
    search_help_text = 'Search by game ID or player name'
    list_display = ('id', 'game', 'spirit', 'name')
    autocomplete_fields = ('hand', 'discard', 'play', 'selection', 'days')

admin.site.register(Card, CardAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(GamePlayer, GamePlayerAdmin)

