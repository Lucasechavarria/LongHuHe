from django.db import transaction, models
from django.shortcuts import get_object_or_404
from .models import Cronograma, InscripcionClase
from apps.ventas.models import Pago

class AcademiaService:
    """
    Servicio encargado de la gestión de inscripciones, cupos y listas de espera.
    Asegura la integridad mediante bloqueos de base de datos (Pessimistic Locking).
    """

    @staticmethod
    @transaction.atomic
    def inscribir_alumno(alumno, clase_id):
        """
        Inscribe a un alumno en una clase, manejando el cupo y la lista de espera.
        Retorna (inscripcion, mensaje, exito).
        """
        # Bloqueamos la fila del cronograma para evitar race conditions en el cupo
        clase = Cronograma.objects.select_for_update().get(id=clase_id)
        
        # 1. Verificar Morosidad
        if alumno.estado_morosidad == 'vencido':
            mensaje = (
                "No puedes inscribirte a clases porque tu cuota está vencida. "
                "Por favor, regulariza tu situación."
            )
            return None, mensaje, False

        # 2. Verificar Saldo si es Paquete (excepto becados)
        if clase.actividad.tipo_cobro == Pago.TipoPago.PAQUETE and not alumno.es_becado:
            if alumno.clases_disponibles <= 0:
                mensaje = (
                    "No tienes clases disponibles. "
                    "Debes adquirir un nuevo paquete para inscribirte."
                )
                return None, mensaje, False

        # 3. Verificar si ya está inscrito
        inscripcion_previa = InscripcionClase.objects.filter(
            alumno=alumno, clase=clase
        ).exclude(estado='baja').first()
        if inscripcion_previa:
            return inscripcion_previa, "Ya estás anotado en este horario.", False


        # 2. Contar inscriptos regulares actuales
        inscriptos_regulares = InscripcionClase.objects.filter(
            clase=clase, 
            estado=InscripcionClase.EstadoInscrito.REGULAR
        ).count()
        
        if inscriptos_regulares < clase.cupo:
            estado = InscripcionClase.EstadoInscrito.REGULAR
            mensaje = f"¡Excelente! Te has inscrito en {clase.actividad.nombre}."
            exito = True
            
            # Consumimos crédito si es paquete y no es becado
            if clase.actividad.tipo_cobro == Pago.TipoPago.PAQUETE and not alumno.es_becado:
                alumno.clases_disponibles = models.F('clases_disponibles') - 1
                alumno.save(update_fields=['clases_disponibles'])
                # Recargamos el valor para el mensaje si es necesario, 
                # aunque F() no lo permite ver en el objeto actual sin refrescar.
        else:
            estado = InscripcionClase.EstadoInscrito.ESPERA
            mensaje = "El cupo está completo. Has sido agregado a la lista de espera."
            exito = True

        # 3. Crear o actualizar inscripción (si estaba de baja)
        inscripcion, created = InscripcionClase.objects.update_or_create(
            alumno=alumno,
            clase=clase,
            defaults={'estado': estado}
        )
        
        return inscripcion, mensaje, exito

    @staticmethod
    @transaction.atomic
    def dar_de_baja(alumno, clase_id):
        """
        Da de baja a un alumno de una clase y promueve al siguiente en espera si se libera cupo.
        """
        # Bloqueamos cronograma e inscripción
        clase = get_object_or_404(Cronograma.objects.select_for_update(), id=clase_id)
        inscripcion = get_object_or_404(InscripcionClase.objects.select_for_update(), alumno=alumno, clase=clase)
        
        if inscripcion.estado == 'baja':
            return False, "Ya estabas dado de baja."

        estado_anterior = inscripcion.estado
        inscripcion.estado = InscripcionClase.EstadoInscrito.BAJA
        inscripcion.save()

        # Si liberamos un cupo REGULAR, reintegramos crédito si era paquete
        if estado_anterior == InscripcionClase.EstadoInscrito.REGULAR:
            if clase.actividad.tipo_cobro == Pago.TipoPago.PAQUETE and not alumno.es_becado:
                alumno.clases_disponibles = models.F('clases_disponibles') + 1
                alumno.save(update_fields=['clases_disponibles'])

            # Buscamos a los candidatos en espera ordenados por fecha
            candidatos = InscripcionClase.objects.filter(
                clase=clase, 
                estado=InscripcionClase.EstadoInscrito.ESPERA
            ).select_for_update().order_by('fecha_inscripcion')
            
            for proximo in candidatos:
                # Si es tipo paquete, validamos que el alumno todavía tenga saldo
                if clase.actividad.tipo_cobro == Pago.TipoPago.PAQUETE and not proximo.alumno.es_becado:
                    if proximo.alumno.clases_disponibles <= 0:
                        continue
                    
                    # Consumimos crédito del que entra
                    proximo.alumno.clases_disponibles = models.F('clases_disponibles') - 1
                    proximo.alumno.save(update_fields=['clases_disponibles'])
                
                # Promoción exitosa
                proximo.estado = InscripcionClase.EstadoInscrito.REGULAR
                proximo.save()
                break
        
        return True, "Te has dado de baja correctamente."
