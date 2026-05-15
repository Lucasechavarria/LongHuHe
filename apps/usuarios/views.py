from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib import messages
from functools import wraps
from .models import Usuario
from .forms import AlumnoOnboardingForm, UsuarioPerfilForm, UsuarioSaludForm
from django.core.cache import cache
from .utils import get_client_ip

def rate_limit_login(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.method == 'POST':
            ip = get_client_ip(request)
            key = f"rate_limit_login_{ip}"
            attempts = cache.get(key, 0)
            if attempts >= 10:
                messages.error(request, "⚠️ Demasiados intentos fallidos. Por favor, espera 15 minutos.")
                return render(request, 'usuarios/identificacion.html')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def requiere_rol(rol_nombre):
    """
    Decorador avanzado para RBAC (Role Based Access Control).
    Verifica si el usuario tiene el campo booleano 'rol_nombre' activo.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Asegurar objeto usuario en request
            if not hasattr(request, 'user_obj'):
                if 'alumno_id' in request.session:
                    request.user_obj = Usuario.objects.filter(id=request.session['alumno_id']).first()
                elif request.user.is_authenticated:
                    request.user_obj = request.user
            
            if not getattr(request, 'user_obj', None):
                messages.error(request, "Sesión requerida.")
                return redirect('splash')

            # 2. Verificar rol (o acceso total)
            usuario = request.user_obj
            if usuario.rol_acceso_total:
                return view_func(request, *args, **kwargs)
            
            if getattr(usuario, rol_nombre, False):
                return view_func(request, *args, **kwargs)
            
            messages.error(request, f"Acceso denegado: Se requiere el rol '{rol_nombre.replace('rol_', '').replace('_', ' ').title()}'.")
            return redirect('splash')
        return _wrapped_view
    return decorator

def profe_requerido(view_func):
    """ Decorador base para asegurar que sea un profesor/staff. """
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

@rate_limit_login
def identificacion(request):
    if 'alumno_id' in request.session:
        return redirect('perfil')
    if request.method == 'POST':
        identificador = request.POST.get('identificador', '').strip()
        nacimiento = request.POST.get('nacimiento', '').strip()
        
        ip = get_client_ip(request)
        key = f"rate_limit_login_{ip}"
        
        from .models import BitacoraSeguridad
        if identificador and nacimiento:
            alumno = Usuario.objects.filter(Q(celular__icontains=identificador) | Q(dni=identificador)).first()
            if alumno:
                if alumno.fecha_nacimiento and str(alumno.fecha_nacimiento.year) == nacimiento:
                    request.session['alumno_id'] = alumno.id
                    request.session['es_profe'] = alumno.es_profe
                    BitacoraSeguridad.registrar(request, BitacoraSeguridad.TipoEvento.ACCESO_EXITOSO, f"Login exitoso via DNI/Nacimiento", usuario=alumno)
                    cache.delete(key) # Limpiar intentos
                    messages.success(request, f"¡Bienvenido, {alumno.nombre}!")
                    return redirect('perfil')
                else:
                    # Incrementar intentos
                    cache.set(key, cache.get(key, 0) + 1, 900) # 15 min
                    BitacoraSeguridad.registrar(request, BitacoraSeguridad.TipoEvento.ACCESO_FALLIDO, f"Intento fallido para DNI {identificador}: Año nacimiento incorrecto")
                    messages.error(request, "⚠️ El Año de Nacimiento proveido es incorrecto.")
            else:
                cache.set(key, cache.get(key, 0) + 1, 900)
                BitacoraSeguridad.registrar(request, BitacoraSeguridad.TipoEvento.ACCESO_FALLIDO, f"Intento fallido: Identificador {identificador} no encontrado")
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
            from apps.usuarios.services import UsuarioService
            
            # Pasar los clean data al servicio
            usuario = UsuarioService.crear_alumno_desde_onboarding(
                datos=form.cleaned_data,
                foto_perfil=form.cleaned_data.get('foto_perfil')
            )
            
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
    from apps.usuarios.services import UsuarioService
    
    exito, mensaje = UsuarioService.solicitar_prorroga(alumno)
    
    if exito:
        messages.success(request, f"🛡️ {mensaje}")
    else:
        if "al día" in mensaje:
            messages.info(request, mensaje)
        else:
            messages.warning(request, mensaje)
            return redirect('cuota_vencida')
            
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
