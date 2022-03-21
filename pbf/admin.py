from django.contrib import admin
from .models import *

class CardAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    search_fields = ('name',)

class GameAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False

class GamePlayerAdmin(admin.ModelAdmin):
    autocomplete_fields = ('hand', 'discard', 'play', 'selection', 'days')

admin.site.register(Card, CardAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(GamePlayer, GamePlayerAdmin)

