import pytest
from django.utils import timezone
from apps.usuarios.models import Usuario, Grado
from apps.examenes.models import MesaExamen, InscripcionExamen

@pytest.mark.django_db
def test_ascenso_automatico_al_aprobar():
    """ Task 7.3: Verificar que el ascenso se aplique correctamente al aprobar """
    # 1. Setup inicial (Grados y Alumno)
    blanco = Grado.objects.create(nombre="Blanco", orden=1)
    amarillo = Grado.objects.create(nombre="Amarillo", orden=2)
    alumno = Usuario.objects.create(
        username="alumno_test", 
        nombre="Test", 
        apellido="User", 
        grado=blanco
    )
    
    # 2. Mesa y Inscripción
    mesa = MesaExamen.objects.create(
        fecha=timezone.now(),
        lugar="Sede Central"
    )
    insc = InscripcionExamen.objects.create(
        mesa=mesa,
        alumno=alumno,
        grado_actual=blanco,
        grado_a_aspirar=amarillo,
        resultado=InscripcionExamen.EstadoResultado.PENDIENTE
    )
    
    # 3. Simular Aprobación
    insc.resultado = InscripcionExamen.EstadoResultado.APROBADO
    insc.nota_tecnica = 90
    insc.save()
    
    # 4. Act
    insc.aplicar_ascenso()
    
    # 5. Assert: El grado del alumno debe haber cambiado
    alumno.refresh_from_db()
    assert alumno.grado == amarillo
    assert insc.procesado == True
    
    # 6. Assert: El historial de examen debe haberse creado
    assert alumno.examenes.count() == 1
    assert alumno.examenes.first().grado == amarillo

@pytest.mark.django_db
def test_no_hay_ascenso_si_desaprueba():
    """ Verificar que no se ascienda si el resultado no es APROBADO """
    blanco = Grado.objects.create(nombre="Blanco", orden=1)
    amarillo = Grado.objects.create(nombre="Amarillo", orden=2)
    alumno = Usuario.objects.create(username="alumno_fail", grado=blanco)
    
    mesa = MesaExamen.objects.create(fecha=timezone.now(), lugar="Sede")
    insc = InscripcionExamen.objects.create(
        mesa=mesa, alumno=alumno, grado_actual=blanco, grado_a_aspirar=amarillo, 
        resultado=InscripcionExamen.EstadoResultado.DESAPROBADO
    )
    
    insc.aplicar_ascenso()
    
    alumno.refresh_from_db()
    assert alumno.grado == blanco  # Sigue en blanco
    assert insc.procesado == False
