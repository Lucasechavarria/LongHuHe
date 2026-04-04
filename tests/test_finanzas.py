import pytest
from apps.usuarios.models import Usuario, Sede
from apps.academia.models import Actividad
from apps.ventas.models import Pago

@pytest.mark.django_db
def test_calculo_comisiones_profesor():
    """ Task 4.6: Verificar que las comisiones se calculen correctamente al aprobar un pago """
    # 1. Setup
    sede = Sede.objects.create(nombre="Sede Sur")
    profe = Usuario.objects.create(username="profe_v8", es_profe=True)
    alumno = Usuario.objects.create(username="alumno_v8")
    
    actividad = Actividad.objects.create(
        nombre="Tai Chi Principiantes",
        precio_mes=10000,
        sede=sede
    )
    
    # 2. Pago pendiente por mes completo (10000)
    pago = Pago.objects.create(
        alumno=alumno,
        actividad=actividad,
        tipo=Pago.TipoPago.MES,
        metodo=Pago.MetodoPago.EFECTIVO,
        monto=10000,
        estado=Pago.EstadoPago.PENDIENTE
    )
    
    # 3. Act: Aprobar pago (dispara recalcular_comisiones en .save())
    pago.estado = Pago.EstadoPago.APROBADO
    pago.save()
    
    # 4. Assert: Por defecto 50% para el profe en este modelo simplificado
    pago.refresh_from_db()
    assert pago.monto == 10000
    assert pago.monto_comision_profesor == 5000
    assert pago.monto_utilidad_asociacion == 5000
