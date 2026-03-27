from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('asistencia/registrar/', views.registrar_asistencia, name='registrar_asistencia'),
    path('pago/tipo/', views.pago_tipo, name='pago_tipo'),
    path('pago/metodo/', views.pago_metodo, name='pago_metodo'),
    path('pago/comprobante/', views.pago_comprobante, name='pago_comprobante'),
    path('pago/confirmacion/', views.pago_confirmacion, name='pago_confirmacion'),
    path('gracias/', views.gracias, name='gracias'),
]
