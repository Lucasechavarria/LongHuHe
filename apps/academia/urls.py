from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_clases, name='lista_clases'),
    path('inscribir/<int:clase_id>/', views.inscribir_clase, name='inscribir_clase'),
    path('desanotarse/<int:clase_id>/', views.desanotarse_clase, name='desanotarse_clase'),
]
