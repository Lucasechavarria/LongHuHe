from django.urls import path
from . import views

urlpatterns = [
    path('tipo/', views.pago_tipo, name='pago_tipo'),
    path('metodo/', views.pago_metodo, name='pago_metodo'),
    path('comprobante/', views.pago_comprobante, name='pago_comprobante'),
    path('confirmacion/', views.pago_confirmacion, name='pago_confirmacion'),
    path('mercadopago/<int:pago_id>/', views.pago_mercadopago_checkout, name='pago_mercadopago_checkout'), 
    path('mercadopago/webhook/', views.mercadopago_webhook, name='mercadopago_webhook'),
    
    path('tienda/', views.tienda_inicio, name='tienda_inicio'),
    path('tienda/comprar/<int:producto_id>/', views.tienda_comprar, name='tienda_comprar'),
    
    # Carrito
    path('tienda/carrito/sync/', views.carrito_sync, name='carrito_sync'),
    path('tienda/carrito/', views.carrito_ver, name='carrito_ver'),
    path('tienda/checkout/', views.checkout, name='checkout'),
    
    # Tesorería
    path('gestion/', views.gestion_tesoreria, name='gestion_tesoreria'),
    path('gestion/pago/<int:pago_id>/', views.gestionar_pago_accion, name='gestionar_pago_accion'),
    path('gestion/pedido/<int:pedido_id>/', views.gestionar_pedido_accion, name='gestionar_pedido_accion'),
    path('gracias/', views.gracias, name='gracias'),
    path('historial/', views.pago_historial, name='pago_historial'),
    path('exportar-csv/', views.exportar_tesoreria_csv, name='exportar_tesoreria_csv'),
    path('exportar-pdf/', views.exportar_tesoreria_pdf, name='exportar_tesoreria_pdf'),
    path('cerrar-caja/', views.cerrar_caja_mensual, name='cerrar_caja_mensual'),
]
