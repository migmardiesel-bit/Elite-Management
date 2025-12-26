from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView
from django.db.models import Avg, Max, Min, Sum, F, Q, Count
import statistics 
import urllib.parse # <--- AGREGA ESTO AL PRINCIPIO DEL ARCHIVO SI NO ESTÁ
from django.urls import reverse_lazy
from django.core.exceptions import ValidationError
from django.utils import timezone 
from .models import Producto, Movimiento, Proveedor, Destino, Inventario, ListaCompra, ItemLista
from django.views.generic import ListView, CreateView, UpdateView
from .forms import ProductoForm, MovimientoForm, ProveedorForm, DestinoForm
import csv
import json
from django.conf import settings
import uuid  # <--- ESTA ERA LA LIBRERÍA QUE FALTABA
from datetime import timedelta
from openai import OpenAI
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .utils import create_google_calendar_event # Asegúrate de tener utils.py creado

# ==============================================================================
# ELITE BRAIN: ARTIFICIAL INTELLIGENCE MODULE (ENGLISH VERSION)
# ==============================================================================

class EliteIntelligenceService:
    """
    Advanced Business Intelligence Service.
    Language: ENGLISH (Output) / MULTI-LANGUAGE (Input).
    Capabilities: Financial Analysis, Operational Audit, Report Generation.
    """

    def __init__(self, user):
        self.user = user
        self.today = timezone.now().date()
        self.client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )

    def _get_financial_metrics(self):
        """Generates deep financial analysis."""
        total_assets = sum(p.valor_total for p in Producto.objects.all())
        
        start_month = self.today - timedelta(days=30)
        expenses_30d = Movimiento.objects.filter(
            tipo__in=['OUT', 'REPLACEMENT'],
            fecha__gte=start_month
        ).aggregate(total=Sum(F('cantidad') * F('producto__precio_venta')))['total'] or 0

        # Historical Total Expenses
        expenses_historical = Movimiento.objects.filter(
            tipo__in=['OUT', 'REPLACEMENT']
        ).aggregate(total=Sum(F('cantidad') * F('producto__precio_venta')))['total'] or 0

        top_units_query = Movimiento.objects.filter(
            tipo__in=['OUT', 'REPLACEMENT'], 
            destino__isnull=False
        ).values('destino__nombre', 'destino__tipo').annotate(
            total_expense=Sum(F('cantidad') * F('producto__precio_venta'))
        ).order_by('-total_expense')[:5]

        top_units = [
            f"- {u['destino__nombre']} ({u['destino__tipo']}): ${u['total_expense']:,.2f}" 
            for u in top_units_query
        ]

        return {
            "total_assets": total_assets,
            "expenses_30d": expenses_30d,
            "expenses_historical": expenses_historical,
            "top_units_list": top_units
        }

    def _get_inventory_health(self):
        """Inventory Health Diagnostics."""
        critical = Producto.objects.filter(stock_total_global__lte=0)
        low_stock = Producto.objects.filter(stock_total_global__lte=F('stock_minimo'), stock_total_global__gt=0)
        
        top_value = Producto.objects.annotate(
            val=F('stock_total_global') * F('precio_venta')
        ).order_by('-val')[:5]

        return {
            "critical_count": critical.count(),
            "critical_names": [p.nombre for p in critical[:5]],
            "low_stock_count": low_stock.count(),
            "top_value": [f"{p.nombre}: ${p.valor_total:,.2f}" for p in top_value]
        }

    def _get_operational_logs(self):
        """Operational Audit Logs."""
        movs_today = Movimiento.objects.filter(fecha=self.today).select_related('usuario', 'producto').order_by('-id')
        details_today = []
        for m in movs_today[:8]:
            details_today.append(
                f"[{m.fecha.strftime('%H:%M')}] {m.get_tipo_display()}: {m.cantidad}x {m.producto.nombre} "
                f"(User: {m.usuario.username if m.usuario else 'System'})"
            )
        return {"total_today": movs_today.count(), "details": details_today}

    def _detect_intent(self, query):
        """
        Heuristic Intent Detection.
        Understands both English and Spanish keywords.
        """
        query = query.lower()
        intents = []
        
        # Keywords (Mixed English/Spanish to understand user input)
        kw_finance = ['dinero', 'costo', 'gasto', 'valor', 'precio', 'money', 'cost', 'expense', 'price', 'budget', 'financi']
        kw_inventory = ['stock', 'cantidad', 'falta', 'sobra', 'producto', 'inventory', 'warehouse', 'bodega', 'item']
        kw_ops = ['quien', 'cuando', 'movimiento', 'who', 'when', 'movement', 'log', 'user', 'usuario']

        if any(k in query for k in kw_finance): intents.append('finance')
        if any(k in query for k in kw_inventory): intents.append('inventory')
        if any(k in query for k in kw_ops): intents.append('ops')
        
        if not intents: return ['finance', 'inventory', 'ops']
        return intents

    def build_context(self, user_query, chat_history):
        """
        Builds the System Prompt in English.
        """
        intents = self._detect_intent(user_query)
        context_parts = []
        
        fin_data = self._get_financial_metrics()
        inv_data = self._get_inventory_health()
        ops_data = self._get_operational_logs()

        # System Header
        context_parts.append(
            f"CURRENT DATE: {self.today.strftime('%Y-%m-%d')}\n"
            f"USER: {self.user.username}\n"
            "ROLE: You are 'Elite AI', a Senior Financial & Logistics Analyst. "
            "Your language is ENGLISH. You can read/understand Spanish input, but you must ALWAYS REPLY IN ENGLISH. "
            "Be professional, concise, and data-driven.\n"
        )

        # 1. Financial Data Injection
        if 'finance' in intents:
            context_parts.append(
                "\n--- 💰 FINANCIAL REPORT ---\n"
                f"* Total Assets Value (Inventory): ${fin_data['total_assets']:,.2f}\n"
                f"* Historical Total Expenses: ${fin_data['expenses_historical']:,.2f}\n"
                f"* Expenses (Last 30 Days): ${fin_data['expenses_30d']:,.2f}\n"
                "* Top 5 Most Expensive Units (Cost Centers):\n" + "\n".join(fin_data['top_units_list'])
            )

        # 2. Inventory Data Injection
        if 'inventory' in intents:
            context_parts.append(
                "\n--- 📦 INVENTORY HEALTH ---\n"
                f"* Critical Items (Out of Stock): {inv_data['critical_count']} "
                f"(e.g., {', '.join(inv_data['critical_names'])})\n"
                f"* Low Stock Items: {inv_data['low_stock_count']}\n"
                "* Top 5 High Value Items:\n" + "\n  ".join(inv_data['top_value'])
            )

        # 3. Operational Data Injection
        if 'ops' in intents:
            context_parts.append(
                "\n--- ⚙️ OPERATIONAL LOGS ---\n"
                f"* Movements Today: {ops_data['total_today']}\n"
                "* Recent Logs (Today):\n" + "\n".join(ops_data['details'])
            )

        # 4. EXCEL GENERATION MANUAL (ENGLISH)
        context_parts.append(
            "\n=== EXCEL REPORT GENERATION MANUAL ===\n"
            "If the user asks to download, generate, or export an Excel file (even in Spanish), generate a Markdown link using this structure:\n"
            "Base URL: `/reportes/financiero/?export=excel_financiero`\n"
            "Parameters:\n"
            "1. `type=salidas_detalladas` -> For general logs, detailed movements.\n"
            "2. `type=unidades` -> For costs by Unit, Apartment, or Site.\n"
            "3. `type=por_referencia` -> For costs grouped by Operation Reference.\n"
            "4. `start_date=YYYY-MM-DD` & `end_date=YYYY-MM-DD` -> Optional filters.\n\n"
            "RESPONSE EXAMPLES:\n"
            "- User: 'Quiero un excel de gastos por unidad'\n"
            "  You: 'Here is the report requested: [Download Unit Cost Report](/reportes/financiero/?export=excel_financiero&type=unidades)'\n"
        )

        # 5. Conversation Memory
        if chat_history:
            context_parts.append("\n--- 🧠 RECENT CHAT HISTORY ---")
            for msg in chat_history[-2:]:
                role = "User" if msg['role'] == 'user' else "Elite AI"
                context_parts.append(f"{role}: {msg['content']}")

        return "\n".join(context_parts)

    def ask_deepseek(self, system_context, user_question):
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_context},
                    {"role": "user", "content": user_question},
                ],
                temperature=0.3,
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Critical AI Error: {str(e)}"

