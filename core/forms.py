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
        label="¿A qué actividad quieres inscribirte?",
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
                'placeholder': 'Ej: 1112345678',
                'type': 'tel',
                'pattern': '[0-9]*',
                'inputmode': 'numeric'
            }),
            'dni': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: 12345678',
                'pattern': '[0-9]*',
                'inputmode': 'numeric'
            }),
            'fecha_nacimiento': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 focus:border-orange-500 outline-none transition-all shaolin-shadow font-bold text-center',
                'placeholder': 'DD/MM/AAAA',
                'inputmode': 'numeric'
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

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre and any(char.isdigit() for char in nombre):
            raise forms.ValidationError("El nombre no debe contener números.")
        return nombre

    def clean_apellido(self):
        apellido = self.cleaned_data.get('apellido')
        if apellido and any(char.isdigit() for char in apellido):
            raise forms.ValidationError("El apellido no debe contener números.")
        return apellido

    def clean_celular(self):
        celular = self.cleaned_data.get('celular')
        if celular:
            celular = celular.replace(" ", "").replace("-", "")
            if not celular.isdigit():
                raise forms.ValidationError("El celular debe contener solo números.")
            if len(celular) > 20:
                raise forms.ValidationError("El celular no puede tener más de 20 dígitos.")
        return celular

    def clean_fecha_nacimiento(self):
        fecha_str = self.cleaned_data.get('fecha_nacimiento')
        if not fecha_str:
            return None
        
        # Si ya es un objeto date (poco probable con TextInput pero por las dudas)
        from datetime import datetime, date
        if isinstance(fecha_str, date):
            return fecha_str
        
        try:
            # Intentamos parsear el formato DD/MM/AAAA
            return datetime.strptime(fecha_str, '%d/%m/%Y').date()
        except (ValueError, TypeError):
            raise forms.ValidationError("Usa el formato DD/MM/AAAA (ej: 15/05/1980)")

    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        if dni:
            dni = dni.replace(".", "").replace("-", "").replace(" ", "")
            if not dni.isdigit():
                raise forms.ValidationError("El DNI debe contener solo números.")
            if len(dni) > 8:
                raise forms.ValidationError("El DNI no puede tener más de 8 dígitos.")
        return dni


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
