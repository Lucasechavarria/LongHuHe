from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_institucional, name='dashboard_institucional'),
    path('mesa/<int:mesa_id>/evaluar/', views.evaluar_mesa, name='evaluar_mesa'),
]
