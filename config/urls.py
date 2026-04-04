"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.admin_site.urls if hasattr(admin.site, 'admin_site') else admin.site.urls),
    path('', include('apps.usuarios.urls')),
    path('clases/', include('apps.academia.urls')),
    path('usuarios/', include('apps.usuarios.urls')),
    path('asistencia/', include('apps.asistencia.urls')),
    path('pagos/', include('apps.ventas.urls')),
    path('biblioteca/', include('apps.biblioteca.urls')),
    path('examenes/', include('apps.examenes.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
