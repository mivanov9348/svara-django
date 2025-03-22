from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('start/', views.start_game, name='start_game'),
    path('game/<int:game_id>/', views.game_view, name='game_view'),
]