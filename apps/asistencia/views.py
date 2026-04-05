from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from apps.usuarios.models import Usuario
from apps.usuarios.views import profe_requerido
from apps.academia.models import Cronograma
from .models import RegistroAsistencia
from django.utils import timezone
import json

@profe_requerido
def escaner(request):
    """ Vista del escáner premium para el profesor. """
    return render(request, 'asistencia/escaner.html')

@csrf_exempt
@profe_requerido
def registrar_asistencia_qr(request):
    """ Endpoint AJAX para procesar el escaneo. """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            uuid_carnet = data.get('uuid')
            
            alumno = get_object_or_404(Usuario, uuid_carnet=uuid_carnet)
            hoy = timezone.now().date()
            
            # Validaciones de Seguridad y Negocio
            alertas = []
            es_valido = True
            
            if alumno.estado_morosidad == 'vencido':
                alertas.append("CUOTA VENCIDA")
                es_valido = False # Opcional: Bloquear o solo advertir. El task dice feedback visual.
            
            if not alumno.apto_medico:
                alertas.append("SIN APTO MÉDICO")
                # No bloqueamos asistencia por defecto, pero advertimos fuerte.
            
            # Detectar Actividad Actual (Inteligente: Horario + Inscripción)
            ahora = timezone.now()
            
            # Map strftime(%A) English to Cronograma codes
            day_map = {
                'monday': 'LU', 'tuesday': 'MA', 'wednesday': 'MI', 
                'thursday': 'JU', 'friday': 'VI', 'saturday': 'SA', 'sunday': 'DO'
            }
            dia_semana_raw = ahora.strftime('%A').lower()
            dia_semana = day_map.get(dia_semana_raw)
            
            # Buscamos en qué clases está el alumno HOY y CERCA de esta hora (+/- 2 horas de margen)
            rango_inicio = (ahora - timezone.timedelta(hours=2)).time()
            rango_fin = (ahora + timezone.timedelta(hours=2)).time()
            
            clase_actual = Cronograma.objects.filter(
                alumnos_inscritos__alumno=alumno,
                alumnos_inscritos__estado='regular',
                dia=dia_semana,
                hora_inicio__gte=rango_inicio,
                hora_inicio__lte=rango_fin
            ).first()

            actividad_detectada = None
            if clase_actual:
                actividad_detectada = clase_actual.actividad
            else:
                # Fallback: Si no hay clase programada exacta, tomamos su inscripción principal
                inscripcion_activa = alumno.inscripciones_academia.filter(estado='regular').first()
                if inscripcion_activa:
                    actividad_detectada = inscripcion_activa.clase.actividad

            # Bloqueo de doble registro hoy para la MISMA actividad
            ya_asistio = RegistroAsistencia.objects.filter(alumno=alumno, actividad=actividad_detectada, fecha_hora__date=hoy).exists()
            if ya_asistio:
                return JsonResponse({
                    'success': False,
                    'message': f"Ya vino a {actividad_detectada.nombre if actividad_detectada else 'clase'} hoy.",
                    'color': 'orange'
                })

            if not es_valido and "CUOTA VENCIDA" in alertas:
                 return JsonResponse({
                    'success': False,
                    'message': f"Bloqueado: {alumno.nombre} (Deuda)",
                    'color': 'red',
                    'alertas': alertas
                })

            # Registrar Asistencia con actividad
            RegistroAsistencia.objects.create(alumno=alumno, actividad=actividad_detectada)
            
            return JsonResponse({
                'success': True,
                'alumno': {
                    'nombre': alumno.nombre_completo,
                    'foto': alumno.foto_perfil.url if alumno.foto_perfil else None,
                    'grado': alumno.grado.nombre if alumno.grado else "Sin Grado",
                    'actividad': actividad_detectada.nombre if actividad_detectada else "General"
                },
                'alertas': alertas,
                'color': 'green' if not alertas else 'yellow'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
            
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
