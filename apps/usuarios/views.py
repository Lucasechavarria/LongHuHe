from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib import messages
from functools import wraps
from .models import Usuario
from .forms import AlumnoOnboardingForm, UsuarioPerfilForm, UsuarioSaludForm

def profe_requerido(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'alumno_id' in request.session:
            usuario = Usuario.objects.filter(id=request.session['alumno_id']).first()
            if usuario and usuario.es_profe:
                request.user_obj = usuario
                return view_func(request, *args, **kwargs)
        if request.user.is_authenticated and getattr(request.user, 'es_profe', False):
            request.user_obj = request.user
            return view_func(request, *args, **kwargs)
        messages.error(request, "Acceso restringido solo para profesores.")
        return redirect('splash')
    return _wrapped_view

def alumno_requerido(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'alumno_id' not in request.session:
            return redirect('onboarding')
        
        usuario_id = request.session['alumno_id']
        # Optimización Sprint 7: Cargar grado y sede de una vez
        usuario = Usuario.objects.select_related('grado', 'sede').filter(id=usuario_id).first()
        
        if not usuario:
            del request.session['alumno_id']
            return redirect('onboarding')

        # --- SISTEMA DE RESTRICCIÓN POR MOROSIDAD ---
        if usuario.estado_morosidad == 'vencido':
            from django.urls import resolve
            try:
                url_name = resolve(request.path_info).url_name
            except Exception:
                url_name = ""
            
            urls_permitidas = [
                'pago_tipo', 'pago_metodo', 'pago_comprobante', 'pago_confirmacion', 
                'pago_mercadopago_checkout', 'mercadopago_webhook', 'logout', 
                'cuota_vencida', 'gracias', 'solicitar_prorroga', 'splash'
            ]
            
            if url_name not in urls_permitidas:
                return redirect('cuota_vencida')

        request.user_obj = usuario
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def splash(request):
    """ Task 2: Pantalla de Bienvenida High-Impact (Long Hu He) """
    if 'alumno_id' in request.session:
        return redirect('perfil')
    return render(request, 'usuarios/splash.html')

def acceso_opciones(request):
    if 'alumno_id' in request.session:
        return redirect('perfil')
    return render(request, 'usuarios/acceso_opciones.html')

def identificacion(request):
    if 'alumno_id' in request.session:
        return redirect('perfil')
    if request.method == 'POST':
        identificador = request.POST.get('identificador', '').strip()
        nacimiento = request.POST.get('nacimiento', '').strip()
        
        if identificador and nacimiento:
            alumno = Usuario.objects.filter(Q(celular__icontains=identificador) | Q(dni=identificador)).first()
            if alumno:
                # Security Hook (REMOVIDO: Permitir que los Docentes y Staff usen la App móvil)
                # if getattr(alumno, 'is_staff', False) or getattr(alumno, 'is_superuser', False) or getattr(alumno, 'es_profe', False):
                #     messages.error(request, "🚫⛔ Acceso Denegado: Docentes y Staff deben iniciar sesión con Contraseña obligatoria.")
                #     return redirect('acceso_opciones')
                
                # Validation Hook
                if alumno.fecha_nacimiento and str(alumno.fecha_nacimiento.year) == nacimiento:
                    request.session['alumno_id'] = alumno.id
                    request.session['es_profe'] = alumno.es_profe
                    messages.success(request, f"¡Bienvenido, {alumno.nombre}!")
                    return redirect('perfil')
                else:
                    messages.error(request, "⚠️ El Año de Nacimiento proveido es incorrecto.")
            else:
                messages.info(request, "No encontramos tus datos. ¡Por favor, completa tu inscripción!")
                return redirect('onboarding')
        else:
            messages.warning(request, "Debes completar el DNI y el Año de Nacimiento.")
    return render(request, 'usuarios/identificacion.html')

def onboarding(request):
    if 'alumno_id' in request.session:
        return redirect('perfil')
    if request.method == 'POST':
        form = AlumnoOnboardingForm(request.POST, request.FILES)
        if form.is_valid():
            celular = form.cleaned_data['celular']
            dni = form.cleaned_data['dni']
            # Asignar Grado "Blanco" por defecto (Orden 0)
            from .models import Grado
            default_grado = Grado.objects.filter(Q(nombre__iexact="Blanco") | Q(orden=0)).first()

            usuario, created = Usuario.objects.get_or_create(
                celular=celular,
                defaults={
                    'nombre': form.cleaned_data['nombre'],
                    'apellido': form.cleaned_data['apellido'],
                    'dni': dni,
                    'fecha_nacimiento': form.cleaned_data['fecha_nacimiento'],
                    'domicilio': form.cleaned_data['domicilio'],
                    'localidad': form.cleaned_data['localidad'],
                    'sede': form.cleaned_data['sede'],
                    'foto_perfil': form.cleaned_data.get('foto_perfil'),
                    'grado': default_grado,
                }
            )
            if not created:
                usuario.nombre = form.cleaned_data['nombre']
                usuario.apellido = form.cleaned_data['apellido']
                usuario.dni = dni
                usuario.fecha_nacimiento = form.cleaned_data['fecha_nacimiento']
                usuario.domicilio = form.cleaned_data['domicilio']
                usuario.localidad = form.cleaned_data['localidad']
                usuario.sede = form.cleaned_data['sede']
                if not usuario.grado:
                    usuario.grado = default_grado
                if form.cleaned_data.get('foto_perfil'):
                    usuario.foto_perfil = form.cleaned_data.get('foto_perfil')
                usuario.save()
            actividad = form.cleaned_data.get('actividad_inicial')
            if actividad:
                usuario.actividades.add(actividad)
            request.session['alumno_id'] = usuario.id
            request.session['es_profe'] = usuario.es_profe
            return redirect('perfil')
    else:
        form = AlumnoOnboardingForm()
    return render(request, 'usuarios/onboarding.html', {'form': form})

@alumno_requerido
def perfil(request):
    """ Muestra el dashboard del alumno con sus datos y QR. """
    alumno = request.user_obj
    from apps.examenes.models import MesaExamen
    
    mesas_disponibles = MesaExamen.objects.filter(esta_abierta=True).exclude(
        candidatos__alumno=alumno
    ).order_by('fecha')
    
    return render(request, 'usuarios/perfil.html', {
        'alumno': alumno,
        'mesas_disponibles': mesas_disponibles
    })

@alumno_requerido
def editar_perfil(request):
    alumno = Usuario.objects.get(id=request.session['alumno_id'])
    if request.method == 'POST':
        form = UsuarioPerfilForm(request.POST, request.FILES, instance=alumno)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Perfil actualizado correctamente!")
            return redirect('perfil')
    else:
        form = UsuarioPerfilForm(instance=alumno)
    return render(request, 'usuarios/editar_perfil.html', {'form': form, 'alumno': alumno})

@alumno_requerido
def editar_salud(request):
    alumno = Usuario.objects.get(id=request.session['alumno_id'])
    if request.method == 'POST':
        form = UsuarioSaludForm(request.POST, instance=alumno)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Información de salud actualizada!")
            return redirect('perfil')
    else:
        form = UsuarioSaludForm(instance=alumno)
    return render(request, 'usuarios/editar_salud.html', {'form': form, 'alumno': alumno})
@alumno_requerido
def solicitar_prorroga(request):
    alumno = request.user_obj
    
    if alumno.estado_morosidad == 'vencido':
        from datetime import date, timedelta
        hoy = date.today()
        
        # Validación de "Una sola prórroga por mes"
        if alumno.ultima_prorroga_solicitada and \
           alumno.ultima_prorroga_solicitada.month == hoy.month and \
           alumno.ultima_prorroga_solicitada.year == hoy.year:
            messages.warning(request, "Ya has solicitado una prórroga este mes. Por favor, regulariza tu cuota para continuar.")
            return redirect('cuota_vencida')

        # Si no tiene fecha_prorroga activa o expiré, le otorgamos 15 días desde hoy
        alumno.fecha_prorroga = hoy + timedelta(days=15)
        alumno.ultima_prorroga_solicitada = hoy
        alumno.save(update_fields=['fecha_prorroga', 'ultima_prorroga_solicitada'])
        
        messages.success(request, "🛡️ Prórroga de 15 días activada. Tenés acceso completo temporariamente.")
        return redirect('perfil')
    else:
        messages.info(request, "No necesitas prórroga, tu cuota está al día.")
        return redirect('perfil')

@alumno_requerido
def cuota_vencida(request):
    """ Vista de bloqueo para alumnos morosos (Sprint 2) """
    alumno = request.user_obj
    if alumno.estado_morosidad != 'vencido':
        return redirect('perfil')
    
    return render(request, 'usuarios/cuota_vencida.html', {
        'alumno': alumno,
    })

def logout(request):
    request.session.flush()
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect('acceso_opciones')
