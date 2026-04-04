from django import forms
from apps.academia.models import Actividad
from .models import Pago

class PagoTipoForm(forms.Form):
    actividad = forms.ModelChoiceField(
        queryset=Actividad.objects.all(),
        empty_label="Selecciona la actividad",
        widget=forms.Select(attrs={
            'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 focus:border-orange-500 outline-none transition-all shaolin-shadow uppercase font-bold text-center'
        })
    )
    tipo = forms.ChoiceField(
        choices=Pago.TipoPago.choices,
        widget=forms.RadioSelect(attrs={'class': 'hidden pe-none'})
    )
    cantidad_clases = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 outline-none transition-all shaolin-shadow uppercase font-bold text-center',
            'placeholder': '¿Cuántas clases?'
        })
    )

class PagoMetodoForm(forms.Form):
    metodo = forms.ChoiceField(
        choices=Pago.MetodoPago.choices,
        widget=forms.RadioSelect(attrs={'class': 'hidden pe-none'})
    )

class PagoComprobanteForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['comprobante']
        widgets = {
            'comprobante': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-xl text-brown-800 file:mr-6 file:py-4 file:px-8 file:rounded-3xl file:border-0 file:text-xl file:font-black file:bg-orange-500 file:text-white hover:file:bg-orange-600 file:uppercase'
            })
        }
