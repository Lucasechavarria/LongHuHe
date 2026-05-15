from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_institucional, name='dashboard_institucional'),
    path('mesa/nueva/', views.crear_mesa_examen, name='crear_mesa_examen'),
    path('mesa/<int:mesa_id>/evaluar/', views.evaluar_mesa, name='evaluar_mesa'),
    path('mesa/<int:mesa_id>/inscribir-manual/', views.inscribir_alumno_mesa_manual, name='inscribir_alumno_mesa_manual'),
    path('mesa/<int:mesa_id>/inscribir/', views.inscribir_examen, name='inscribir_examen'),
    path('mesa/<int:mesa_id>/pago/', views.pago_examen, name='pago_examen'),
    path('pago/<int:pago_id>/comprobante/', views.pago_comprobante_examen, name='pago_comprobante_examen'),
]
