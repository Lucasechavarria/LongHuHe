from django.urls import path
from . import views

urlpatterns = [
    path('escaner/', views.escaner, name='escaner'),
    path('api/registrar-qr/', views.registrar_asistencia_qr, name='registrar_asistencia_qr'),
    path('api/cobrar-efectivo/', views.api_registrar_pago_efectivo_scanner, name='api_registrar_pago_efectivo_scanner'),
    path('api/otorgar-prorroga/', views.api_otorgar_prorroga_scanner, name='api_otorgar_prorroga_scanner'),
    path('api/forzar-ingreso/', views.api_forzar_ingreso_scanner, name='api_forzar_ingreso_scanner'),
]
