from decimal import Decimal
from django.db import transaction, models
from django.utils import timezone
from apps.ventas.models import Pago, CierreCaja
from django.core.files.base import ContentFile
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

class TesoreriaService:
    """
    Servicio encargado de la gestión contable, cierres de caja y reportes financieros.
    """

    @staticmethod
    def generar_pdf_tesoreria(mes, anio):
        """
        Genera un reporte PDF de los ingresos del mes.
        """
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        p.setFont("Helvetica-Bold", 16)
        p.drawString(2*cm, height - 2*cm, "REPORTE DE TESORERIA - ASOCIACION LONG HU HE")
        p.setFont("Helvetica", 12)
        p.drawString(2*cm, height - 3*cm, f"Período: {mes}/{anio}")

        pagos = Pago.objects.filter(
            estado=Pago.EstadoPago.APROBADO,
            fecha_registro__month=mes,
            fecha_registro__year=anio
        ).select_related('alumno', 'actividad')

        y = height - 4.5*cm
        p.setFont("Helvetica-Bold", 10)
        p.drawString(2*cm, y, "ALUMNO")
        p.drawString(7*cm, y, "ACTIVIDAD")
        p.drawString(11*cm, y, "METODO")
        p.drawString(15*cm, y, "MONTO")
        y -= 0.6*cm
        p.line(2*cm, y+0.1*cm, width-2*cm, y+0.1*cm)

        p.setFont("Helvetica", 9)
        total = Decimal('0.00')
        for pago in pagos:
            if y < 2*cm:
                p.showPage()
                y = height - 2*cm
            
            p.drawString(2*cm, y, str(pago.alumno.nombre_completo)[:25])
            p.drawString(7*cm, y, str(pago.actividad.nombre if pago.actividad else "Mensualidad")[:20])
            p.drawString(11*cm, y, pago.get_metodo_display())
            p.drawString(15*cm, y, f"$ {pago.monto}")
            total += pago.monto
            y -= 0.5*cm

        y -= 1*cm
        p.line(2*cm, y+0.5*cm, width-2*cm, y+0.5*cm)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(11*cm, y, "TOTAL INGRESOS:")
        p.drawString(15*cm, y, f"$ {total}")

        p.showPage()
        p.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    @transaction.atomic
    def cerrar_mes(usuario_operador):
        """
        Realiza el cierre formal del mes actual.
        """
        hoy = timezone.now()
        mes = hoy.month
        anio = hoy.year

        if CierreCaja.objects.filter(mes=mes, anio=anio).exists():
            raise ValueError(f"Ya existe un cierre guardado para {mes}/{anio}.")

        # 1. Calcular total
        total = Pago.objects.filter(
            estado=Pago.EstadoPago.APROBADO,
            fecha_registro__month=mes,
            fecha_registro__year=anio
        ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0.00')

        # 2. Generar PDF
        pdf_buffer = TesoreriaService.generar_pdf_tesoreria(mes, anio)

        # 3. Crear registro
        cierre = CierreCaja.objects.create(
            mes=mes,
            anio=anio,
            total_recaudado=total,
            usuario_genero=usuario_operador
        )
        
        filename = f"cierre_{anio}_{mes}.pdf"
        cierre.archivo_pdf.save(filename, ContentFile(pdf_buffer.getvalue()))
        
        return cierre
