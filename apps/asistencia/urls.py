from django.urls import path
from . import views

urlpatterns = [
    path('escaner/', views.escaner, name='escaner'),
    path('api/registrar-qr/', views.registrar_asistencia_qr, name='registrar_asistencia_qr'),
]
