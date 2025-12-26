"""
URL configuration for Elite_brand project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Esto le dice a Django: "Cualquier ruta que no sea admin, búscala en Inventario"
    path('', include('Inventario.urls')), 
]