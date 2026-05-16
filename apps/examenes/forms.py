from django import forms
from .models import MesaExamen
from apps.usuarios.models import Usuario

class MesaExamenForm(forms.ModelForm):
    class Meta:
        model = MesaExamen
        fields = ['fecha', 'lugar', 'examinadores', 'maestro_invitado', 'precio_inscripcion']
        widgets = {
            'fecha': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'glass-input'}),
            'lugar': forms.TextInput(attrs={'class': 'glass-input', 'placeholder': 'Ej: Sede Central / Dirección'}),
            'maestro_invitado': forms.TextInput(attrs={'class': 'glass-input', 'placeholder': 'Ej: Maestro Wang (Opcional)'}),
            'precio_inscripcion': forms.NumberInput(attrs={'class': 'glass-input'}),
            'examinadores': forms.SelectMultiple(attrs={'class': 'glass-input h-32'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['examinadores'].queryset = Usuario.objects.filter(es_profe=True)
