import json
import pytest
from django.urls import reverse
from django.test import Client
from apps.usuarios.models import Usuario
from apps.ventas.models import Pago, Actividad
from unittest.mock import patch, MagicMock

@pytest.fixture
def api_client():
    return Client()

@pytest.fixture
def setup_datos(db):
    alumno = Usuario.objects.create(
        nombre="Juan",
        apellido="Pérez",
        celular="1122334455",
        dni="12345678",
        es_profe=False
    )
    actividad = Actividad.objects.create(
        nombre="Tai-Chi",
        precio_mes=5000,
        precio_clase=500,
        tipo_cobro="mes"
    )
    pago = Pago.objects.create(
        alumno=alumno,
        actividad=actividad,
        monto=5000,
        tipo=Pago.TipoPago.MES,
        metodo=Pago.MetodoPago.MERCADOPAGO,
        estado=Pago.EstadoPago.PENDIENTE
    )
    return alumno, actividad, pago

@pytest.mark.django_db
def test_webhook_metodo_invalido(api_client):
    """ El webhook debe rechazar llamadas que no sean POST """
    url = reverse('mercadopago_webhook')
    response = api_client.get(url)
    assert response.status_code == 400
    assert json.loads(response.content)['status'] == 'bad_request'

@pytest.mark.django_db
@patch('apps.ventas.views.validar_signature_mp')
def test_webhook_firma_invalida(mock_validar, api_client):
    """ Si la firma es inválida, debe rechazar con 400 Forbidden """
    mock_validar.return_value = False
    url = reverse('mercadopago_webhook')
    response = api_client.post(url, data=json.dumps({"id": 123}), content_type="application/json")
    assert response.status_code == 400
    assert json.loads(response.content)['status'] == 'forbidden'

@pytest.mark.django_db
@patch('apps.ventas.views.validar_signature_mp')
def test_webhook_payload_malformado(mock_validar, api_client):
    """ Si el payload JSON es malformado, debe responder con 400 y no 500 """
    mock_validar.return_value = True
    url = reverse('mercadopago_webhook')
    response = api_client.post(url, data="payload corrupto", content_type="application/json")
    assert response.status_code == 400
    assert json.loads(response.content)['detail'] == 'JSON malformado'

@pytest.mark.django_db
@patch('apps.ventas.views.validar_signature_mp')
@patch('apps.ventas.services.payments.factory.PaymentGatewayFactory.get_gateway')
def test_webhook_v2_aprobacion_exitosa(mock_gateway, mock_validar, api_client, setup_datos):
    """ Simula la aprobación exitosa de un pago via Webhook V2 (ID en el body JSON) """
    alumno, actividad, pago = setup_datos
    mock_validar.return_value = True
    
    # Mockear la respuesta de la pasarela de Mercado Pago
    mock_gateway_instance = MagicMock()
    mock_gateway_instance.obtener_pago.return_value = {
        "external_reference": str(pago.id),
        "status": "approved"
    }
    mock_gateway.return_value = mock_gateway_instance
    
    url = reverse('mercadopago_webhook')
    # Webhook V2: Envía el ID en el cuerpo JSON
    payload = {
        "action": "payment.created",
        "api_version": "v1",
        "data": {
            "id": "999888777"
        },
        "type": "payment"
    }
    
    response = api_client.post(
        url, 
        data=json.dumps(payload), 
        content_type="application/json"
    )
    
    assert response.status_code == 200
    assert json.loads(response.content)['status'] == 'ok'
    
    # Verificar que el pago se haya actualizado a APROBADO
    pago.refresh_from_db()
    assert pago.estado == Pago.EstadoPago.APROBADO
