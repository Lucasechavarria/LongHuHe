from django.urls import path
from . import views

urlpatterns = [
    path('', views.biblioteca_inicio, name='biblioteca_inicio'),
    path('material/<int:material_id>/', views.material_detalle, name='material_detalle'),
    path('gestion/', views.gestion_biblioteca, name='gestion_biblioteca'),
]
