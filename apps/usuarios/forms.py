from django import forms
from .models import Usuario
from apps.academia.models import Actividad

class AlumnoOnboardingForm(forms.ModelForm):
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
        fields = [
            'nombre', 'apellido', 'celular', 'dni', 
            'fecha_nacimiento', 'domicilio', 'localidad', 
            'sede', 'actividad_inicial', 'foto_perfil'
        ]
        widgets = {
            'foto_perfil': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-xl text-brown-800 file:mr-6 file:py-4 file:px-8 file:rounded-3xl file:border-0 file:text-xl file:font-black file:bg-orange-500 file:text-white hover:file:bg-orange-600 file:uppercase',
                'x-model': 'foto_perfil'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 focus:bg-white outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: Juan',
                'x-model': 'nombre'
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 focus:bg-white outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: Pérez',
                'x-model': 'apellido'
            }),
            'celular': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 focus:bg-white outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: 1112345678',
                'type': 'tel',
                'pattern': '[0-9]*',
                'inputmode': 'numeric',
                'x-model': 'celular'
            }),
            'dni': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: 12345678',
                'pattern': '[0-9]*',
                'inputmode': 'numeric',
                'x-model': 'dni'
            }),
            'fecha_nacimiento': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 focus:border-orange-500 outline-none transition-all shaolin-shadow font-bold text-center',
                'placeholder': 'DD/MM/AAAA',
                'inputmode': 'numeric',
                'x-model': 'fecha_nacimiento'
            }),
            'domicilio': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: Av. Rivadavia 1234',
                'x-model': 'domicilio'
            }),
            'localidad': forms.TextInput(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 placeholder-brown-800/40 focus:border-orange-500 outline-none transition-all shaolin-shadow uppercase font-bold',
                'placeholder': 'Ej: CABA',
                'x-model': 'localidad'
            }),
            'sede': forms.Select(attrs={
                'class': 'w-full rounded-3xl bg-cream-50 border-4 border-brown-700/20 p-6 text-2xl text-brown-950 focus:border-orange-500 focus:bg-white outline-none transition-all shaolin-shadow uppercase font-bold',
                'x-model': 'sede'
            }),
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
        from datetime import datetime, date
        if isinstance(fecha_str, date):
            return fecha_str
        try:
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

class UsuarioPerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['foto_perfil', 'domicilio', 'localidad']
        widgets = {
            'foto_perfil': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-sm text-white file:mr-4 file:py-3 file:px-6 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-orange-500 file:text-white hover:file:bg-orange-600'
            }),
            'domicilio': forms.TextInput(attrs={
                'class': 'w-full rounded-2xl bg-white/5 border border-white/10 p-4 text-white focus:border-orange-500 outline-none transition-all'
            }),
            'localidad': forms.TextInput(attrs={
                'class': 'w-full rounded-2xl bg-white/5 border border-white/10 p-4 text-white focus:border-orange-500 outline-none transition-all'
            }),
        }
