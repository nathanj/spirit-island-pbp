from django.contrib import admin
from .models import *

class SpiritAdmin(admin.ModelAdmin):
    pass
class CardAdmin(admin.ModelAdmin):
    search_fields = ('name',)
class GameAdmin(admin.ModelAdmin):
    pass
class GamePlayerAdmin(admin.ModelAdmin):
    autocomplete_fields = ('hand', 'discard', 'play', 'selection')

admin.site.register(Card, CardAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(GamePlayer, GamePlayerAdmin)

