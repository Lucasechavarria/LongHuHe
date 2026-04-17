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
            
            # Validaciones de Seguridad, Prórroga y Paquetes
            alertas = []
            es_valido = False
            estado_pago = alumno.estado_morosidad
            descuenta_paquete = False
            
            if estado_pago in ["al_dia", "atrasado"]:
                es_valido = True
            elif alumno.fecha_prorroga and alumno.fecha_prorroga >= hoy:
                es_valido = True
                alertas.append("VENCIDO (EN PRÓRROGA)")
            elif alumno.clases_disponibles > 0:
                es_valido = True
                descuenta_paquete = True
            
            if not es_valido:
                 return JsonResponse({
                    'success': False,
                    'message': f"Bloqueado: {alumno.nombre} (Deuda / Sin Clases)",
                    'color': 'red',
                    'alertas': ["CUOTA VENCIDA"]
                })
            
            if not alumno.apto_medico:
                alertas.append("SIN APTO MÉDICO")
            
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
            elif descuenta_paquete:
                # Si no hay horario fijo pero tiene créditos, permitimos el ingreso libre
                inscripcion_activa = alumno.inscripciones_academia.filter(estado='regular').first()
                if inscripcion_activa:
                    actividad_detectada = inscripcion_activa.clase.actividad
                else:
                    actividad_detectada = "Clase Libre"
            else:
                # Alumno regular fuera de su horario y sin créditos
                return JsonResponse({
                    'success': False,
                    'message': f"Bloqueado: No tienes clase programada ahora ({ahora.strftime('%H:%M')}).",
                    'color': 'red',
                    'alertas': ["HORARIO NO CORRESPONDIENTE"]
                })

            # Cooldown: Bloqueo si vino a esta misma actividad hace menos de 3 horas
            limite_cooldown = ahora - timezone.timedelta(hours=3)
            ya_asistio = RegistroAsistencia.objects.filter(
                alumno=alumno, 
                actividad=actividad_detectada, 
                fecha_hora__gte=limite_cooldown
            ).exists()
            
            if ya_asistio:
                return JsonResponse({
                    'success': False,
                    'message': "Escaneo reciente (cooldown 3hs).",
                    'color': 'orange'
                })

            # Si era válido solo por tener clases disponibles, consumimos 1
            if descuenta_paquete:
                alumno.clases_disponibles -= 1
                alumno.save(update_fields=['clases_disponibles'])
                alertas.append(f"PAQUETE: Quedan {alumno.clases_disponibles}")

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
