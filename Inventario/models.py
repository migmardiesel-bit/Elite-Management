from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid

# --- PROVEEDOR ---
class Proveedor(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre Empresa / Proveedor")
    contacto = models.CharField(max_length=100, blank=True, verbose_name="Persona de Contacto")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, verbose_name="Email")
    direccion = models.TextField(blank=True, verbose_name="Dirección Física")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

# --- DESTINO (SITIOS) ---
class Destino(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Sitio / Identificador")
    direccion = models.CharField(max_length=200, verbose_name="Dirección Completa")
    encargado = models.CharField(max_length=100, blank=True, verbose_name="Encargado / Manager")
    tipo = models.CharField(max_length=50, blank=True, verbose_name="Tipo", help_text="Ej: Apto, Bodega")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Destino / Sitio"
        verbose_name_plural = "Destinos / Sitios"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

# --- PRODUCTO ---
class Producto(models.Model):
    CATEGORIAS = [
        ('Kitchen', 'Kitchen'),
        ('Livingroom', 'Living Room'),
        ('Bedroom', 'Bedroom'),
        ('Bathroom', 'Bathroom'),
        ('Maintenance', 'Maintenance / Tools'),
        ('Other', 'Other'),
    ]

    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código Único")
    nombre = models.CharField(max_length=200, verbose_name="Descripción / Nombre")
    categoria = models.CharField(max_length=50, choices=CATEGORIAS, verbose_name="Zona de Uso")
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo ($)")
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Venta ($)")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    
    stock_total_global = models.IntegerField(default=0, editable=False, verbose_name="Stock Total (Global)")
    stock_minimo = models.IntegerField(default=5, verbose_name="Stock Mínimo (Reorden)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def valor_total(self):
        if self.stock_total_global is None or self.precio_venta is None: return 0
        return self.stock_total_global * self.precio_venta

    @property
    def estado_stock(self):
        if self.stock_total_global <= 0: return 'CRITICO'
        elif self.stock_total_global <= self.stock_minimo: return 'BAJO'
        return 'OPTIMO'
    
    @property
    def stock_global(self):
        return self.stock_total_global

# --- INVENTARIO ---
class Inventario(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='inventarios')
    ubicacion = models.ForeignKey(Destino, on_delete=models.CASCADE, related_name='inventario_sitio')
    cantidad = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('producto', 'ubicacion')
        verbose_name = "Inventario por Sitio"
        verbose_name_plural = "Inventario por Sitios"

    def __str__(self):
        return f"{self.producto.nombre} en {self.ubicacion.nombre}: {self.cantidad}"

# --- MOVIMIENTO ---
class Movimiento(models.Model):
    TIPO_MOVIMIENTO = [
        ('IN', 'Entry (Purchase/Income)'),
        ('OUT', 'Exit (Usage/Sale)'),
        ('REPLACEMENT', 'Exit (Replacement/Swap)'),
        ('TRANSFER', 'Transfer (Between Sites)'),
        ('ADJ_POS', 'Adjustment (+)'),
        ('ADJ_NEG', 'Adjustment (-)'),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO)
    cantidad = models.PositiveIntegerField()
    fecha = models.DateField(default=timezone.now)
    referencia = models.CharField(max_length=50, blank=True, unique=True, editable=False)
    
    origen = models.ForeignKey(Destino, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_salida', verbose_name="Desde (Origen)")
    destino = models.ForeignKey(Destino, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_entrada', verbose_name="Hacia (Destino)")
    
    razon_ajuste = models.TextField(blank=True, null=True)
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        # 1. Generar Referencia
        if not self.referencia:
            prefijo = "MOV"
            if self.tipo == 'IN': prefijo = "IN"
            elif self.tipo == 'OUT': prefijo = "OUT"
            elif self.tipo == 'REPLACEMENT': prefijo = "REP"
            elif self.tipo == 'TRANSFER': prefijo = "TRF"
            elif self.tipo == 'ADJ_POS': prefijo = "ADJ+"
            elif self.tipo == 'ADJ_NEG': prefijo = "ADJ-"
            self.referencia = f"{prefijo}-{timezone.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

        # 2. Lógica de Inventario (Solo si es nuevo)
        if not self.pk: 
            
            # === CASO 1: ENTRADAS (IN) ===
            if self.tipo == 'IN':
                if self.destino:
                    inv_destino, created = Inventario.objects.get_or_create(
                        producto=self.producto, 
                        ubicacion=self.destino
                    )
                    inv_destino.cantidad += self.cantidad
                    inv_destino.save()

            # === CASO 2: SALIDAS (OUT) O REEMPLAZOS (REPLACEMENT) ===
            elif self.tipo == 'OUT' or self.tipo == 'REPLACEMENT':
                if self.origen:
                    try:
                        inv_origen = Inventario.objects.get(producto=self.producto, ubicacion=self.origen)
                        if inv_origen.cantidad < self.cantidad:
                            raise ValidationError(f"Stock insuficiente en {self.origen.nombre}. Disponibles: {inv_origen.cantidad}")
                        inv_origen.cantidad -= self.cantidad
                        inv_origen.save()
                    except Inventario.DoesNotExist:
                        raise ValidationError(f"No hay stock de este producto en {self.origen.nombre}.")
                else:
                    raise ValidationError("Debes seleccionar el Origen (From) para salidas o reemplazos.")

            # === CASO 3: AJUSTE POSITIVO (+) ===
            elif self.tipo == 'ADJ_POS':
                if self.destino:
                    inv_destino, created = Inventario.objects.get_or_create(
                        producto=self.producto, 
                        ubicacion=self.destino
                    )
                    inv_destino.cantidad += self.cantidad
                    inv_destino.save()
                else:
                    raise ValidationError("Para Ajuste Positivo, selecciona el Destino.")

            # === CASO 4: AJUSTE NEGATIVO (-) ===
            elif self.tipo == 'ADJ_NEG':
                if self.origen:
                    try:
                        inv_origen = Inventario.objects.get(producto=self.producto, ubicacion=self.origen)
                        if inv_origen.cantidad < self.cantidad:
                            raise ValidationError(f"No puedes restar {self.cantidad}. Solo hay {inv_origen.cantidad}.")
                        inv_origen.cantidad -= self.cantidad
                        inv_origen.save()
                    except Inventario.DoesNotExist:
                        raise ValidationError(f"No existe inventario en {self.origen.nombre}.")
                else:
                    raise ValidationError("Para Ajuste Negativo, selecciona el Origen.")

            # === CASO 5: TRANSFERENCIAS ===
            elif self.tipo == 'TRANSFER':
                if self.origen and self.destino:
                    # Restar Origen
                    try:
                        inv_origen = Inventario.objects.get(producto=self.producto, ubicacion=self.origen)
                        if inv_origen.cantidad < self.cantidad:
                            raise ValidationError(f"Stock insuficiente en origen ({self.origen.nombre}).")
                        inv_origen.cantidad -= self.cantidad
                        inv_origen.save()
                    except Inventario.DoesNotExist:
                        raise ValidationError(f"No hay inventario en {self.origen.nombre}.")

                    # Sumar Destino
                    inv_destino, created = Inventario.objects.get_or_create(
                        producto=self.producto, 
                        ubicacion=self.destino
                    )
                    inv_destino.cantidad += self.cantidad
                    inv_destino.save()

            # 3. Recalcular Stock Global
            total_real = 0
            inventarios = Inventario.objects.filter(producto=self.producto)
            for inv in inventarios:
                total_real += inv.cantidad
            
            self.producto.stock_total_global = total_real
            self.producto.save()

        super().save(*args, **kwargs)

# --- NUEVOS MODELOS PARA LISTA DE COMPRAS ---
class ListaCompra(models.Model):
    ESTADOS = [
        ('PENDING', 'Pending Purchase'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id_lista = models.CharField(max_length=50, unique=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDING')
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    nota = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.id_lista:
            # Format: SHOP-YYMMDD-UUID (Short)
            self.id_lista = f"SHOP-{timezone.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id_lista} ({self.get_estado_display()})"

class ItemLista(models.Model):
    lista = models.ForeignKey(ListaCompra, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad_sugerida = models.PositiveIntegerField(default=1)
    comprado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad_sugerida}"