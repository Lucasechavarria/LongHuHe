from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib import messages
from functools import wraps
from .models import Usuario
from .forms import AlumnoOnboardingForm, UsuarioPerfilForm

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
        return redirect('inicio')
    return _wrapped_view

def alumno_requerido(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'alumno_id' not in request.session:
            return redirect('onboarding')
        if not Usuario.objects.filter(id=request.session['alumno_id']).exists():
            del request.session['alumno_id']
            return redirect('onboarding')
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
        return redirect('inicio')
    if request.method == 'POST':
        identificador = request.POST.get('identificador', '').strip()
        if identificador:
            alumno = Usuario.objects.filter(Q(celular__icontains=identificador) | Q(dni=identificador)).first()
            if alumno:
                request.session['alumno_id'] = alumno.id
                request.session['es_profe'] = alumno.es_profe
                messages.success(request, f"¡Bienvenido nuevamente, {alumno.nombre}!")
                return redirect('inicio')
            else:
                messages.info(request, "No encontramos tus datos. ¡Por favor, completa tu inscripción!")
                return redirect('onboarding')
    return render(request, 'usuarios/identificacion.html')

def onboarding(request):
    if 'alumno_id' in request.session:
        return redirect('inicio')
    if request.method == 'POST':
        form = AlumnoOnboardingForm(request.POST, request.FILES)
        if form.is_valid():
            celular = form.cleaned_data['celular']
            dni = form.cleaned_data['dni']
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
                if form.cleaned_data.get('foto_perfil'):
                    usuario.foto_perfil = form.cleaned_data.get('foto_perfil')
                usuario.save()
            actividad = form.cleaned_data.get('actividad_inicial')
            if actividad:
                usuario.actividades.add(actividad)
            request.session['alumno_id'] = usuario.id
            request.session['es_profe'] = usuario.es_profe
            return redirect('inicio')
    else:
        form = AlumnoOnboardingForm()
    return render(request, 'usuarios/onboarding.html', {'form': form})

@alumno_requerido
def perfil(request):
    alumno = Usuario.objects.get(id=request.session['alumno_id'])
    linea_tiempo = alumno.examenes.select_related('grado', 'examinador').all()
    return render(request, 'usuarios/perfil.html', {
        'alumno': alumno,
        'linea_tiempo': linea_tiempo
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
def logout(request):
    request.session.flush()
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect('acceso_opciones')
