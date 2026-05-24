from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_clases, name='lista_clases'),
    path('inscribir/<int:clase_id>/', views.inscribir_clase, name='inscribir_clase'),
    path('desanotarse/<int:clase_id>/', views.desanotarse_clase, name='desanotarse_clase'),
    
    # Alumnos - Torneos
    path('torneos/', views.lista_torneos, name='lista_torneos'),
    path('torneos/<int:torneo_id>/inscribir/', views.inscribir_torneo, name='inscribir_torneo'),
    path('torneos/<int:torneo_id>/desanotarse/', views.desanotarse_torneo, name='desanotarse_torneo'),
    
    # Profesores - CRUD Torneos
    path('torneos/gestion/', views.gestion_torneos, name='gestion_torneos'),
    path('torneos/crear/', views.crear_torneo, name='crear_torneo'),
    path('torneos/<int:torneo_id>/editar/', views.editar_torneo, name='editar_torneo'),
    path('torneos/<int:torneo_id>/eliminar/', views.eliminar_torneo, name='eliminar_torneo'),
    path('torneos/<int:torneo_id>/inscritos/', views.ver_inscritos_torneo, name='ver_inscritos_torneo'),
    path('torneos/<int:torneo_id>/resultados/', views.registrar_resultados_torneo, name='registrar_resultados_torneo'),
]
