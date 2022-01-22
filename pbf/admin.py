from django.contrib import admin
from .models import *

class SpiritAdmin(admin.ModelAdmin):
    pass
class CardAdmin(admin.ModelAdmin):
    pass
class GameAdmin(admin.ModelAdmin):
    pass
class GamePlayerAdmin(admin.ModelAdmin):
    pass
admin.site.register(Spirit, SpiritAdmin)
admin.site.register(Card, CardAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(GamePlayer, GamePlayerAdmin)
