from django.shortcuts import render, redirect
from django.contrib import messages
from apps.usuarios.views import alumno_requerido
from .models import Cronograma, InscripcionClase, Sede, Actividad
from apps.usuarios.models import Usuario


@alumno_requerido
def lista_clases(request):
    """
    Muestra la grilla semanal global o filtrada dinámicamente.
    """
    sedes = Sede.objects.all()
    actividades = Actividad.objects.all()
    profesores = Usuario.objects.filter(es_profe=True).order_by('nombre')
    
    sede_id = request.GET.get('sede')
    actividad_id = request.GET.get('actividad')
    profesor_id = request.GET.get('profesor')
    
    clases = Cronograma.objects.all().select_related('actividad', 'profesor', 'sede').order_by('hora_inicio')
    
    if sede_id:
        clases = clases.filter(sede_id=sede_id)
    if actividad_id:
        clases = clases.filter(actividad_id=actividad_id)
    if profesor_id:
        clases = clases.filter(profesor_id=profesor_id)

    # Agrupamos por día para facilitar el renderizado en la grilla
    clases_por_dia = {dia[0]: [] for dia in Cronograma.DiasSemana.choices}
    for clase in clases:
        clases_por_dia[clase.dia].append(clase)

    # Verificamos inscripciones actuales del usuario para marcar en el template
    mis_clases_ids = InscripcionClase.objects.filter(
        alumno_id=request.session['alumno_id'],
        estado__in=['regular', 'espera']
    ).values_list('clase_id', flat=True)

    return render(request, 'academia/cronograma.html', {
        'sedes': sedes,
        'actividades': actividades,
        'profesores': profesores,
        'sede_seleccionada': int(sede_id) if sede_id else '',
        'actividad_seleccionada': int(actividad_id) if actividad_id else '',
        'profesor_seleccionado': int(profesor_id) if profesor_id else '',
        'clases_por_dia': clases_por_dia,
        'mis_clases_ids': list(mis_clases_ids),
        'dias_semana': Cronograma.DiasSemana.choices
    })



@alumno_requerido
def inscribir_clase(request, clase_id):
    """
    Lógica de inscripción delegada al AcademiaService.
    """
    alumno_id = request.session['alumno_id']
    alumno = Usuario.objects.get(id=alumno_id)
    
    from .services import AcademiaService
    inscripcion, mensaje, exito = AcademiaService.inscribir_alumno(alumno, clase_id)
    
    if exito:
        if inscripcion.estado == 'regular':
            messages.success(request, mensaje)
        else:
            messages.warning(request, mensaje)
    else:
        messages.warning(request, f"⚠️ {mensaje}")

    return redirect('lista_clases')

@alumno_requerido
def desanotarse_clase(request, clase_id):
    """
    Lógica de baja delegada al AcademiaService.
    """
    alumno_id = request.session['alumno_id']
    alumno = Usuario.objects.get(id=alumno_id)
    
    from .services import AcademiaService
    exito, mensaje = AcademiaService.dar_de_baja(alumno, clase_id)
    
    if exito:
        messages.success(request, f"✅ {mensaje}")
    else:
        messages.warning(request, mensaje)
        
    return redirect('lista_clases')
