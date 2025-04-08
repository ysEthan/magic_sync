import json
import time
import math
import logging
import requests
from django.http import JsonResponse
from .product_sync_base import ProductSyncBase

# 设置日志
logger = logging.getLogger(__name__)

class ProductSyncBySku(ProductSyncBase):
    """按SKU同步商品数据"""

    def sync_products(self, sku_list, page=1):
        """
        按SKU列表同步产品数据
        
        Args:
            sku_list: SKU编码列表
            page: 页码，默认为1
        """
        # logger.info(f"开始同步第 {page} 页数据...")
        # logger.info(f"按SKU同步模式，SKU列表: {sku_list}")
        
        body = {
            "page_size": 100,
            "page_no": page,
            "status": 0,
            "sku_list": sku_list
        }

        body_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        params, headers = self.generate_sign(body_str)

        try:
            response = requests.post(self.api_url, params=params, headers=headers, data=body_str)
            # logger.info(f"API响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"API响应内容: {response.text}")
                raise Exception(f"API请求失败: {response.text}")

            result = response.json()
            if result['code'] != 200:
                raise Exception(f"业务处理失败: {result['message']}")

            data = result['data']
            total = data['total']
            page_size = data['pageSize']
            current_page = data['currentPage']
            max_page = math.ceil(total / page_size)

            # logger.info(f"当前页：{current_page}，总页数：{max_page}，总记录数：{total}")

            # 处理当前页数据
            processed_count = self.process_products(data['data'])
            # logger.info(f"当前页处理完成，成功处理 {processed_count} 条数据")

            all_data = {
                'total': total,
                'pageSize': page_size,
                'currentPage': current_page,
                'data': data['data']
            }

            if current_page < max_page:
                time.sleep(1)  # 避免请求过快
                next_page_data = self.sync_products(sku_list, page + 1)
                all_data['data'].extend(next_page_data['data'])

            return all_data

        except Exception as e:
            logger.error(f"发生异常: {str(e)}")
            raise

def import_products_by_sku(request):
    """处理按SKU导入商品的请求"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sku_list = data.get('sku_list')
            
            if not sku_list:
                return JsonResponse({
                    'status': 'error',
                    'message': '请提供SKU列表'
                }, status=400)
            
            sync = ProductSyncBySku()
            logger.info(f"开始按SKU导入商品: {sku_list}")
            api_data = sync.sync_products(sku_list=sku_list)
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

    return JsonResponse({'status': 'error', 'message': '只支持POST请求'}, status=405)

def sync_products_by_sku(sku_list):
    """其他模块调用的同步函数"""
    try:
        sync = ProductSyncBySku()
        logger.info(f"开始执行SKU同步任务: {sku_list}")
        api_data = sync.sync_products(sku_list=sku_list)
        processed_count = sync.process_products(api_data['data'])
        logger.info(f"SKU同步任务完成，共处理 {processed_count} 条数据")
        return True
    except Exception as e:
        logger.error(f"SKU同步任务失败: {str(e)}")
        return False
