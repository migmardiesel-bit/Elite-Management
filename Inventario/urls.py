from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='Inventario/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Productos
    path('productos/', views.ProductoListView.as_view(), name='producto_list'),
    path('productos/nuevo/', views.ProductoCreateView.as_view(), name='producto_create'),
    path('productos/editar/<int:pk>/', views.ProductoUpdateView.as_view(), name='producto_edit'),

    # Proveedores
    path('proveedores/', views.ProveedorListView.as_view(), name='proveedor_list'),
    path('proveedores/nuevo/', views.ProveedorCreateView.as_view(), name='proveedor_create'),
    path('proveedores/editar/<int:pk>/', views.ProveedorUpdateView.as_view(), name='proveedor_edit'),

    # Destinos (Sites)
    path('destinos/', views.DestinoListView.as_view(), name='destino_list'),
    path('destinos/nuevo/', views.DestinoCreateView.as_view(), name='destino_create'),
    path('destinos/editar/<int:pk>/', views.DestinoUpdateView.as_view(), name='destino_edit'),

    # Movimientos
    path('movimientos/nuevo/', views.MovimientoCreateView.as_view(), name='movimiento_create'),
    
    # Reportes
    path('reportes/movimientos/', views.reporte_movimientos, name='reporte_movimientos'),
    path('reportes/bodegas/', views.reporte_bodegas, name='reporte_bodegas'),
    path('api/chat-ai/', views.chat_inventario, name='chat_inventario'),
    path('reportes/financiero/', views.reporte_financiero, name='reporte_financiero'),
    path('shopping-list/', views.shopping_list_index, name='shopping_list'), # Lista de todas las órdenes
    path('shopping-list/crear/', views.generar_lista, name='generar_lista'), # Acción de crear
    path('shopping-list/<int:pk>/', views.shopping_list_detail, name='shopping_list_detail'), # Detalle individual

]