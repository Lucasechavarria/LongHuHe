en github me da este# 🥋 Shaolin Long Hu He - ERP Marcial Zen Premium

![Licencia](https://img.shields.io/badge/Status-Production--Ready-orange)
![Framework](https://img.shields.io/badge/Django-5.x-092E20)
![Security](https://img.shields.io/badge/MP--Webhook-Secured-blue)
![Architecture](https://img.shields.io/badge/Database-Postgres--Supabase-purple)

## 🧘 Descripción
**Shaolin Long Hu He** es un ecosistema ERP de vanguardia para la gestión integral de academias de artes marciales. Diseñado bajo la estética **"Dark Zen Premium"**, integra finanzas, inventario, progreso académico y control de acceso en una sola experiencia fluida y blindada.

## ✨ Características Implementadas (Producción)
### 🏦 Gestión Financiera y Ventas
- **Checkout Pro de Mercado Pago**: Integración blindada con atomización de base de datos para confirmación automática de pagos.
- **Tienda Oficial**: Catálogo con gestión de **variantes (talles)** y costos de reposición dinámicos.
- **Comisiones Pro/Asis**: Cálculo automático de comisiones para docentes y asistentes por cada venta/clase.
- **Módulo de Descuentos**: Sistema de cupones y becas integradas en el flujo de caja.

### 👥 Gestión de Alumnos y Acceso
- **Carnet Digital QR**: Identificación con generación automática de QR para cada socio.
- **Escáner Inteligente**: Control de asistencia que valida horarios, morosidad y apto médico en tiempo real.
- **Perfil Zen**: Dashboard de alta legibilidad con historial financiero y línea de tiempo marcial.

### 📚 Academia y Biblioteca
- **Dojo Digital**: Acceso restringido a material de estudio (Tao Lu, Reglamento) basado en el nivel marcial del alumno.
- **Exámenes y Ascensos**: Ciclo completo de inscripción, evaluación y ascenso automático de grado/acceso.
- **Sincronización Marcial**: Los permisos de la biblioteca se actualizan automáticamente al aprobar exámenes.

## 🛠️ Stack Tecnológico
- **Core**: Django 5.x (Python) - Arquitectura defensiva.
- **Frontend**: Tailwind CSS + Alpine.js (Glassmorphism UI).
- **Backend de Media**: Cloudinary / S3 + Pillow (Optimización WebP automática).
- **Notificaciones**: Integración con servicios de mensajería (Próximamente).

## 🚀 Despliegue Rápido
1. Clonar el repositorio.
2. Configurar `.env` con las claves de `SUPABASE`, `MERCADO_PAGO_TOKEN` y `CLOUDINARY`.
3. Ejecutar `python manage.py migrate`.
4. Iniciar con `python manage.py rundev` (o servidor de producción).

---
*Para detalles sobre la lógica de seguridad y finanzas, consulte el [Manual Técnico](DOCUMENTACION_TECNICA.md).*

Creado con honor para **Long Hu He** 🌑🚀
