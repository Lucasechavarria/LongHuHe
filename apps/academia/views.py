from django.shortcuts import render, redirect, get_object_or_404
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
    
    clases = Cronograma.objects.all().select_related('actividad', 'profesor', 'sede')
    
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
    Lógica de inscripción: verifica cupo y gestiona lista de espera.
    """
    clase = get_object_or_404(Cronograma, id=clase_id)
    alumno_id = request.session['alumno_id']
    
    # 1. Verificar si ya está inscrito
    if InscripcionClase.objects.filter(alumno_id=alumno_id, clase=clase).exclude(estado='baja').exists():
        messages.info(request, "Ya estás anotado en este horario.")
        return redirect('lista_clases')

    # 2. Contar inscriptos regulares
    inscriptos_actuales = InscripcionClase.objects.filter(clase=clase, estado='regular').count()
    
    if inscriptos_actuales < clase.cupo:
        estado = InscripcionClase.EstadoInscrito.REGULAR
        messages.success(request, f"¡Excelente! Te has inscrito en {clase.actividad.nombre}.")
    else:
        estado = InscripcionClase.EstadoInscrito.ESPERA
        messages.warning(request, "El cupo está completo. Has sido agregado a la lista de espera.")

    # 3. Crear inscripción
    InscripcionClase.objects.update_or_create(
        alumno_id=alumno_id,
        clase=clase,
        defaults={'estado': estado}
    )
    
    return redirect('lista_clases')

@alumno_requerido
def desanotarse_clase(request, clase_id):
    """
    Permite al alumno bajarse de una clase y libera cupo para alguien en espera.
    """
    inscripcion = get_object_or_404(InscripcionClase, alumno_id=request.session['alumno_id'], clase_id=clase_id)
    
    if inscripcion.estado == 'regular':
        # Liberar cupo: buscar el primero en espera
        proximo_en_espera = InscripcionClase.objects.filter(clase=inscripcion.clase, estado='espera').order_by('fecha_inscripcion').first()
        if proximo_en_espera:
            proximo_en_espera.estado = 'regular'
            proximo_en_espera.save()
            # Aquí se podría disparar una notificación

    inscripcion.estado = 'baja'
    inscripcion.save()
    messages.info(request, "Te has dado de baja de la clase.")
    return redirect('lista_clases')
