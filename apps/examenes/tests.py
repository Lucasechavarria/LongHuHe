import pytest
from mixer.backend.django import mixer
from apps.usuarios.models import Usuario, Grado, Examen
from apps.examenes.models import MesaExamen, InscripcionExamen

@pytest.mark.django_db
class TestExamenesModel:
    def test_creacion_mesa(self):
        # En MesaExamen el campo es 'lugar' no 'sede'
        # Y 'examinadores' es ManyToMany
        mesa = mixer.blend(MesaExamen, lugar="Sede Central")
        assert mesa.lugar == "Sede Central"
        assert str(mesa).startswith("Mesa")

    def test_auto_ascenso(self):
        # 1. Crear Grados
        g_blanco = mixer.blend(Grado, nombre="Blanco", orden=0)
        g_amarillo = mixer.blend(Grado, nombre="Amarillo", orden=1)
        
        # 2. Alumno Blanco
        alumno = mixer.blend(Usuario, grado=g_blanco)
        
        # 3. Inscripcion a Examen para Amarillo
        mesa = mixer.blend(MesaExamen)
        inscripcion = mixer.blend(InscripcionExamen, 
                                 alumno=alumno, 
                                 mesa=mesa,
                                 grado_actual=g_blanco,
                                 grado_a_aspirar=g_amarillo, 
                                 resultado=InscripcionExamen.EstadoResultado.PENDIENTE)
        
        # 4. Aprobar
        inscripcion.nota_tecnica = 80
        inscripcion.resultado = InscripcionExamen.EstadoResultado.APROBADO
        # Debe llamar aplicar_ascenso()
        inscripcion.aplicar_ascenso()
        
        alumno.refresh_from_db()
        assert alumno.grado == g_amarillo
        
        # 5. Debe existir el registro historico en Examen (del app usuarios)
        assert Examen.objects.filter(alumno=alumno, grado=g_amarillo).exists()

    def test_reprobar_no_ascender(self):
        g_blanco = mixer.blend(Grado, nombre="Blanco", orden=0)
        g_amarillo = mixer.blend(Grado, nombre="Amarillo", orden=1)
        alumno = mixer.blend(Usuario, grado=g_blanco)
        
        mesa = mixer.blend(MesaExamen)
        inscripcion = mixer.blend(InscripcionExamen, 
                                 alumno=alumno, 
                                 mesa=mesa,
                                 grado_actual=g_blanco,
                                 grado_a_aspirar=g_amarillo, 
                                 resultado=InscripcionExamen.EstadoResultado.PENDIENTE)
                                 
        inscripcion.nota_tecnica = 30
        inscripcion.resultado = InscripcionExamen.EstadoResultado.DESAPROBADO
        # No se aplica ascenso
        
        alumno.refresh_from_db()
        assert alumno.grado == g_blanco
