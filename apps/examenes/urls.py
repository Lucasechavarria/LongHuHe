from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_institucional, name='dashboard_institucional'),
    path('mesa/<int:mesa_id>/evaluar/', views.evaluar_mesa, name='evaluar_mesa'),
    path('mesa/<int:mesa_id>/inscribir/', views.inscribir_examen, name='inscribir_examen'),
    path('mesa/<int:mesa_id>/pago/', views.pago_examen, name='pago_examen'),
    path('pago/<int:pago_id>/comprobante/', views.pago_comprobante_examen, name='pago_comprobante_examen'),
]
