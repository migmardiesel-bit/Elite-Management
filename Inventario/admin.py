from django.contrib import admin
from .models import Proveedor, Destino, Producto, Movimiento, Inventario

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'contacto', 'telefono', 'email')
    search_fields = ('nombre', 'contacto')

@admin.register(Destino)
class DestinoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'encargado', 'direccion')
    search_fields = ('nombre', 'encargado')

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # Aquí cambiamos 'stock_actual' por 'stock_total_global'
    list_display = ('codigo', 'nombre', 'categoria', 'precio_venta', 'stock_total_global')
    list_filter = ('categoria', 'proveedor')
    search_fields = ('codigo', 'nombre', 'descripcion')
    # Importante: el campo de solo lectura también se llama diferente ahora
    readonly_fields = ('stock_total_global',)

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    # Esta tabla te dejará ver stock por ubicación específica
    list_display = ('producto', 'ubicacion', 'cantidad')
    list_filter = ('ubicacion', 'producto__categoria')
    search_fields = ('producto__nombre', 'ubicacion__nombre')

@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ('referencia', 'fecha', 'tipo', 'producto', 'cantidad', 'origen', 'destino', 'usuario')
    list_filter = ('tipo', 'fecha', 'origen', 'destino')
    search_fields = ('referencia', 'producto__nombre')
    date_hierarchy = 'fecha'