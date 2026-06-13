from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.usuarios.views import alumno_requerido, profe_requerido
from .models import Cronograma, InscripcionClase, Sede, Actividad, Torneo, InscripcionTorneo, ResultadoTorneo
from apps.usuarios.models import Usuario
from django.utils import timezone
from .forms import TorneoForm
from django.db.models import Count


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
    
    clases = Cronograma.objects.all().select_related('actividad', 'profesor', 'sede').annotate(
        num_inscriptos=Count('alumnos_inscritos')
    ).order_by('hora_inicio')
    
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
        'dias_semana': Cronograma.DiasSemana.choices,
        'hoy_cod': ['LU', 'MA', 'MI', 'JU', 'VI', 'SA', 'LU'][timezone.localtime().weekday()]
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


# ========================================================
#            PORTAL DE TORNEOS (ALUMNOS)
# ========================================================

@alumno_requerido
def lista_torneos(request):
    """
    Lista los torneos del año en curso en un panel premium.
    """
    alumno_id = request.session['alumno_id']
    anio_actual = timezone.now().year
    
    # Mostrar solo torneos del año actual
    torneos = Torneo.objects.filter(activo=True, fecha__year=anio_actual).order_by('fecha')
    
    #IDs de torneos en los que el alumno está inscrito
    mis_inscripciones_ids = InscripcionTorneo.objects.filter(
        alumno_id=alumno_id,
        torneo__fecha__year=anio_actual
    ).values_list('torneo_id', flat=True)
    
    return render(request, 'academia/torneos.html', {
        'torneos': torneos,
        'mis_inscripciones_ids': list(mis_inscripciones_ids),
        'anio_actual': anio_actual
    })

@alumno_requerido
def inscribir_torneo(request, torneo_id):
    """
    Inscribe de forma rápida al alumno en un torneo activo.
    """
    alumno_id = request.session['alumno_id']
    alumno = Usuario.objects.get(id=alumno_id)
    torneo = get_object_or_404(Torneo, id=torneo_id, activo=True)
    
    inscripcion, created = InscripcionTorneo.objects.get_or_create(alumno=alumno, torneo=torneo)
    if created:
        messages.success(request, f"🏆 ¡Inscripción registrada con éxito para {torneo.nombre}!")
    else:
        messages.warning(request, "Ya te encuentras registrado en este torneo.")
        
    return redirect('lista_torneos')

@alumno_requerido
def desanotarse_torneo(request, torneo_id):
    """
    Permite darse de baja de la convocatoria de un torneo.
    """
    alumno_id = request.session['alumno_id']
    inscripcion = get_object_or_404(InscripcionTorneo, alumno_id=alumno_id, torneo_id=torneo_id)
    torneo_nombre = inscripcion.torneo.nombre
    inscripcion.delete()
    
    messages.success(request, f"Has cancelado tu inscripción para {torneo_nombre}.")
    return redirect('lista_torneos')


# ========================================================
#          GESTIÓN DE TORNEOS (PROFESORES - CRUD)
# ========================================================

@profe_requerido
def gestion_torneos(request):
    """
    Panel centralizado para que los profesores administren torneos del año actual.
    """
    anio_actual = timezone.now().year
    # Anotamos la cantidad de inscriptos para cada torneo
    torneos = Torneo.objects.filter(fecha__year=anio_actual).annotate(
        total_inscriptos=Count('alumnos_inscritos')
    ).order_by('fecha')
    
    return render(request, 'academia/gestion_torneos.html', {
        'torneos': torneos,
        'anio_actual': anio_actual
    })

@profe_requerido
def crear_torneo(request):
    """
    Creación de un nuevo torneo mediante formulario Zen-Tech.
    """
    if request.method == 'POST':
        form = TorneoForm(request.POST)
        if form.is_valid():
            torneo = form.save()
            messages.success(request, f"¡Torneo '{torneo.nombre}' programado con éxito!")
            return redirect('gestion_torneos')
    else:
        form = TorneoForm()
        
    return render(request, 'academia/crear_editar_torneo.html', {
        'form': form,
        'titulo_accion': 'Programar Torneo'
    })

