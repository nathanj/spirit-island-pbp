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
    list_display = ('id', 'created_at', 'name', 'scenario', 'discord_channel')
    ordering = ('-created_at', )
    filter_horizontal = ('minor_deck', 'major_deck', 'discard_pile')
    def has_delete_permission(self, request, obj=None):
        return False

class GamePlayerAdmin(admin.ModelAdmin):
    search_fields = ('game__id', 'name')
    search_help_text = 'Search by game ID or player name'
    list_display = ('id', 'game', 'spirit__name', 'aspect', 'name')
    # Changing spirit doesn't change their hand or presence.
    # Doing so via admin interface is not an operation we should offer,
    # as offering it is an implicit promise that it works.
    readonly_fields = ('spirit', )
    autocomplete_fields = ('hand', 'discard', 'play', 'selection', 'days')

    # Some fields are specific to one spirit and don't do anything for others.
    # Don't display them, to avoid clutter and data that doesn't make sense.
    def get_exclude(self, request, obj=None):
        excludes = []
        if not obj or obj.spirit.name != 'Waters':
            excludes.append('healing')
        if not obj or obj.spirit.name != 'Fractured':
            excludes.append('days')
        return excludes

    filter_horizontal = ('healing', )
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'healing':
            kwargs['queryset'] = Card.objects.filter(name__in=Card.HEALING_NAMES)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

admin.site.register(Card, CardAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(GamePlayer, GamePlayerAdmin)

