import json
import time
import math
import logging
import requests
from datetime import datetime, timedelta
from django.http import JsonResponse
from .product_sync_base import ProductSyncBase

logger = logging.getLogger(__name__)

class ProductSyncByDate(ProductSyncBase):
    """按日期同步商品数据"""

    def sync_products(self, start_time=None, end_time=None, page=1):
        """
        按时间范围同步产品数据，默认同步最近1天的数据
        
        Args:
            start_time: 开始时间，格式：'YYYY-MM-DD HH:MM:SS'
            end_time: 结束时间，格式：'YYYY-MM-DD HH:MM:SS'
            page: 页码，默认为1
        """
        logger.info(f"开始同步第 {page} 页数据...")
        print("开始获取商品数据")
        if not start_time:
            start_time = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        if not end_time:
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info(f"按时间区间同步模式: {start_time} 到 {end_time}")
        
        body = {
            "page_size": 100,
            "page_no": page,
            "status": 0,
            "start_time": start_time,
            "end_time": end_time
        }

        body_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        params, headers = self.generate_sign(body_str)

        logger.info(f"请求参数: {json.dumps(params, ensure_ascii=False)}")
        logger.info(f"请求体: {body_str}")
        
        try:
            response = requests.post(self.api_url, params=params, headers=headers, data=body_str)
            logger.info(f"API响应状态码: {response.status_code}")
            logger.info(f"API响应内容: {response.text}")
            
            if response.status_code != 200:
                logger.error(f"API响应内容: {response.text}")
                raise Exception(f"API请求失败: {response.text}")

            result = response.json()
            logger.info(f"API返回数据: {json.dumps(result, ensure_ascii=False)}")

            if result['code'] != 200:
                raise Exception(f"业务处理失败: {result['message']}")

            data = result['data']
            total = data['total']
            page_size = data['pageSize']
            current_page = data['currentPage']
            max_page = math.ceil(total / page_size)

            logger.info(f"当前页：{current_page}，总页数：{max_page}，总记录数：{total}")

            all_data = {
                'total': total,
                'pageSize': page_size,
                'currentPage': current_page,
                'data': data['data']
            }

            if current_page < max_page:
                time.sleep(1)  # 避免请求过快
                next_page_data = self.sync_products(start_time, end_time, page + 1)
                all_data['data'].extend(next_page_data['data'])

            return all_data

        except Exception as e:
            logger.error(f"发生异常: {str(e)}")
            raise

def import_products_by_date(request):
    """处理按日期导入商品的请求"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            start_time = data.get('start_time')
            end_time = data.get('end_time')
            
            sync = ProductSyncByDate()
            logger.info(f"开始按日期导入商品: {start_time} 到 {end_time}")
            api_data = sync.sync_products(start_time=start_time, end_time=end_time)
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

def sync_products_by_date():
    """定时任务调用的同步函数"""
    try:
        sync = ProductSyncByDate()
        logger.info("开始执行定时同步任务")
        api_data = sync.sync_products()  # 默认同步最近1天的数据
        processed_count = sync.process_products(api_data['data'])
        logger.info(f"定时同步任务完成，共处理 {processed_count} 条数据")
        return True
    except Exception as e:
        logger.error(f"定时同步任务失败: {str(e)}")
        return False
