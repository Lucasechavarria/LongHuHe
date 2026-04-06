from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from apps.usuarios.views import alumno_requerido, profe_requerido
from apps.usuarios.models import Usuario
from apps.biblioteca.models import CategoriaContenido, MaterialEstudio, VisualizacionMaterial
from django.db.models import Count

@alumno_requerido
def biblioteca_inicio(request):
    """ Portal principal de la biblioteca (Task 6.3) """
    # En este proyecto usamos la ID del alumno en sesion si no esta logueado como superuser
    alumno_id = request.session.get('alumno_id')
    alumno = get_object_or_404(Usuario, id=alumno_id)
    grado_alumno = alumno.grado
    
    # Solo materiales cuyo grado_minimo.orden sea <= al grado del alumno.orden
    if not grado_alumno:
        materiales = MaterialEstudio.objects.none()
    else:
        materiales = MaterialEstudio.objects.filter(
            grado_minimo__orden__lte=grado_alumno.orden,
            activo=True
        ).select_related('categoria', 'grado_minimo')

    categorias = CategoriaContenido.objects.annotate(count=Count('materiales')).filter(count__gt=0)
    
    return render(request, 'biblioteca/explorar.html', {
        'materiales': materiales,
        'categorias': categorias,
        'grado_alumno': grado_alumno,
        'alumno_actual': alumno
    })

@alumno_requerido
def material_detalle(request, material_id):
    """ Vista detallada del material y tracking (Task 6.4) """
    alumno_id = request.session.get('alumno_id')
    alumno = get_object_or_404(Usuario, id=alumno_id)
    material = get_object_or_404(MaterialEstudio, id=material_id, activo=True)
    
    # Validar acceso por grado (Task 6.1)
    if not alumno.grado or material.grado_minimo.orden > alumno.grado.orden:
        messages.error(request, "Aún no tienes el grado necesario para ver este material.")
        return redirect('biblioteca_inicio')
    
    # Registrar visualización (Tracking Task 6.4)
    # Corrección Bug N°2: Evitar Crash de repetición con get_or_create
    VisualizacionMaterial.registrar_vista(
        alumno=alumno,
        material=material
    )
    
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