@profe_requerido
def editar_torneo(request, torneo_id):
    """
    Modificación de los detalles de un torneo existente.
    """
    torneo = get_object_or_404(Torneo, id=torneo_id)
    if request.method == 'POST':
        form = TorneoForm(request.POST, instance=torneo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Torneo '{torneo.nombre}' actualizado.")
            return redirect('gestion_torneos')
    else:
        form = TorneoForm(instance=torneo)
        
    return render(request, 'academia/crear_editar_torneo.html', {
        'form': form,
        'torneo': torneo,
        'titulo_accion': 'Editar Torneo'
    })

@profe_requerido
def eliminar_torneo(request, torneo_id):
    """
    Elimina un torneo de forma definitiva y redirecciona al panel de control.
    """
    torneo = get_object_or_404(Torneo, id=torneo_id)
    nombre = torneo.nombre
    torneo.delete()
    messages.success(request, f"Se ha eliminado el torneo '{nombre}' del sistema.")
    return redirect('gestion_torneos')

@profe_requerido
def ver_inscritos_torneo(request, torneo_id):
    """
    Muestra la nómina de alumnos registrados a un torneo con fines organizativos.
    """
    torneo = get_object_or_404(Torneo, id=torneo_id)
    inscripciones = torneo.alumnos_inscritos.select_related('alumno', 'alumno__grado').order_by('fecha_inscripcion')
    
    return render(request, 'academia/inscritos_torneo.html', {
        'torneo': torneo,
        'inscripciones': inscripciones
    })

@profe_requerido
def registrar_resultados_torneo(request, torneo_id):
    """
    Carga post-torneo: registra asistencia, categorías y podios de competidores.
    """
    torneo = get_object_or_404(Torneo, id=torneo_id)
    
    # Acción de Eliminación Rápida
    delete_id = request.GET.get('delete_id')
    if delete_id:
        resultado = get_object_or_404(ResultadoTorneo, id=delete_id, torneo=torneo)
        alumno_nombre = resultado.alumno.nombre_completo
        cat_nombre = resultado.categoria
        resultado.delete()
        messages.success(request, f"✅ Se eliminó el resultado de {alumno_nombre} en la categoría '{cat_nombre}'.")
        return redirect('registrar_resultados_torneo', torneo_id=torneo.id)

    # Procesar carga de resultado (POST)
    if request.method == 'POST':
        alumno_id = request.POST.get('alumno_id')
        categoria = request.POST.get('categoria', '').strip()
        asistio = request.POST.get('asistio') == 'on'
        podio = request.POST.get('podio', 'ninguno')
        
        if not alumno_id or not categoria:
            messages.error(request, "⚠️ Debes seleccionar un alumno y definir una categoría.")
        else:
            alumno = get_object_or_404(Usuario, id=alumno_id)
            try:
                ResultadoTorneo.objects.create(
                    alumno=alumno,
                    torneo=torneo,
                    categoria=categoria,
                    asistio=asistio,
                    podio=podio
                )
                messages.success(request, f"🏆 Cargado resultado para {alumno.nombre_completo} ({categoria}).")
            except Exception:
                messages.warning(request, f"⚠️ El alumno {alumno.nombre_completo} ya tiene registrado un resultado en la categoría '{categoria}'.")
            return redirect('registrar_resultados_torneo', torneo_id=torneo.id)

    # Datos para renderizar
    resultados = torneo.resultados_alumnos.select_related('alumno', 'alumno__grado').order_by('alumno__apellido', 'categoria')
    alumnos = Usuario.objects.filter(es_profe=False, is_active=True).order_by('apellido', 'nombre')
    
    return render(request, 'academia/registrar_resultados.html', {
        'torneo': torneo,
        'resultados': resultados,
        'alumnos': alumnos,
        'podio_opciones': ResultadoTorneo.PodioOpciones.choices
    })
