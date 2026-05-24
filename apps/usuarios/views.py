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
    Verifica si el usuario tiene el campo booleano 'rol_nombre' activo y sesión Django segura.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Exigir sesión segura de Django autenticada con contraseña
            if not request.user.is_authenticated or not (request.user.es_profe or request.user.is_staff):
                messages.error(request, "⚠️ Se requiere inicio de sesión administrativo seguro.")
                return redirect('login_profesor')
            
            usuario = request.user
            request.user_obj = usuario
            
            if usuario.rol_acceso_total:
                return view_func(request, *args, **kwargs)
            
            if getattr(usuario, rol_nombre, False):
                return view_func(request, *args, **kwargs)
            
            nombre_legible = rol_nombre.replace('rol_', '').replace('_', ' ').title()
            messages.error(request, f"⚠️ Acceso denegado: Se requiere el rol administrativo '{nombre_legible}'.")
            return redirect('perfil')
        return _wrapped_view
    return decorator

def profe_requerido(view_func):
    """ Decorador base para asegurar que sea un profesor/staff con sesión segura de Django. """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Exigir sesión segura de Django autenticada con contraseña
        if request.user.is_authenticated and (request.user.es_profe or request.user.is_staff):
            request.user_obj = request.user
            return view_func(request, *args, **kwargs)
            
        messages.error(request, "⚠️ Acceso restringido. Por favor inicia sesión como Instructor.")
        return redirect('login_profesor')
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
        pin = request.POST.get('pin', '').strip()
        
        ip = get_client_ip(request)
        key = f"rate_limit_login_{ip}"
        
        from .models import BitacoraSeguridad
        if identificador and pin:
            alumno = Usuario.objects.filter(Q(celular__icontains=identificador) | Q(dni=identificador)).first()
            if alumno:
                # 1. Bloquear accesos administrativos / de profesores en este login simplificado
                if alumno.es_profe or alumno.is_staff or alumno.is_superuser:
                    BitacoraSeguridad.registrar(request, BitacoraSeguridad.TipoEvento.ACCESO_FALLIDO, f"Intento de acceso profe en panel de alumnos para ID {identificador}")
                    messages.error(request, "⚠️ Los profesores deben iniciar sesión mediante el Panel de Instructores.")
                    return render(request, 'usuarios/identificacion.html')

                # 2. Migración transparente de PIN si el alumno no lo tiene configurado (perezosa)
                fue_autogenerado = False
                if not alumno.pin_hash:
                    alumno.blanquear_pin()
                    alumno.refresh_from_db()
                    fue_autogenerado = True

                # 3. Validación de PIN seguro
                if alumno.check_pin(pin):
                    request.session['alumno_id'] = alumno.id
                    request.session['es_profe'] = False  # Garantizar que no se inyecten permisos
                    BitacoraSeguridad.registrar(request, BitacoraSeguridad.TipoEvento.ACCESO_EXITOSO, "Login exitoso via DNI/PIN", usuario=alumno)
                    cache.delete(key) # Limpiar intentos
                    
                    if fue_autogenerado:
                        messages.success(request, f"¡Bienvenido, {alumno.nombre}! Hemos asignado un PIN de seguridad temporal (últimos 4 números de tu DNI o celular). Por favor, modifícalo en tu perfil.")
                    else:
                        messages.success(request, f"¡Bienvenido, {alumno.nombre}!")
                    return redirect('perfil')
                else:
                    # Incrementar intentos
                    cache.set(key, cache.get(key, 0) + 1, 900) # 15 min
                    BitacoraSeguridad.registrar(request, BitacoraSeguridad.TipoEvento.ACCESO_FALLIDO, f"Intento fallido para DNI {identificador}: PIN incorrecto")
                    messages.error(request, "⚠️ El PIN ingresado es incorrecto.")
            else:
                cache.set(key, cache.get(key, 0) + 1, 900)
                BitacoraSeguridad.registrar(request, BitacoraSeguridad.TipoEvento.ACCESO_FALLIDO, f"Intento fallido: Identificador {identificador} no encontrado")
                messages.info(request, "No encontramos tus datos. ¡Por favor, completa tu inscripción!")
                return redirect('onboarding')
        else:
            messages.warning(request, "Debes completar el Identificador y el PIN de acceso.")
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

def login_profesor(request):
    """
    Vista de login seguro para profesores y personal administrativo.
    Utiliza el sistema de contraseñas nativo y robusto de Django.
    """
    if 'alumno_id' in request.session:
        request.session.flush()

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        from django.contrib.auth import authenticate, login as django_login
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.es_profe or user.is_staff or user.is_superuser:
                django_login(request, user)
                request.session['alumno_id'] = user.id
                request.session['es_profe'] = True
                
                from .models import BitacoraSeguridad
                BitacoraSeguridad.registrar(request, BitacoraSeguridad.TipoEvento.ACCESO_EXITOSO, "Login admin exitoso", usuario=user)
                
                messages.success(request, f"¡Bienvenido, {user.nombre}!")
                if user.rol_gestion_tesoreria or user.rol_acceso_total:
                    return redirect('gestion_tesoreria')
                return redirect('perfil')
            else:
                messages.error(request, "⚠️ Acceso denegado: Esta cuenta no tiene rango de profesor o staff.")
        else:
            messages.error(request, "⚠️ Credenciales inválidas. Verifica tu usuario y contraseña.")
            
    return render(request, 'usuarios/login_profesor.html')
