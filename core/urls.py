from django.urls import path
from . import views

urlpatterns = [
    path('', views.splash, name='splash'),
    path('acceso/', views.acceso_opciones, name='acceso_opciones'),
    path('ingresar/', views.identificacion, name='identificacion'),
    path('dashboard/', views.inicio, name='inicio'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('asistencia/registrar/', views.registrar_asistencia, name='registrar_asistencia'),
    path('pago/tipo/', views.pago_tipo, name='pago_tipo'),
    path('pago/metodo/', views.pago_metodo, name='pago_metodo'),
    path('pago/comprobante/', views.pago_comprobante, name='pago_comprobante'),
    path('pago/confirmacion/', views.pago_confirmacion, name='pago_confirmacion'),
    path('pago/mercadopago/<int:pago_id>/', views.pago_mercadopago_checkout, name='pago_mercadopago_checkout'), # Checkout automático
    path('mercadopago/webhook/', views.mercadopago_webhook, name='mercadopago_webhook'), # Webhook
    path('gracias/', views.gracias, name='gracias'),
]
