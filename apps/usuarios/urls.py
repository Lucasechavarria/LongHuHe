from django.urls import path
from . import views

urlpatterns = [
    path('', views.splash, name='splash'),
    path('acceso/', views.acceso_opciones, name='acceso_opciones'),
    path('ingresar/', views.identificacion, name='identificacion'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('logout/', views.logout, name='logout'),
]
