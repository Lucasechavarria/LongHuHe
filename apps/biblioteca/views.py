from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from apps.usuarios.views import alumno_requerido, profe_requerido
from apps.usuarios.models import Usuario
from apps.biblioteca.models import CategoriaContenido, MaterialEstudio
from django.db.models import Count

@alumno_requerido
def biblioteca_inicio(request):
    """ Portal principal de la biblioteca usando BibliotecaService. """
    alumno_id = request.session.get('alumno_id')
    alumno = get_object_or_404(Usuario, id=alumno_id)
    
    from .services import BibliotecaService
    materiales = BibliotecaService.obtener_materiales_para_alumno(alumno)
    categorias = CategoriaContenido.objects.annotate(count=Count('materiales')).filter(count__gt=0)
    
    return render(request, 'biblioteca/explorar.html', {
        'materiales': materiales,
        'categorias': categorias,
        'grado_alumno': alumno.grado,
        'alumno_actual': alumno
    })

@alumno_requerido
def material_detalle(request, material_id):
    """ Vista detallada con tracking vía BibliotecaService. """
    alumno_id = request.session.get('alumno_id')
    alumno = get_object_or_404(Usuario, id=alumno_id)
    material = get_object_or_404(MaterialEstudio, id=material_id, activo=True)
    
    # Validar acceso por grado
    if not alumno.grado or material.grado_minimo.orden > alumno.grado.orden:
        messages.error(request, "Aún no tienes el grado necesario para ver este material.")
        return redirect('biblioteca_inicio')
    
    from .services import BibliotecaService
    BibliotecaService.registrar_visualizacion(alumno, material)
    
    return render(request, 'biblioteca/detalle.html', {
        'material': material,
        'alumno_actual': alumno
    })

@profe_requerido
def gestion_biblioteca(request):
    """ Panel de carga para Maestros (Task 6.2) """
    from django.db.models import Count
    materiales = MaterialEstudio.objects.annotate(
        vistas_count=Count('visualizaciones')
    ).all().order_by('-vistas_count')
    
    return render(request, 'biblioteca/gestion.html', {
        'materiales': materiales
    })
