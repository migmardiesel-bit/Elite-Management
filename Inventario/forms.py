from django import forms
from .models import Producto, Movimiento, Proveedor, Destino

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'contacto', 'telefono', 'email', 'direccion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'contacto': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class DestinoForm(forms.ModelForm):
    class Meta:
        model = Destino
        fields = ['nombre', 'direccion', 'encargado', 'tipo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'encargado': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['codigo', 'nombre', 'categoria', 'precio_costo', 'precio_venta', 'proveedor', 'stock_minimo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select select2'}),
            'precio_costo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio_venta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'proveedor': forms.Select(attrs={'class': 'form-select select2'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ['producto', 'tipo', 'cantidad', 'fecha', 'origen', 'destino', 'razon_ajuste']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select select2'}),
            'tipo': forms.Select(attrs={'class': 'form-select select2', 'id': 'id_tipo'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'origen': forms.Select(attrs={'class': 'form-select select2', 'id': 'id_origen'}),
            'destino': forms.Select(attrs={'class': 'form-select select2', 'id': 'id_destino'}),
            'razon_ajuste': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        origen = cleaned_data.get('origen')
        destino = cleaned_data.get('destino')
        
        # Validaciones

        # ADJUSTMENT POSITIVO (+)
        if tipo == 'ADJ_POS' and not destino:
            self.add_error('destino', 'Para sumar stock (+), selecciona el SITIO en el campo "Destino".')

        # ADJUSTMENT NEGATIVO (-)
        if tipo == 'ADJ_NEG' and not origen:
            self.add_error('origen', 'Para restar stock (-), selecciona el SITIO en el campo "Origen".')

        # ENTRADA (COMPRA)
        if tipo == 'IN' and not destino:
            self.add_error('destino', 'Para una Entrada, indica en qué bodega entrará (Destino).')

        # SALIDA (VENTA) O REEMPLAZO
        if (tipo == 'OUT' or tipo == 'REPLACEMENT') and not origen:
            self.add_error('origen', 'Selecciona la bodega de donde sale el producto (Origen).')

        # TRANSFERENCIA
        if tipo == 'TRANSFER':
            if not origen: self.add_error('origen', 'Selecciona desde dónde sale.')
            if not destino: self.add_error('destino', 'Selecciona hacia dónde va.')
            if origen and destino and origen == destino:
                self.add_error('destino', 'El origen y el destino no pueden ser el mismo sitio.')

        return cleaned_data