# Documentación Técnica: Blindaje y Lógica del ERP Long Hu He

Este documento detalla los mecanismos de ingeniería y seguridad implementados para garantizar la integridad de los datos en un entorno de producción de alta demanda.

## 1. Integridad Financiera y Concurrencia
### 1.1 Blindaje de Webhooks (Mercado Pago)
Para evitar "condiciones de carrera" (cuando dos notificaciones llegan al mismo tiempo), el sistema utiliza:
- **`transaction.atomic()`**: Garantiza que si un paso falla, nada se guarda.
- **`select_for_update()`**: Bloquea la fila del `Pedido` en la base de datos hasta que termine de procesarse el estado de pago, evitando duplicación de acreditaciones.

### 1.2 Recalculación Automática de Stats
Se utilizan **Django Signals** (`post_save` en `PedidoItem`) para actualizar automáticamente el `monto_costo_reposicion` y la `utilidad_neta_asociacion` en el modelo `Pedido`. Esto garantiza que los tableros de tesorería siempre reflejen datos reales.

## 2. Gestión de Inventario Automática
### 2.1 Descuento de Stock
El sistema descuenta stock automáticamente en dos casos:
1. Al marcarse como **PAGADO** (vía Webhook o Admin).
2. Al marcarse como **ENTREGADO**.
Si un pedido se cancela, el sistema restaura el stock de forma atómica.

### 2.2 Variantes (Talles)
El sistema soporta `ProductoVariante`. El descuento de stock prioriza la variante si existe; de lo contrario, descuenta del producto base.

## 3. Lógica de Asistencia y Escáner (QR)
### 3.1 Validación Inteligente
El escáner no solo lee el UUID; realiza un barrido de pre-requisitos:
- **Morosidad**: Bloqueo automático si el estado es `VENCIDO` (salvo prórroga activa).
- **Apto Médico**: Alerta visual si el certificado está vencido.
- **Validación de Horarios**: El alumno solo puede marcar si tiene una clase en el `Cronograma` dentro de una ventana de **+/- 2 horas** de la hora actual. 
- **Modo Paquete**: Si el alumno no tiene horario fijo pero sí "clases disponibles", el sistema descuenta un crédito y permite el ingreso.

## 4. Sincronización Académica
### 4.1 Grado vs Nivel de Acceso
Al procesar un aprobado en la mesa de examen:
1. Se actualiza el `grado` del alumno.
2. El método `Usuario.save()` sincroniza automáticamente el `nivel_acceso` de la biblioteca con el `nivel_desbloqueado` definido en el nuevo `Grado`.

## 5. Políticas de Borrado (Blindaje de Historial)
Se ha implementado `on_delete=models.PROTECT` en relaciones críticas:
- No se puede borrar un alumno si tiene órdenes o pagos (para no romper la contabilidad).
- No se puede borrar un grado si hay alumnos vinculados.

---
**Nota para Desarrolladores:** El sistema utiliza optimización de imágenes WebP automática al subir fotos de perfil para reducir el ancho de banda.
