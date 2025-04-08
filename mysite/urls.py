"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from mysite.views import *

from utils.product_sync_by_date import sync_products_by_date
from utils.purchase_sync import import_purchase_orders
from utils.order_sync import orders_sync


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', product_sync_page, name='product_sync_page'),
    path('orders', orders_sync_page, name='orders_sync_page'),

    path('api/products/sync-by-date/', sync_products_by_date, name='sync_products_by_date'),
    path('api/purchase/import/', import_purchase_orders, name='import_purchase_orders'),
    path('api/orders/sync/', orders_sync, name='orders_sync'),




    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
