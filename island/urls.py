from django.contrib import admin
from django.urls import include, path
from pbf import views
from pbf.api import api

urlpatterns = [
    path('__debug__/', include('debug_toolbar.urls')),
    path('admin/', admin.site.urls),
    path("api/", api.urls),
    path('', views.home, name='home'),
    path('screenshot/<str:filename>', views.view_screenshot, name='view_screenshot'),
    path('new', views.new_game, name='new_game'),
    path('game/<str:game_id>', views.view_game, name='view_game'),
    path('game/<str:game_id>/logs', views.game_logs, name='game_logs'),
    path('game/<str:game_id>/unready', views.unready, name='unready'),
    path('game/<str:game_id>/time-passes', views.time_passes, name='time_passes'),
    path('game/<str:game_id>/screenshot', views.view_game, name='add_screenshot'),
    path('game/<str:game_id>/add-player', views.add_player, name='add_player'),
    path('game/<str:game_id>/draw/<str:type>', views.draw_card, name='draw_card'),
    path('game/<str:game_id>/tab/<int:player_id>', views.tab, name='tab'),
    path('game/<int:player_id>/gain/<str:type>/<int:num>', views.gain_power, name='gain_power'),
    path('game/<int:player_id>/choose/<int:card_id>', views.choose_card, name='choose_card'),
    path('game/<int:player_id>/choose2/<int:card_id>', views.choose_card2, name='choose_card2'),
    path('game/<int:player_id>/play/<int:card_id>', views.play_card, name='play_card'),
    path('game/<int:player_id>/unplay/<int:card_id>', views.unplay_card, name='unplay_card'),
    path('game/<int:player_id>/forget/<int:card_id>', views.forget_card, name='forget_card'),
    path('game/<int:player_id>/reclaim/<int:card_id>', views.reclaim_card, name='reclaim_card'),
    path('game/<int:player_id>/reclaim/all', views.reclaim_all, name='reclaim_all'),
    path('game/<int:player_id>/discard/<int:card_id>', views.discard_card, name='discard_card'),
    path('game/<int:player_id>/energy/<str:amount>', views.change_energy, name='change_energy'),
    path('game/<int:player_id>/presence', views.toggle_presence, name='toggle_presence'),
    path('game/<int:player_id>/ready', views.ready, name='ready'),
    path('game/<int:player_id>/notes', views.notes, name='notes'),
]
