from django.db import models
from django.utils import timezone
from django.shortcuts import get_object_or_404
from apps.usuarios.models import Usuario
from apps.academia.models import Cronograma
from apps.asistencia.models import RegistroAsistencia

class ScannerService:
    @staticmethod
    def procesar_escaneo(uuid_carnet):
        """
        Procesa el escaneo del QR, validando morosidad, horarios, apto médico
        y registrando la asistencia si todo es correcto.
        Devuelve un diccionario con el estado y los datos a renderizar.
        """
        alumno = get_object_or_404(Usuario, uuid_carnet=uuid_carnet)
        hoy = timezone.now().date()
        ahora = timezone.now()
        
        alertas = []
        es_valido = False
        estado_pago = alumno.estado_morosidad
        descuenta_paquete = False
        
        # 1. Validar Morosidad o Paquete
        if estado_pago in ["al_dia", "atrasado"]:
            es_valido = True
        elif alumno.fecha_prorroga and alumno.fecha_prorroga >= hoy:
            es_valido = True
            alertas.append("VENCIDO (EN PRÓRROGA)")
        elif alumno.clases_disponibles > 0:
            es_valido = True
            descuenta_paquete = True
        
        if not es_valido:
            return {
                'success': False,
                'message': f"Bloqueado: {alumno.nombre} (Deuda / Sin Clases)",
                'color': 'red',
                'alertas': ["CUOTA VENCIDA"]
            }
        
        if not alumno.apto_medico:
            alertas.append("SIN APTO MÉDICO")
            
        # 2. Detectar Actividad Actual
        day_map = {
            'monday': 'LU', 'tuesday': 'MA', 'wednesday': 'MI', 
            'thursday': 'JU', 'friday': 'VI', 'saturday': 'SA', 'sunday': 'DO'
        }
        dia_semana_raw = ahora.strftime('%A').lower()
        dia_semana = day_map.get(dia_semana_raw)
        
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
            inscripcion_activa = alumno.inscripciones_academia.filter(estado='regular').first()
            if inscripcion_activa:
                actividad_detectada = inscripcion_activa.clase.actividad
            else:
                actividad_detectada = "Clase Libre"
        else:
            return {
                'success': False,
                'message': f"Bloqueado: No tienes clase programada ahora ({ahora.strftime('%H:%M')}).",
                'color': 'red',
                'alertas': ["HORARIO NO CORRESPONDIENTE"]
            }

        # 3. Cooldown
        limite_cooldown = ahora - timezone.timedelta(hours=3)
        ya_asistio = RegistroAsistencia.objects.filter(
            alumno=alumno, 
            actividad=actividad_detectada, 
            fecha_hora__gte=limite_cooldown
        ).exists()
        
        if ya_asistio:
            return {
                'success': False,
                'message': "Escaneo reciente (cooldown 3hs).",
                'color': 'orange'
            }

        # 4. Procesar Asistencia (Consumo de créditos)
        # Solo descontamos si no estaba previamente inscrito (Clase Libre)
        # porque la inscripción ya descuenta el crédito al momento de confirmarse.
        if descuenta_paquete and not clase_actual:
            alumno.clases_disponibles = models.F('clases_disponibles') - 1
            alumno.save(update_fields=['clases_disponibles'])
            # Refrescamos para el mensaje
            alumno.refresh_from_db()
            alertas.append(f"CLASE LIBRE: Quedan {alumno.clases_disponibles}")
        elif clase_actual and clase_actual.actividad.tipo_cobro == 'paquete' and not alumno.es_becado:
            # Ya fue descontado en la inscripción
            alertas.append(f"INSCRIPCIÓN: Saldo {alumno.clases_disponibles}")

        RegistroAsistencia.objects.create(alumno=alumno, actividad=actividad_detectada)
        
        actividad_nombre = actividad_detectada.nombre if getattr(actividad_detectada, 'nombre', None) else str(actividad_detectada)
        if hasattr(actividad_detectada, 'nombre'):
             actividad_nombre = actividad_detectada.nombre
        else:
             actividad_nombre = "General" if not actividad_detectada else str(actividad_detectada)

        return {
            'success': True,
            'alumno': {
                'nombre': alumno.nombre_completo,
                'foto': alumno.foto_perfil.url if alumno.foto_perfil else None,
                'grado': alumno.grado.nombre if alumno.grado else "Sin Grado",
                'actividad': actividad_nombre
            },
            'alertas': alertas,
            'color': 'green' if not alertas else 'yellow'
        }
