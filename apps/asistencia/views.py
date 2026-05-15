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
            # Validaciones y Procesamiento vía Service Layer
            from .services import ScannerService
            resultado = ScannerService.procesar_escaneo(uuid_carnet)
            return JsonResponse(resultado)
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
            
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
