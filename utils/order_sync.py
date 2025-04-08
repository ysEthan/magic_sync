import time
import hashlib
import json
import math
import requests
import logging
from datetime import datetime, timedelta
from django.db import connection
from django.http import JsonResponse
from .product_sync_by_sku import ProductSyncBySku
from .logistics_sync import LogisticsSync
from api.get_tracking import TrackingAPI
import sys

# 设置系统默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python 3.6 或更早版本
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

# 配置日志级别
logger = logging.getLogger(__name__)
# 禁用 urllib3 的 DEBUG 日志
logging.getLogger('urllib3').setLevel(logging.WARNING)
# 禁用 requests 的 DEBUG 日志
logging.getLogger('requests').setLevel(logging.WARNING)
# 禁用 connectionpool 的 DEBUG 日志
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

class OrderSync:
    """订单同步服务"""
    
    def __init__(self):
        self.api_url = "https://openapi.qizhishangke.com/api/openservices/trade/v1/getSalesTradeList"
        self.app_name = "mathmagic"
        self.app_key = "82be0592545283da00744b489f758f99"
        self.sid = "mathmagic"
        self.product_sync = ProductSyncBySku()
        self.tracking_api = TrackingAPI()
        self.logistics_sync = LogisticsSync()

    def generate_sign(self, body):
        """生成API签名"""
        headers = {'Content-Type': 'application/json'}
        timestamp = str(int(time.time()))
        sign_str = f"{self.app_key}appName{self.app_name}body{body}sid{self.sid}timestamp{timestamp}{self.app_key}"
        sign = hashlib.md5(sign_str.encode()).hexdigest()
        
        params = {
            "appName": self.app_name,
            "sid": self.sid,
            "sign": sign,
            "timestamp": timestamp,
        }
        return params, headers

    def fetch_orders(self, page=1, start_time=None, end_time=None):
        """从API获取订单数据"""
        try:
            # 准备请求数据
            body = {
                "pageSize": 200,
                "pageNo": page,
                "createTimeBegin": start_time or (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S'),
                "createTimeEnd": end_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "tradeStatusCode": 0
            }
            
            body_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
            params, headers = self.generate_sign(body_str)
            response = requests.post(self.api_url, params=params, headers=headers, data=body_str)
            response.raise_for_status()
            
            result = response.json()
            
            if result['code'] != 200:
                raise Exception(f"API返回错误: {result.get('msg')}")
            
            data = result['data']
            return {
                'items': data.get('data', []),
                'total': data.get('total', 0),
                'current_page': data.get('currentPage', page),
                'page_size': data.get('pageSize', 200)
            }
            
        except UnicodeEncodeError as e:
            logger.error(f"编码错误: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取订单数据失败: {str(e)}")
            logger.error("详细错误信息:", exc_info=True)
            return None

    def ensure_product_exists(self, cursor, sku_code):
        """确保商品存在，如果不存在则导入"""
        try:
            # 检查SKU是否存在
            cursor.execute("""
                SELECT id FROM products_product WHERE code = %s
            """, [sku_code])
            product_result = cursor.fetchone()
            
            if not product_result:
                logger.info(f"SKU不存在，开始导入: {sku_code}")
                try:
                    # 使用商品同步功能导入SKU
                    self.product_sync.sync_products(sku_list=[sku_code])
                    time.sleep(1)  # 等待数据写入
                    
                    # 重新检查SKU是否存在
                    cursor.execute("""
                        SELECT id FROM products_product WHERE code = %s
                    """, [sku_code])
                    product_result = cursor.fetchone()
                    
                    if not product_result:
                        logger.error(f"SKU {sku_code} 导入失败")
                        return None
                        
                except Exception as e:
                    logger.error(f"导入SKU {sku_code} 失败: {str(e)}")
                    return None

            return product_result[0] if product_result else None
            
        except Exception as e:
            logger.error(f"确保商品存在失败: {str(e)}")
            return None

    def fetch_order_details(self, trade_ids):
        """获取订单明细数据"""
        try:
            # 将订单ID列表分成每批99个
            trade_id_chunks = [trade_ids[i:i + 99] for i in range(0, len(trade_ids), 99)]
            all_details = []
            
            for chunk in trade_id_chunks:
                body = {
                    "tradeIds": chunk
                }
                
                body_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
                params, headers = self.generate_sign(body_str)
                
                url = "https://openapi.qizhishangke.com/api/openservices/trade/v1/getSalesTradeOrderList"
                response = requests.post(url, params=params, headers=headers, data=body_str)
                response.raise_for_status()
                
                result = response.json()
                if result['code'] != 200:
                    raise Exception(f"API返回错误: {result.get('msg')}")
                
                all_details.extend(result['data'])
                time.sleep(0.1)  # 避免请求过快
            
            return all_details
            
        except Exception as e:
            logger.error(f"获取订单明细失败: {str(e)}")
            return []

    def process_order(self, cursor, item):
        """处理单个订单数据"""
        try:
            # 检查订单是否需要更新
            api_status = item.get('tradeStatusDesc', '')
            skip_statuses = ['已发货', '已完成', '已取消']
            
            if api_status in skip_statuses:
                # 检查数据库中的订单状态
                cursor.execute("""
                    SELECT status FROM trade_order WHERE order_number = %s
                """, [item['tradeNo']])
                existing_order = cursor.fetchone()
                
                if existing_order and existing_order[0] in skip_statuses:
                    logger.info(f"订单 {item['tradeNo']} API状态为 {api_status}，数据库状态为 {existing_order[0]}，跳过更新")
                    return True
                else:
                    if existing_order:
                        logger.info(f"订单 {item['tradeNo']} API状态为 {api_status}，但数据库状态为 {existing_order[0]}，需要更新")
                    else:
                        logger.info(f"订单 {item['tradeNo']} 首次同步，继续处理")
            
            logger.info(f"处理订单: {item['tradeNo']}")

            # 1. 处理店铺
            cursor.execute("""
                INSERT INTO trade_shop (
                    name, platform, shop_code, manager_id, status, created_at, updated_at
                )
                VALUES (%s, %s, %s, 
                    (SELECT id FROM authentication_user LIMIT 1), 1, NOW(6), NOW(6))
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    updated_at = NOW(6)
            """, [
                item.get('shopText', '默认店铺'),
                'offline',
                item['shopNo']
            ])
            
            # 获取店铺ID
            cursor.execute("SELECT id FROM trade_shop WHERE shop_code = %s", [item['shopNo']])
            shop_id = cursor.fetchone()[0]
            
            # 2. 处理订单主表
            created_time = datetime.fromisoformat(item['created'].replace('Z', '+00:00'))
            trade_time = datetime.fromisoformat(item.get('tradeTime', item['created']).replace('Z', '+00:00'))
            
            cursor.execute("""
                INSERT INTO trade_order (
                    order_number, platform_order_number, order_type,
                    exchange_rate_to_usd, shop_id, status, total_amount,
                    currency, shipping_fee, payment_method, payment_status,
                    payment_time, order_place_time, shipping_address,
                    shipping_contact, shipping_phone, postal_code,
                    country, state, city, district, system_remark,
                    cs_remark, buyer_remark, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(6), NOW(6))
                ON DUPLICATE KEY UPDATE
                    platform_order_number = VALUES(platform_order_number),
                    order_type = VALUES(order_type),
                    exchange_rate_to_usd = VALUES(exchange_rate_to_usd),
                    shop_id = VALUES(shop_id),
                    status = VALUES(status),
                    total_amount = VALUES(total_amount),
                    currency = VALUES(currency),
                    shipping_fee = VALUES(shipping_fee),
                    payment_method = VALUES(payment_method),
                    payment_status = VALUES(payment_status),
                    payment_time = VALUES(payment_time),
                    order_place_time = VALUES(order_place_time),
                    shipping_address = VALUES(shipping_address),
                    shipping_contact = VALUES(shipping_contact),
                    shipping_phone = VALUES(shipping_phone),
                    postal_code = VALUES(postal_code),
                    country = VALUES(country),
                    state = VALUES(state),
                    city = VALUES(city),
                    district = VALUES(district),
                    system_remark = VALUES(system_remark),
                    cs_remark = VALUES(cs_remark),
                    buyer_remark = VALUES(buyer_remark),
                    updated_at = NOW(6)
            """, [
                item['tradeNo'],
                item.get('srcTids'),
                item.get('tradeSource', 'platform'),
                float(item.get('exchangeRate', 1.0)),
                shop_id,
                item.get('tradeStatusDesc', 'pending'),
                float(item.get('receivable', 0)),
                item.get('currencyCode', 'CNY'),
                float(item.get('postAmount', 0)),
                'online',
                item.get('received', 0) > 0,
                None,  # payment_time
                trade_time,  # order_place_time
                item['receiverAddress'],
                item['receiverName'],
                item.get('receiverMobile') or item.get('receiverTelno', ''),
                item.get('receiverZip'),
                item.get('country', '中国'),
                item.get('receiverProvince'),
                item.get('receiverCity'),
                item.get('receiverDistrict'),
                item.get('erpRemark', ''),
                item.get('csRemark', ''),
                item.get('buyerMessage', '')
            ])
            
            # 获取订单ID
            cursor.execute("SELECT id FROM trade_order WHERE order_number = %s", [item['tradeNo']])
            order_id = cursor.fetchone()[0]
            
            # 3. 获取并处理订单明细
            order_details = self.fetch_order_details([item['tradeId']])
            for detail in order_details:
                sku_id = self.ensure_product_exists(cursor, detail['skuNo'])
                if not sku_id:
                    raise Exception(f"无法获取或创建SKU: {detail['skuNo']}")
                
                cursor.execute("""
                    INSERT INTO trade_order_item (
                        order_id, product_id, quantity, unit_price,
                        discount, total_price, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(6), NOW(6))
                    ON DUPLICATE KEY UPDATE
                        quantity = VALUES(quantity),
                        unit_price = VALUES(unit_price),
                        discount = VALUES(discount),
                        total_price = VALUES(total_price),
                        updated_at = NOW(6)
                """, [
                    order_id,
                    sku_id,
                    detail['num'],
                    detail['price'],
                    0,
                    detail['skuAmount']
                ])
            
            # 4. 处理包裹信息
            package_id = None
            logistics_text = item.get('logisticsText', '')
            if item.get('warehouseNo') and logistics_text != '无':
                if self.logistics_sync.create_or_update_package(cursor, item, order_id, order_details):
                    # 获取包裹ID和状态
                    cursor.execute("""
                        SELECT id, status_id FROM logistics_package 
                        WHERE order_id = %s AND tracking_no = %s
                    """, [order_id, item.get('logisticsNo')])
                    result = cursor.fetchone()
                    if result:
                        package_id = result[0]
                        package_status = result[1]
                        
                        # 只有当订单状态为已发货且包裹状态为0时才注册物流单号
                        if (item.get('tradeStatusDesc') == '已发货' and 
                            package_status == 0 and 
                            item.get('logisticsNo')):
                            logger.info(f"注册物流单号 {item.get('logisticsNo')} (订单: {item.get('tradeNo')})")
                            if self.logistics_sync.register_tracking_number(item):
                                # 更新包裹状态为已注册(1)
                                cursor.execute("""
                                    UPDATE logistics_package 
                                    SET status_id = 1, updated_at = NOW(6)
                                    WHERE id = %s
                                """, [package_id])
                                logger.info(f"包裹状态已更新为已注册 (包裹ID: {package_id})")
            else:
                logger.info(f"订单 {item.get('tradeNo')} 未指定物流或仓库，跳过包裹处理")
            
            return True
            
        except Exception as e:
            logger.error(f"处理订单 {item.get('tradeNo', 'Unknown')} 失败: {str(e)}")
            raise

    def sync_orders(self, start_time=None, end_time=None):
        """同步订单数据"""
        success_count = 0
        error_count = 0
        
        try:
            logger.error(f"开始同步订单，时间范围：{start_time} 至 {end_time}")
            with connection.cursor() as cursor:
                # 获取第一页数据
                result = self.fetch_orders(page=1, start_time=start_time, end_time=end_time)
                if not result:
                    raise Exception("获取订单数据失败")
                
                total = result['total']
                total_pages = math.ceil(total / result['page_size'])
                logger.info(f"开始同步订单，共 {total} 条数据，{total_pages} 页")
                
                # 处理所有页的数据
                for page in range(1, total_pages + 1):
                    if page > 1:
                        result = self.fetch_orders(page=page, start_time=start_time, end_time=end_time)
                        if not result:
                            logger.error(f"获取第 {page} 页数据失败")
                            continue
                    
                    items = result['items']
                    if not items:
                        continue
                        
                    # 获取订单明细
                    trade_ids = [item['tradeId'] for item in items]
                    order_details = self.fetch_order_details(trade_ids)
                    
                    # 将明细数据与主订单数据关联
                    orders_map = {str(item['tradeId']): item for item in items}
                    for detail in order_details:
                        trade_id = str(detail['tradeId'])
                        if trade_id in orders_map:
                            if 'details' not in orders_map[trade_id]:
                                orders_map[trade_id]['details'] = []
                            orders_map[trade_id]['details'].append(detail)
                    
                    # 处理每个订单
                    for item in items:
                        try:
                            if self.process_order(cursor, item):
                                success_count += 1
                            else:
                                error_count += 1
                        except Exception as e:
                            logger.error(f"处理订单 {item.get('tradeNo', 'Unknown')} 失败: {str(e)}")
                            error_count += 1
                    
                    # 显示进度
                    if page % 5 == 0 or page == total_pages:
                        logger.info(f"同步进度: {page}/{total_pages} 页，成功: {success_count}，失败: {error_count}")
                    
                    # 避免请求过快
                    time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"同步订单失败: {str(e)}")
            logger.error("详细错误信息:", exc_info=True)
            raise
        
        return success_count, error_count

# 创建全局实例
order_sync = OrderSync()

def orders_sync(request):
    """处理订单导入请求"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            if not start_date or not end_date:
                return JsonResponse({
                    'status': 'error',
                    'message': '请提供开始时间和结束时间'
                }, status=400)

            # 添加时间部分
            start_time = f"{start_date} 00:00:00"
            end_time = f"{end_date} 23:59:59"
            
            success_count, error_count = order_sync.sync_orders(start_time=start_time, end_time=end_time)
            
            return JsonResponse({
                'status': 'success',
                'message': f'订单同步完成，成功: {success_count} 条，失败: {error_count} 条'
            })
            
        except Exception as e:
            logger.error(f"订单导入失败: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'导入失败：{str(e)}'
            }, status=500)
    
    return JsonResponse({'status': 'error', 'message': '只支持POST请求'}, status=405)
