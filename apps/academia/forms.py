from django import forms
from .models import Torneo

class TorneoForm(forms.ModelForm):
    class Meta:
        model = Torneo
        fields = ['nombre', 'descripcion', 'fecha', 'lugar', 'costo_inscripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'glass-input',
                'placeholder': 'Ej: Torneo Nacional de Tai-Chi 2026',
                'required': True
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'glass-input h-32 resize-none',
                'placeholder': 'Detalles del torneo, categorías, requisitos y horarios...'
            }),
            'fecha': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'glass-input',
                'required': True
            }),
            'lugar': forms.TextInput(attrs={
                'class': 'glass-input',
                'placeholder': 'Ej: Polideportivo Municipal / Dirección',
                'required': True
            }),
            'costo_inscripcion': forms.NumberInput(attrs={
                'class': 'glass-input',
                'placeholder': 'Ej: 2500 (0 si es gratuito)'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'w-6 h-6 bg-white/5 border border-white/10 rounded-lg checked:bg-orange-600 focus:ring-2 focus:ring-orange-500/50 text-orange-500 cursor-pointer'
            }),
        }