# --- API ENDPOINT ---
@csrf_exempt
@login_required
def chat_inventario(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        pregunta_usuario = data.get('pregunta', '').strip()

        if not pregunta_usuario:
            return JsonResponse({'status': 'error', 'message': 'Empty query'})

        # Session Memory
        historial = request.session.get('elite_chat_history', [])
        
        # AI Processing
        ai_service = EliteIntelligenceService(request.user)
        system_context = ai_service.build_context(pregunta_usuario, historial)
        respuesta_ia = ai_service.ask_deepseek(system_context, pregunta_usuario)

        # Update History
        historial.append({'role': 'user', 'content': pregunta_usuario})
        historial.append({'role': 'ai', 'content': respuesta_ia})
        request.session['elite_chat_history'] = historial[-6:]

        return JsonResponse({'status': 'success', 'respuesta': respuesta_ia})

    except Exception as e:
        print(f"AI ERROR: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# --- (MANTÉN TUS OTRAS VISTAS AQUÍ: dashboard, reportes, productos...) ---
# --- NO BORRES LAS VISTAS EXISTENTES, SOLO REEMPLAZA LA CLASE Y LA FUNCIÓN DE CHAT ARRIBA ---

# ... dashboard code ...
@login_required
def dashboard(request):
    """
    Dashboard Principal:
    - Métricas KPIs.
    - Gráfica de Categorías (Dona).
    - Lista Resumen de Valor por Bodega (Solicitud Anthony).
    - Chatbot IA.
    """
    # 1. DATOS GENERALES
    productos = Producto.objects.all()
    # Calculamos el valor total sumando la propiedad valor_total de cada producto
    valor_inventario = sum(p.valor_total for p in productos)
    
    alertas = productos.filter(stock_total_global__lte=F('stock_minimo')).count()
    productos_bajo_stock = productos.filter(stock_total_global__lte=F('stock_minimo'))[:5]
    ultimos_movimientos = Movimiento.objects.select_related('producto', 'origen', 'destino', 'usuario').order_by('-fecha', '-id')[:10]

    # 2. LOGICA DE EXPORTACIÓN (EXCEL)
    if request.GET.get('export') == 'dashboard_excel':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Elite_Dashboard_Report.csv"'
        writer = csv.writer(response)

        writer.writerow(['--- GENERAL METRICS ---'])
        writer.writerow(['Total Products', productos.count()])
        writer.writerow(['Total Inventory Value ($)', valor_inventario])
        writer.writerow(['Low Stock Alerts', alertas])
        writer.writerow([])

        writer.writerow(['--- CRITICAL STOCK ALERTS ---'])
        writer.writerow(['Code', 'Product', 'Current Stock', 'Min Stock', 'Category'])
        for p in productos.filter(stock_total_global__lte=F('stock_minimo')):
            writer.writerow([p.codigo, p.nombre, p.stock_total_global, p.stock_minimo, p.categoria])
            
        return response

    # 3. DATOS PARA GRÁFICA DE PASTEL/DONA (Categorías)
    data_categorias = Producto.objects.values('categoria').annotate(total=Count('id')).order_by('-total')
    labels_cat = [item['categoria'] for item in data_categorias]
    data_cat = [item['total'] for item in data_categorias]

    # 4. DATOS PARA LISTA RESUMEN (Valor por Bodega)
    # En lugar de mandar arrays para Chart.js, mandamos una lista de diccionarios para la tabla HTML
    destinos = Destino.objects.all()
    bodegas_summary = []
    
    for d in destinos:
        items = Inventario.objects.filter(ubicacion=d)
        valor_sitio = sum(i.cantidad * i.producto.precio_venta for i in items)
        
        # Solo agregamos si hay algo relevante (valor o items)
        if valor_sitio > 0 or items.exists():
            bodegas_summary.append({
                'name': d.nombre,
                'type': d.tipo,
                'total_items': items.count(),
                'value': float(valor_sitio) # Float para evitar errores de serialización si fuera necesario
            })
            
    # Ordenamos la lista: Bodegas con más valor primero
    bodegas_summary.sort(key=lambda x: x['value'], reverse=True)

    context = {
        'total_productos': productos.count(),
        'valor_inventario': valor_inventario,
        'alertas_bajo_stock': alertas,
        'ultimos_movimientos': ultimos_movimientos,
        'productos_bajo_stock': productos_bajo_stock,
        'movimientos_hoy': Movimiento.objects.filter(fecha=timezone.now().date()).count(),
        
        # Datos JSON para la Gráfica de Dona (Izquierda)
        'chart_cat_labels': json.dumps(labels_cat),
        'chart_cat_data': json.dumps(data_cat),
        
        # Datos para la Lista Resumen (Derecha)
        'bodegas_summary': bodegas_summary,
    }
    return render(request, 'Inventario/dashboard.html', context)

# --- Productos ---
class ProductoListView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = 'Inventario/producto_list.html'
    context_object_name = 'productos'
    paginate_by = 15

    def get_queryset(self):
        queryset = Producto.objects.prefetch_related('inventarios', 'inventarios__ubicacion').all().order_by('nombre')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(codigo__icontains=query) | 
                Q(nombre__icontains=query) | 
                Q(proveedor__nombre__icontains=query)
            )
        categoria = self.request.GET.get('categoria')
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        return queryset
        
    def get(self, request, *args, **kwargs):
        if request.GET.get('export') == 'excel':
            productos = self.get_queryset()
            bodegas = Destino.objects.all().order_by('nombre')

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="Global_Inventory_Report.csv"'
            writer = csv.writer(response)

            header = ['Code', 'Product Name', 'Category', 'Sale Price', 'Global Stock', 'Total Value']
            for bodega in bodegas:
                header.append(f"Stock: {bodega.nombre}")
            writer.writerow(header)

            for p in productos:
                stock_por_bodega = {inv.ubicacion_id: inv.cantidad for inv in p.inventarios.all()}
                row = [p.codigo, p.nombre, p.get_categoria_display(), p.precio_venta, p.stock_global, p.valor_total]
                for bodega in bodegas:
                    row.append(stock_por_bodega.get(bodega.id, 0))
                writer.writerow(row)
            return response
        return super().get(request, *args, **kwargs)
    
class ProductoCreateView(LoginRequiredMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'Inventario/producto_form.html'
    success_url = reverse_lazy('producto_list')

class ProductoUpdateView(LoginRequiredMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'Inventario/producto_form.html'
    success_url = reverse_lazy('producto_list')

# --- Proveedores ---
class ProveedorListView(LoginRequiredMixin, ListView):
    model = Proveedor
    template_name = 'Inventario/proveedor_list.html'
    context_object_name = 'proveedores'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Proveedor.objects.filter(
                Q(nombre__icontains=query) | Q(contacto__icontains=query)
            )
        return Proveedor.objects.all()

class ProveedorCreateView(LoginRequiredMixin, CreateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'Inventario/proveedor_form.html'
    success_url = reverse_lazy('proveedor_list')

class ProveedorUpdateView(LoginRequiredMixin, UpdateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'Inventario/proveedor_form.html'
    success_url = reverse_lazy('proveedor_list')

# --- Destinos (Sitios) ---
class DestinoListView(LoginRequiredMixin, ListView):
    model = Destino
    template_name = 'Inventario/destino_list.html'
    context_object_name = 'destinos'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Destino.objects.filter(nombre__icontains=query)
        return Destino.objects.all()

class DestinoCreateView(LoginRequiredMixin, CreateView):
    model = Destino
    form_class = DestinoForm
    template_name = 'Inventario/destino_form.html'
    success_url = reverse_lazy('destino_list')

class DestinoUpdateView(LoginRequiredMixin, UpdateView):
    model = Destino
    form_class = DestinoForm
    template_name = 'Inventario/destino_form.html'
    success_url = reverse_lazy('destino_list')

# --- Movimientos ---
class MovimientoCreateView(LoginRequiredMixin, CreateView):
    model = Movimiento
    form_class = MovimientoForm
    template_name = 'Inventario/movimiento_form.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        try:
            form.instance.usuario = self.request.user
            return super().form_valid(form) 
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)

# --- Reportes ---
@login_required
def reporte_movimientos(request):
    """
    Handles both the display of the report and the Excel export.
    """
    movimientos = Movimiento.objects.select_related('producto', 'origen', 'destino', 'usuario').order_by('-fecha', '-id')
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    tipo = request.GET.get('tipo')
    
    if fecha_inicio and fecha_fin:
        movimientos = movimientos.filter(fecha__range=[fecha_inicio, fecha_fin])
    
    if tipo:
        movimientos = movimientos.filter(tipo=tipo)

    if request.GET.get('export') == 'excel':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Movement_Analysis.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Reference', 'Type', 'Category', 'Product Code', 'Product Name', 
            'Quantity', 'Unit Cost ($)', 'Total Value ($)', 'Origin', 'Destination', 'User', 'Notes'
        ])

        for mov in movimientos:
            origin_name = mov.origen.nombre if mov.origen else 'N/A'
            dest_name = mov.destino.nombre if mov.destino else 'N/A'
            costo = mov.producto.precio_costo if mov.producto.precio_costo else 0
            
            writer.writerow([
                mov.fecha.strftime("%Y-%m-%d"),
                mov.referencia,
                mov.get_tipo_display(), 
                mov.producto.categoria,
                mov.producto.codigo,
                mov.producto.nombre,
                mov.cantidad,
                costo,
                costo * mov.cantidad,
                origin_name,
                dest_name,
                mov.usuario.username if mov.usuario else 'System',
                mov.razon_ajuste
            ])
        return response

    return render(request, 'Inventario/reporte_movimientos.html', {'movimientos': movimientos})

@login_required
def reporte_bodegas(request):
    """
    Muestra el inventario por sitios y permite exportar:
    1. Individualmente (por bodega).
    2. General (todo junto).
    """
    # 1. EXPORTACIÓN GENERAL
    if request.GET.get('export') == 'general_excel':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="General_Inventory_All_Sites.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Warehouse/Site', 'Product Code', 'Product Name', 'Category', 'Quantity', 'Unit Price', 'Total Value'])
        
        items = Inventario.objects.filter(cantidad__gt=0).select_related('ubicacion', 'producto').order_by('ubicacion__nombre', 'producto__nombre')
        for item in items:
            writer.writerow([
                item.ubicacion.nombre, item.producto.codigo, item.producto.nombre,
                item.producto.categoria, item.cantidad, item.producto.precio_venta,
                item.cantidad * item.producto.precio_venta
            ])
        return response

    # 2. EXPORTACIÓN INDIVIDUAL
    if request.GET.get('export') == 'excel' and request.GET.get('bodega_id'):
        bodega_id = request.GET.get('bodega_id')
        destino = get_object_or_404(Destino, pk=bodega_id)
        
        items = Inventario.objects.filter(ubicacion=destino, cantidad__gt=0).select_related('producto')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Inventory_{destino.nombre}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Product Code', 'Product Name', 'Category', 'Quantity', 'Unit Price', 'Total Value'])
        for item in items:
            writer.writerow([
                item.producto.codigo, item.producto.nombre, item.producto.categoria,
                item.cantidad, item.producto.precio_venta, item.cantidad * item.producto.precio_venta
            ])
        return response

    # 3. VISTA HTML
    destinos = Destino.objects.all()
    inventario_completo = []
    
    for destino in destinos:
        items = Inventario.objects.filter(ubicacion=destino, cantidad__gt=0).select_related('producto')
        if items.exists():
            inventario_completo.append({
                'sitio': destino,
                'items': items,
                'total_items': sum(i.cantidad for i in items),
                'valor_total': sum(i.cantidad * i.producto.precio_venta for i in items)
            })
            
    return render(request, 'Inventario/reporte_bodegas.html', {
        'inventario_completo': inventario_completo
    })

# --- REPORTE FINANCIERO (CUMPLIENDO REQUERIMIENTOS DE ANTHONY) ---
@login_required
def reporte_financiero(request):
    """
    Centro de Reportes Financieros:
    1. Salidas Generales.
    2. Total por 'Salida' (Referencia).
    3. Total por Bodega.
    4. Total por Unidad (Apartamento).
    """
    # Filtros de fecha opcionales
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # A. RESUMEN DE SALIDAS GENERAL (Todo lo que sea OUT o REPLACEMENT)
    salidas = Movimiento.objects.filter(tipo__in=['OUT', 'REPLACEMENT']).select_related('producto', 'origen', 'destino', 'usuario').order_by('-fecha')
    
    if start_date and end_date:
        salidas = salidas.filter(fecha__range=[start_date, end_date])

    # B. TOTAL POR GENERACIÓN DE SALIDA (Agrupado por Referencia)
    # Ejemplo: La salida "OUT-251201" sumó $500 en total
    salidas_por_ref = salidas.values('referencia', 'fecha', 'usuario__username', 'origen__nombre', 'destino__nombre').annotate(
        total_items=Sum('cantidad'),
        valor_total=Sum(F('cantidad') * F('producto__precio_venta')) # O precio_costo según prefieras
    ).order_by('-fecha')

    # C. TOTAL DE BODEGA (Valor actual del inventario por sitio)
    bodegas = Destino.objects.filter(tipo__icontains='Bodega') # Asumiendo que usas 'Bodega' en el campo tipo
    data_bodegas = []
    for b in bodegas:
        items = Inventario.objects.filter(ubicacion=b)
        valor = sum(i.cantidad * i.producto.precio_venta for i in items)
        data_bodegas.append({'nombre': b.nombre, 'items': items.count(), 'valor': valor})

    # D. TOTAL POR UNIDAD (APARTAMENTOS)
    # Asumiendo que las Unidades son Destinos que NO son bodegas (o tienen tipo 'Apartamento')
    unidades = Destino.objects.exclude(tipo__icontains='Bodega') 
    data_unidades = []
    for u in unidades:
        # Calculamos cuánto se le ha "Despachado" (Salidas hacia esa unidad)
        # Nota: Buscamos movimientos donde el DESTINO sea esta unidad
        movs_hacia_unidad = Movimiento.objects.filter(destino=u, tipo__in=['OUT', 'TRANSFER'])
        
        if start_date and end_date:
            movs_hacia_unidad = movs_hacia_unidad.filter(fecha__range=[start_date, end_date])
            
        costo_acumulado = sum(m.cantidad * m.producto.precio_venta for m in movs_hacia_unidad)
        
        # Solo agregamos si tiene costos asociados
        if costo_acumulado > 0:
            data_unidades.append({'nombre': u.nombre, 'tipo': u.tipo, 'costo_total': costo_acumulado})

    # --- EXPORTACIÓN A EXCEL (LÓGICA AUTOMÁTICA) ---
    if request.GET.get('export') == 'excel_financiero':
        report_type = request.GET.get('type') # 'salidas', 'unidades', 'bodegas'
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Reporte_{report_type}.csv"'
        writer = csv.writer(response)

        if report_type == 'salidas_detalladas':
            writer.writerow(['Fecha', 'Ref', 'Producto', 'Cant', 'Precio Unit', 'Total', 'Origen', 'Destino/Unidad'])
            for s in salidas:
                writer.writerow([s.fecha, s.referencia, s.producto.nombre, s.cantidad, s.producto.precio_venta, s.cantidad * s.producto.precio_venta, s.origen, s.destino])

        elif report_type == 'por_referencia':
            writer.writerow(['Fecha', 'Referencia', 'Usuario', 'Origen', 'Destino', 'Items Totales', 'Valor Total ($)'])
            for s in salidas_por_ref:
                writer.writerow([s['fecha'], s['referencia'], s['usuario__username'], s['origen__nombre'], s['destino__nombre'], s['total_items'], s['valor_total']])

        elif report_type == 'unidades':
            writer.writerow(['Nombre Unidad', 'Tipo', 'Costo Acumulado ($)'])
            for u in data_unidades:
                writer.writerow([u['nombre'], u['tipo'], u['costo_total']])

        return response

    context = {
        'salidas': salidas[:20], # Mostramos solo las ultimas 20 en pantalla
        'salidas_por_ref': salidas_por_ref[:10],
        'data_bodegas': data_bodegas,
        'data_unidades': data_unidades,
    }
    return render(request, 'Inventario/reporte_financiero.html', context)

@login_required
def shopping_list(request):
    # Productos que necesitan compra (Stock actual <= Mínimo)
    items_to_buy = Producto.objects.filter(stock_total_global__lte=F('stock_minimo'))
    
    context = {
        'items': items_to_buy,
        'today': timezone.now().date()
    }

    # Lógica para enviar al calendario
    if request.method == 'POST' and 'create_reminder' in request.POST:
        if not items_to_buy.exists():
            return render(request, 'Inventario/shopping_list.html', {**context, 'error': 'No items to buy.'})
        
        # Generar ID de Lista
        list_id = f"SHOP-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
        
        # Crear texto para el evento
        summary = f"🛒 Shopping List Reminder: {list_id}"
        description = f"Purchase required for {items_to_buy.count()} critical items.\n\nList ID: {list_id}\nGenerated by Elite Management System."
        
        # Llamar a la API de Google
        calendar_link = create_google_calendar_event(summary, description)
        
        if calendar_link:
            context['success'] = f"Reminder created in Google Calendar! List ID: {list_id}"
            context['calendar_link'] = calendar_link
        else:
            context['error'] = "Could not connect to Google Calendar. Check server logs/credentials."

    return render(request, 'Inventario/shopping_list.html', context)



@login_required
def generar_lista(request):
    if request.method == 'POST':
        # Get selected product IDs from the HTML form (checkboxes)
        selected_ids = request.POST.getlist('selected_products')
        
        if not selected_ids:
            # Handle empty selection
            return redirect('producto_list')

        # Create the List Header
        nueva_lista = ListaCompra.objects.create(
            usuario=request.user,
            estado='PENDING'
        )

        # Create Items
        productos = Producto.objects.filter(id__in=selected_ids)
        for p in productos:
            # Calculate suggested quantity (Min Stock - Current Stock, or just 1)
            deficit = p.stock_minimo - p.stock_total_global
            qty = deficit if deficit > 0 else 1
            
            ItemLista.objects.create(
                lista=nueva_lista,
                producto=p,
                cantidad_sugerida=qty
            )
        
        return redirect('shopping_list_detail', pk=nueva_lista.id)
    
    return redirect('producto_list')

# EN views.py

class ProductoListView(LoginRequiredMixin, ListView):  # <--- ESTA LINEA ES LA CLAVE
    model = Producto
    template_name = 'Inventario/producto_list.html'
    context_object_name = 'productos'
    paginate_by = 15

    def get_queryset(self):
        # Optimiza la consulta trayendo inventarios y ubicaciones de una vez
        queryset = Producto.objects.prefetch_related('inventarios', 'inventarios__ubicacion').all().order_by('nombre')
        
        # 1. Filtro de Búsqueda
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(codigo__icontains=query) | 
                Q(nombre__icontains=query) | 
                Q(proveedor__nombre__icontains=query)
            )
        
        # 2. Filtro de Categoría
        categoria = self.request.GET.get('categoria')
        if categoria:
            queryset = queryset.filter(categoria=categoria)

        # 3. FILTRO DE STOCK (NUEVO)
        stock_status = self.request.GET.get('stock_status')
        if stock_status == 'critical':
            # Out of Stock (<= 0)
            queryset = queryset.filter(stock_total_global__lte=0)
        elif stock_status == 'low':
            # Low Stock (Entre 1 y el Mínimo)
            queryset = queryset.filter(
                stock_total_global__lte=F('stock_minimo'), 
                stock_total_global__gt=0
            )
        elif stock_status == 'alert':
            # Ambos (Critical + Low)
            queryset = queryset.filter(stock_total_global__lte=F('stock_minimo'))

        return queryset
        
    def get(self, request, *args, **kwargs):
        # Lógica de exportación a Excel
        if request.GET.get('export') == 'excel':
            productos = self.get_queryset()
            bodegas = Destino.objects.all().order_by('nombre')

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="Global_Inventory_Report.csv"'
            writer = csv.writer(response)

            header = ['Code', 'Product Name', 'Category', 'Sale Price', 'Global Stock', 'Total Value']
            for bodega in bodegas:
                header.append(f"Stock: {bodega.nombre}")
            writer.writerow(header)

            for p in productos:
                stock_por_bodega = {inv.ubicacion_id: inv.cantidad for inv in p.inventarios.all()}
                row = [p.codigo, p.nombre, p.get_categoria_display(), p.precio_venta, p.stock_global, p.valor_total]
                for bodega in bodegas:
                    row.append(stock_por_bodega.get(bodega.id, 0))
                writer.writerow(row)
            return response
        return super().get(request, *args, **kwargs)
    
    
# --- EN views.py (Agrega esto al final) ---

@login_required
def shopping_list_index(request):
    """Muestra el historial de listas guardadas"""
    # Trae todas las listas ordenadas por fecha
    listas = ListaCompra.objects.all().order_by('-fecha_creacion')
    return render(request, 'Inventario/shopping_list_index.html', {'listas': listas})

@login_required
def shopping_list_detail(request, pk):
    lista = get_object_or_404(ListaCompra, pk=pk)
    items = lista.items.select_related('producto').all()
    
    # 1. Construir el Título y la Descripción del evento
    summary = f"🛒 Pending Purchases List #{lista.id_lista}"
    
    desc_lines = [f"List ID: {lista.id_lista}", "Items needed:"]
    for item in items:
        desc_lines.append(f"- {item.producto.nombre} (Qty: {item.cantidad_sugerida})")
    
    description = "\n".join(desc_lines)

    # 2. Codificar para URL (Convierte espacios en %20, etc.)
    params = {
        'action': 'TEMPLATE',
        'text': summary,
        'details': description,
        'dates': f"{timezone.now().strftime('%Y%m%dT%H%M%S')}/{timezone.now().strftime('%Y%m%dT%H%M%S')}" # Hora actual
    }
    url_params = urllib.parse.urlencode(params)
    
    # 3. Crear el enlace final
    calendar_link = f"https://calendar.google.com/calendar/render?{url_params}"

    context = {
        'lista': lista,
        'items': items,
        'calendar_link': calendar_link # <--- Pasamos el enlace directo a la plantilla
    }

    return render(request, 'Inventario/shopping_list_detail.html', context)