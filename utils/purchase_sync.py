from django.http import JsonResponse
from django.db import connection, transaction
import logging
import requests
import json
import time
import hashlib
from datetime import datetime, timedelta
import math
from .product_sync_by_sku import ProductSyncBySku

logger = logging.getLogger(__name__)

class PurchaseSync:
    """采购单同步类"""
    
    def __init__(self):
        self.api_url = "https://openapi.qizhishangke.com/api/openservices/purchaseOrder/v1/getOrders"
        self.app_name = "mathmagic"
        self.app_key = "82be0592545283da00744b489f758f99"
        self.sid = "mathmagic"
        self.product_sync = ProductSyncBySku()
        
        # 状态映射
        self.status_mapping = {
            '待下单': 'pending_order',
            '待支付': 'pending_payment',
            '待入库': 'pending_storage',
            '已完成': 'completed',
            '已作废': 'cancelled',
            '全部退货': 'full_return',
            '部分退货': 'partial_return',
        }

    def generate_sign(self, body):
        """生成API签名"""
        try:
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
        except Exception as e:
            logger.error(f"生成签名失败: {str(e)}")
            raise

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

    def fetch_purchase_orders(self, page=1, start_time=None, end_time=None, purchase_no=None):
        """从API获取采购单数据"""
        try:
            logger.info(f"开始获取第 {page} 页采购单数据")
            
            # 准备请求数据
            if not start_time:
                start_time = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
            if not end_time:
                end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            body = {
                "pageSize": 200,
                "pageNo": page,
                "createTimeBegin": start_time,
                "createTimeEnd": end_time,
                "account": "admin"
            }
            print(body)
            if purchase_no:
                body["purchaseNo"] = purchase_no
            
            body_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
            # logger.info(f"请求参数: {body_str}")
            
            params, headers = self.generate_sign(body_str)
            
            # logger.info(f"发送请求到: {self.api_url}")
            response = requests.post(self.api_url, params=params, headers=headers, data=body_str.encode('utf-8'))
            response.raise_for_status()
            
            result = response.json()

            
            # logger.info(f"API响应数据: {json.dumps(result, ensure_ascii=False)}")
            
            if result['code'] != 200:
                raise Exception(f"API返回错误: {result.get('msg')}")
            
            data = result['data']
            return {
                'items': data.get('data', []),
                'total': data.get('total', 0),
                'current_page': data.get('currentPage', page),
                'page_size': data.get('pageSize', 200)
            }
            
        except Exception as e:
            logger.error(f"获取采购单数据失败: {str(e)}")
            # logger.exception("详细错误信息:")
            return {
                'items': [],
                'total': 0,
                'current_page': page,
                'page_size': 200
            }

    @transaction.atomic
    def process_purchase_order(self, cursor, item):
        """处理单个采购单数据"""
        try:
            logger.info(f"处理采购单: {item['purchaseNo']}")
            
            # 1. 处理采购员
            # 将采购员姓名拆分为first_name和last_name
            purchaser_name = item['purchaserName']
            first_name = purchaser_name[0] if purchaser_name else ''
            last_name = purchaser_name[1:] if len(purchaser_name) > 1 else ''
            
            cursor.execute("""
                INSERT INTO authentication_user (
                    username, email, is_staff, is_active, date_joined,
                    password, is_superuser, created_time, first_name, last_name,
                    updated_time
                )
                VALUES (%s, %s, %s, %s, NOW(6), %s, %s, NOW(6), %s, %s, NOW(6))
                ON DUPLICATE KEY UPDATE
                    email = VALUES(email),
                    first_name = VALUES(first_name),
                    last_name = VALUES(last_name),
                    updated_time = NOW(6)
            """, [
                item['purchaserName'],
                f"{item['purchaserName']}@example.com",
                True,
                True,
                'pbkdf2_sha256$600000$salt$hashedpassword',
                False,
                first_name,
                last_name
            ])
            
            # 获取采购员ID
            cursor.execute("SELECT id FROM authentication_user WHERE username = %s", [item['purchaserName']])
            purchaser_id = cursor.fetchone()[0]
            
            # 2. 处理供应商
            cursor.execute("""
                INSERT INTO purchase_supplier (
                    name, contact_person, contact_phone, address,
                    status, email, remark, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(6), NOW(6))
                ON DUPLICATE KEY UPDATE
                    updated_at = NOW(6)
            """, [
                item['providerName'],
                '',
                '',
                '',
                True,
                '7578@qq.com',
                '自动导入'
            ])
            
            # 获取供应商ID
            cursor.execute("SELECT id FROM purchase_supplier WHERE name = %s", [item['providerName']])
            supplier_id = cursor.fetchone()[0]
            
            # 3. 处理仓库
            cursor.execute("""
                INSERT INTO storage_warehouse (
                    id, warehouse_code, warehouse_name, location,
                    contact_phone, remark, status, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(6), NOW(6))
                ON DUPLICATE KEY UPDATE
                    warehouse_name = VALUES(warehouse_name),
                    updated_at = NOW(6)
            """, [
                item['warehouseId'],
                item['warehouseNo'],
                item['warehouseName'],
                '',
                '',
                '',
                True
            ])
            
            # 4. 处理采购单主表
            status = self.status_mapping.get(item['status'], 'draft')
            created_time = datetime.strptime(item['created'], "%Y-%m-%d %H:%M:%S")
            trade_time = datetime.strptime(item.get('tradeTime', item['created']), "%Y-%m-%d %H:%M:%S")
            
            # 处理价格
            price_str = ''.join(c for c in str(item.get('price', '0')) if c.isdigit() or c == '.')
            total_amount = float(price_str) if price_str else 0
            
            cursor.execute("""
                INSERT INTO purchase_purchaseorder (
                    order_number, supplier_id, status, total_amount,
                    order_time, warehouse_id, expected_delivery_date,
                    actual_delivery_date, remark, created_at, updated_at,
                    purchaser_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(6), %s)
                ON DUPLICATE KEY UPDATE
                    supplier_id = VALUES(supplier_id),
                    status = VALUES(status),
                    total_amount = VALUES(total_amount),
                    updated_at = NOW(6)
            """, [
                item['purchaseNo'],
                supplier_id,
                status,
                total_amount,
                trade_time,
                item['warehouseId'],
                trade_time.date(),
                None,
                item.get('remark', ''),
                created_time,
                purchaser_id
            ])
            
            # 获取采购单ID
            cursor.execute("SELECT id FROM purchase_purchaseorder WHERE order_number = %s", [item['purchaseNo']])
            purchase_order_id = cursor.fetchone()[0]
            
            # 5. 处理采购单明细
            sku_id = self.ensure_product_exists(cursor, item['specNo'])
            if not sku_id:
                raise Exception(f"无法获取或创建SKU: {item['specNo']}")
            
            # 处理数量
            quantity_str = ''.join(c for c in str(item.get('num', '0')) if c.isdigit() or c == '.')
            quantity = int(float(quantity_str)) if quantity_str else 0  # 转换为整数
            unit_price = total_amount / quantity if quantity > 0 else 0
            
            # 处理已收货数量
            arrive_num = item.get('stockinNum', 999.0)  # 直接获取浮点数
            received_quantity = int(arrive_num)  # 转换为整数
            
            cursor.execute("""
                INSERT INTO purchase_purchaseorderitem (
                    purchase_order_id, product_id, quantity, unit_price,
                    total_price, received_quantity, remark, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(6), NOW(6))
                ON DUPLICATE KEY UPDATE
                    quantity = VALUES(quantity),
                    unit_price = VALUES(unit_price),
                    total_price = VALUES(total_price),
                    received_quantity = VALUES(received_quantity),
                    updated_at = NOW(6)
            """, [
                purchase_order_id,
                sku_id,
                quantity,
                unit_price,
                total_amount,  # 使用 total_amount 作为 total_price
                received_quantity,  # 使用 arriveNum 作为 received_quantity
                ''
            ])
            
            return True
            
        except Exception as e:
            logger.error(f"处理采购单 {item.get('purchaseNo', 'Unknown')} 失败: {str(e)}")
            raise

    def sync_purchase_orders(self, start_time=None, end_time=None):
        """同步所有采购单数据"""
        try:
            total_success = 0
            total_error = 0
            page = 1
            
            while True:
                # 获取采购单数据
                purchase_data = self.fetch_purchase_orders(page, start_time, end_time)
                
                if not purchase_data['items']:
                    break
                
                # 处理每个采购单
                with connection.cursor() as cursor:
                    for item in purchase_data['items']:
                        try:
                            if self.process_purchase_order(cursor, item):
                                total_success += 1
                        except Exception as e:
                            logger.error(f"处理采购单失败: {str(e)}")
                            total_error += 1
                
                # 检查是否还有下一页
                max_page = math.ceil(purchase_data['total'] / purchase_data['page_size'])
                if page >= max_page:
                    break
                
                page += 1
                time.sleep(1)  # 避免请求过快
            
            return total_success, total_error
            
        except Exception as e:
            logger.error(f"同步采购单数据失败: {str(e)}")
            raise

    def sync_purchase_order_by_number(self, purchase_no):
        """根据采购单号同步单个采购单"""
        try:
            # 获取指定采购单数据
            purchase_data = self.fetch_purchase_orders(purchase_no=purchase_no)
            
            if not purchase_data['items']:
                return False, f"未找到采购单: {purchase_no}"
            
            # 处理采购单数据
            with connection.cursor() as cursor:
                for item in purchase_data['items']:
                    if item['purchaseNo'] == purchase_no:
                        if self.process_purchase_order(cursor, item):
                            return True, f"采购单 {purchase_no} 同步成功"
            
            return False, f"未找到采购单: {purchase_no}"
            
        except Exception as e:
            logger.error(f"同步采购单 {purchase_no} 失败: {str(e)}")
            return False, str(e)

# 创建全局实例
purchase_sync = PurchaseSync()

def import_purchase_orders(request):
    """处理采购单导入请求"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}

            
            # 处理时间部分
            if data.get('start_date'):
                start_date = f"{data.get('start_date')} 00:00:00"
            if data.get('end_date'):
                end_date = f"{data.get('end_date')} 23:59:59"
                
            # print(f"处理时间范围: {start_date} 到 {end_date}")
            
            success_count, error_count = purchase_sync.sync_purchase_orders(start_date, end_date)
            
            return JsonResponse({
                'status': 'success',
                'message': f'采购单同步完成，成功: {success_count} 条，失败: {error_count} 条'
            })
            
        except Exception as e:
            logger.error(f"采购单导入失败: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'导入失败：{str(e)}'
            }, status=500)
    
    return JsonResponse({'status': 'error', 'message': '只支持POST请求'}, status=405)
