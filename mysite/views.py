from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from utils.product_sync_by_date import ProductSyncByDate
import json
import logging

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def product_sync_page(request):
    """渲染商品同步页面"""
    return render(request, 'product_sync_page.html')

def orders_sync_page(request):
    """渲染订单同步页面"""
    return render(request, 'orders_sync_page.html')
