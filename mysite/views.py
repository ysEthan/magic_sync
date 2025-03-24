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
    return render(request, 'page.html')

@require_http_methods(["POST"])
def import_products_by_date(request):
    """处理商品同步请求"""
    try:
        print("调用同步商品数据")
        sync = ProductSyncByDate()
        api_data = sync.sync_products()  # 默认同步最近一天的数据
        processed_count = sync.process_products(api_data['data'])
        
        return JsonResponse({
            'status': 'success',
            'message': f'商品数据导入成功，共处理 {processed_count} 条数据，总数据量 {api_data["total"]}'
        })
    
    except Exception as e:
        logger.error(f"商品导入失败: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'导入失败：{str(e)}',
            'detail': '请检查服务器日志获取详细信息'
        }, status=500) 