import pytest
from apps.usuarios.models import Usuario
from apps.academia.models import Actividad, Sede
from apps.ventas.models import Pago
from apps.ventas.services.pago_service import PagoService

@pytest.mark.django_db
def test_calculo_comisiones_profesor():
    """ Task 4.6: Verificar que las comisiones se calculen correctamente al aprobar un pago """
    # 1. Setup
    Sede.objects.create(nombre="Sede Sur")
    Usuario.objects.create(username="profe_v8", es_profe=True, celular="11111111")
    alumno = Usuario.objects.create(username="alumno_v8", celular="22222222")
    
    actividad = Actividad.objects.create(
        nombre="Tai Chi Principiantes",
        precio_mes=10000
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
    
    # 3. Act: Aprobar pago vía Service (dispara recalcular_comisiones)
    PagoService.transicionar_a_aprobado(pago)
    
    # 4. Assert: Por defecto 50% para el profe en este modelo simplificado
    pago.refresh_from_db()
    assert pago.monto == 10000
    assert pago.monto_comision_profesor == 5000
    assert pago.monto_utilidad_asociacion == 5000
