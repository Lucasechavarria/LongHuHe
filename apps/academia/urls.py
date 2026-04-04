from django.urls import path
from . import views

urlpatterns = [
    path('clases/', views.lista_clases, name='lista_clases'),
    path('clases/inscribir/<int:clase_id>/', views.inscribir_clase, name='inscribir_clase'),
    path('clases/desanotarse/<int:clase_id>/', views.desanotarse_clase, name='desanotarse_clase'),
]
