from django import forms
from .models import Usuario, Locacion, Pago

class AlumnoOnboardingForm(forms.ModelForm):
    """
    Formulario inicial para identificar al alumno.
    Sin contraseña, pensado para sencillez absoluta.
    """
    from .models import Actividad
    actividad_inicial = forms.ModelChoiceField(
        queryset=Actividad.objects.all(),
        label="Actividad que vas a realizar",
        empty_label="Selecciona una actividad",
        widget=forms.Select(attrs={
            'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 focus:border-orange-500 focus:bg-white outline-none transition-all shaolin-shadow uppercase font-bold'
        }),
        error_messages={'required': 'Dime qué actividad quieres practicar.'}
    )

    class Meta:
        model = Usuario
        fields = ['nombre', 'apellido', 'celular', 'dni', 'fecha_nacimiento', 'domicilio', 'localidad', 'locacion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 focus:bg-white outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: Juan'
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 focus:bg-white outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: Pérez'
            }),
            'celular': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 focus:bg-white outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: 11 1234 5678'
            }),
            'dni': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: 12.345.678'
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 focus:border-orange-500 outline-none transition-all shaolin-shadow font-bold',
                'type': 'date'
            }),
            'domicilio': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: Av. Rivadavia 1234'
            }),
            'localidad': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: CABA'
            }),
            'locacion': forms.Select(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 focus:border-orange-500 focus:bg-white outline-none transition-all shaolin-shadow uppercase font-bold'
            }),
        }
        error_messages = {
            'nombre': {'required': 'Por favor, escribe tu nombre.'},
            'apellido': {'required': 'Por favor, escribe tu apellido.'},
            'celular': {
                'required': 'Necesitamos tu celular para identificarte.',
                'unique': 'Este número ya está registrado.'
            },
            'dni': {'required': 'El DNI es necesario para el seguro.'},
            'fecha_nacimiento': {'required': 'Ingresa tu fecha de nacimiento.'},
            'domicilio': {'required': 'Falta tu dirección.'},
            'localidad': {'required': 'Dinos en qué localidad vives.'},
            'locacion': {'required': 'Selecciona dónde vas a tomar las clases.'},
        }


class PagoTipoForm(forms.Form):
    """
    Paso 1: ¿Qué vas a pagar?
    """
    from .models import Actividad
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
    """
    Paso 2: ¿Cómo vas a pagar?
    """
    metodo = forms.ChoiceField(
        choices=Pago.MetodoPago.choices,
        widget=forms.RadioSelect(attrs={'class': 'hidden pe-none'})
    )


class PagoComprobanteForm(forms.ModelForm):
    """
    Paso 3: Sube tu comprobante (si aplica).
    """
    class Meta:
        model = Pago
        fields = ['comprobante']
        widgets = {
            'comprobante': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-xl text-brown-800 file:mr-6 file:py-4 file:px-8 file:rounded-3xl file:border-0 file:text-xl file:font-black file:bg-orange-500 file:text-white hover:file:bg-orange-600 file:uppercase'
            })
        }
