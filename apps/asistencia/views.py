import json
from datetime import timedelta
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from apps.usuarios.views import profe_requerido
from apps.usuarios.models import Usuario
from apps.academia.models import Actividad
from apps.ventas.models import Pago
from apps.ventas.services.pago_service import PagoService
from apps.asistencia.models import RegistroAsistencia
from .services import ScannerService


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

            # Validaciones y Procesamiento vía Service Layer
            resultado = ScannerService.procesar_escaneo(uuid_carnet)
            return JsonResponse(resultado)
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
            
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)


@csrf_exempt
@profe_requerido
def api_registrar_pago_efectivo_scanner(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            alumno_id = data.get('alumno_id')
            actividad_id = data.get('actividad_id')
            
            alumno = get_object_or_404(Usuario, id=alumno_id)
            if actividad_id:
                actividad = get_object_or_404(Actividad, id=actividad_id)
            else:
                actividad = alumno.actividades.first()
                
            if not actividad:
                return JsonResponse({'success': False, 'message': 'El alumno no tiene actividades registradas.'}, status=400)
                
            # Registrar y transicionar a aprobado
            pago = PagoService.registrar_pago(
                alumno=alumno,
                actividad=actividad,
                tipo=Pago.TipoPago.MES,
                metodo=Pago.MetodoPago.EFECTIVO,
            )
            PagoService.transicionar_a_aprobado(pago)
            
            # Registrar asistencia
            RegistroAsistencia.objects.create(alumno=alumno, actividad=actividad)
            
            return JsonResponse({
                'success': True,
                'message': f"Pago en efectivo de cuota (${pago.monto}) registrado y asistencia marcada para {alumno.nombre_completo}."
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)


@csrf_exempt
@profe_requerido
def api_otorgar_prorroga_scanner(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            alumno_id = data.get('alumno_id')
            alumno = get_object_or_404(Usuario, id=alumno_id)
            
            hoy = timezone.now().date()
            alumno.fecha_prorroga = hoy + timedelta(days=15)
            alumno.ultima_prorroga_solicitada = hoy
            alumno.save(update_fields=['fecha_prorroga', 'ultima_prorroga_solicitada'])
            
            # Registrar asistencia
            actividad = alumno.actividades.first()
            RegistroAsistencia.objects.create(alumno=alumno, actividad=actividad)
            
            return JsonResponse({
                'success': True,
                'message': f"Prórroga de 15 días concedida y asistencia marcada para {alumno.nombre_completo}."
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)


@csrf_exempt
@profe_requerido
def api_forzar_ingreso_scanner(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            alumno_id = data.get('alumno_id')
            alumno = get_object_or_404(Usuario, id=alumno_id)
            
            actividad = alumno.actividades.first()
            RegistroAsistencia.objects.create(alumno=alumno, actividad=actividad)
            
            return JsonResponse({
                'success': True,
                'message': f"Ingreso excepcional (clase de prueba/forzado) registrado para {alumno.nombre_completo}."
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
