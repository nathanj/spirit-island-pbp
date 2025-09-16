from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from pbf import views
from pbf.api import api

urlpatterns = [
    path('', include('django_prometheus.urls')),
    path('admin/', admin.site.urls),
    path("api/", api.urls),
    path('', views.home, name='home'),
    path('new', views.new_game, name='new_game'),
    path('import', views.import_game, name='import_game'),
    path('game/<str:game_id>', views.view_game, name='view_game'),
    path('game/<str:game_id>/spirit/<path:spirit_spec>', views.view_game, name='view_game'),
    path('game/<str:game_id>/setup', views.game_setup, name='game_setup'),
    path('game/<str:game_id>/logs', views.game_logs, name='game_logs'),
    path('game/<str:game_id>/screenshot', views.view_game, name='add_screenshot'),
    path('game/<str:game_id>/add-player', views.add_player, name='add_player'),
    path('game/<str:game_id>/draw', views.draw_cards, name='draw_cards'),
    path('game/<str:game_id>/tab/<int:player_id>', views.tab, name='tab'),
    path('game/<str:game_id>/minor-deck', views.minor_deck, name='minor_deck'),
    path('game/<str:game_id>/major-deck', views.major_deck, name='major_deck'),
    path('game/<str:game_id>/change_game_name', views.change_game_name, name='change_game_name'),
    path('game/<str:game_id>/change_scenario', views.change_scenario, name='change_scenario'),
    path('game/<str:game_id>/edit_players', views.edit_players, name='edit_players'),
    path('game/<str:game_id>/deck_mods', views.deck_mods, name='deck_mods'),
    path('game/<str:game_id>/deck_mod/<str:mod>', views.toggle_deck_mod, name='toggle_deck_mod'),
    path('game/<int:player_id>/gain/<str:type>/<int:num>', views.gain_power, name='gain_power'),
    path('game/<int:player_id>/gain_healing', views.gain_healing, name='gain_healing'),
    path('game/<int:player_id>/take/<str:type>/<int:num>', views.take_powers, name='take_powers'),
    path('game/<int:player_id>/choose/<int:card_id>', views.choose_card, name='choose_card'),
    path('game/<int:player_id>/send_days/<int:card_id>', views.send_days, name='send_days'),
    path('game/<int:player_id>/choose_days/<int:card_id>', views.choose_days, name='choose_days'),
    path('game/<int:player_id>/create_days/<int:num>', views.create_days, name='create_days'),
    path('game/<int:player_id>/discard-pile', views.discard_pile, name='discard_pile'),
    path('game/<int:player_id>/choose_from_discard/<int:card_id>', views.choose_from_discard, name='choose_from_discard'),
    path('game/<int:player_id>/return_to_deck/<int:card_id>', views.return_to_deck, name='return_to_deck'),
    path('game/<int:player_id>/play/<int:card_id>', views.play_card, name='play_card'),
    path('game/<int:player_id>/add_energy_to_impending/<int:card_id>', views.add_energy_to_impending, name='add_energy_to_impending'),
    path('game/<int:player_id>/remove_energy_from_impending/<int:card_id>', views.remove_energy_from_impending, name='remove_energy_from_impending'),
    path('game/<int:player_id>/play_from_impending/<int:card_id>', views.play_from_impending, name='play_from_impending'),
    path('game/<int:player_id>/unplay_from_impending/<int:card_id>', views.unplay_from_impending, name='unplay_from_impending'),
    path('game/<int:player_id>/gain_energy_on_impending', views.gain_energy_on_impending, name='gain_energy_on_impending'),
    path('game/<int:player_id>/impend/<int:card_id>', views.impend_card, name='impend_card'),
    path('game/<int:player_id>/unimpend/<int:card_id>', views.unimpend_card, name='unimpend_card'),
    path('game/<int:player_id>/unplay/<int:card_id>', views.unplay_card, name='unplay_card'),
    path('game/<int:player_id>/forget/<int:card_id>', views.forget_card, name='forget_card'),
    path('game/<int:player_id>/reclaim/<int:card_id>', views.reclaim_card, name='reclaim_card'),
    path('game/<int:player_id>/reclaim/all', views.reclaim_all, name='reclaim_all'),
    path('game/<int:player_id>/reclaim/all/<str:element>', views.reclaim_all, name='reclaim_all'),
    path('game/<int:player_id>/discard/all', views.discard_all, name='discard_all'),
    path('game/<int:player_id>/discard/<int:card_id>', views.discard_card, name='discard_card'),
    path('game/<int:player_id>/energy/pay', views.pay_energy, name='pay_energy'),
    path('game/<int:player_id>/energy/gain', views.gain_energy, name='gain_energy'),
    path('game/<int:player_id>/energy/<str:amount>', views.change_energy, name='change_energy'),
    path('game/<int:player_id>/bargain_cost/<str:amount>', views.change_bargain_cost_per_turn, name='change_bargain_cost_per_turn'),
    path('game/<int:player_id>/bargain_pay/<str:amount>', views.change_bargain_paid_this_turn, name='change_bargain_paid_this_turn'),
    path('game/<int:player_id>/spirit_specific_resource/<str:amount>', views.change_spirit_specific_resource, name='change_spirit_specific_resource'),
    path('game/<int:player_id>/rot/gain', views.gain_rot, name='gain_rot'),
    path('game/<int:player_id>/rot/convert', views.convert_rot, name='convert_rot'),
    path('game/<int:player_id>/presence/<int:left>/<int:top>', views.toggle_presence, name='toggle_presence'),
    path('game/<int:player_id>/undo-gain-card', views.undo_gain_card, name='undo_gain_card'),
    path('game/<int:player_id>/ready', views.ready, name='ready'),
    path('game/<int:player_id>/element/<str:element>/add', views.add_element, name='add_element'),
    path('game/<int:player_id>/element/<str:element>/remove', views.remove_element, name='remove_element'),
    path('game/<int:player_id>/element-permanent/<str:element>/add', views.add_element_permanent, name='add_element_permanent'),
    path('game/<int:player_id>/element-permanent/<str:element>/remove', views.remove_element_permanent, name='remove_element_permanent'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += [
        path('screenshot/<str:filename>', views.view_screenshot, name='view_screenshot'),
        path('screenshot/<str:game_id>/<str:filename>', views.view_screenshot, name='view_screenshot'),
    ]
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns += [
            path('__debug__/', include('debug_toolbar.urls')),
        ]
