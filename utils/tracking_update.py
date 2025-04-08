import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from api.get_tracking import TrackingAPI

logger = logging.getLogger(__name__)

class LogisticsSync:
    def __init__(self):
        self.tracking_api = TrackingAPI()

    

    def ensure_logistics_service(self, cursor, logistics_id: int, logistics_text: str) -> Optional[int]:
        """
        确保物流服务存在，如果不存在则创建
        
        Args:
            cursor: 数据库游标
            logistics_id: 物流服务ID
            logistics_text: 物流服务名称
            
        Returns:
            int: 物流服务ID，如果失败则返回None
        """
        try:
            # 检查物流服务是否存在
            cursor.execute("""
                SELECT id FROM logistics_service WHERE id = %s
            """, [logistics_id])
            
            result = cursor.fetchone()
            if result:
                return result[0]
            
            # 创建新的物流服务
            cursor.execute("""
                INSERT INTO logistics_service (
                    id, service_name, service_code, service_type,
                    created_at, updated_at, carrier_id
                )
                VALUES (%s, %s, %s, %s, NOW(6), NOW(6), %s)
            """, [
                logistics_id,                # id
                logistics_text,             # service_name
                str(logistics_id),          # service_code
                1,                          # service_type
                1                           # carrier_id
            ])
            
            return logistics_id
            
        except Exception as e:
            logger.error(f"确保物流服务存在时发生错误: {logistics_id}-{logistics_text} {str(e)}")
            return None

    def create_or_update_package(self, cursor, order_data: Dict, order_id: int, order_details: List[Dict]) -> bool:
        """
        创建或更新包裹信息
        
        Args:
            cursor: 数据库游标
            order_data: 订单数据
            order_id: 订单ID
            order_details: 订单详情列表
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if not order_data.get('warehouseNo'):
                return False

            # 获取或创建物流服务
            service_id = self.ensure_logistics_service(
                cursor,
                order_data.get('logisticsId'),
                order_data.get('logisticsText', '未知物流')
            )
            
            if not service_id:
                logger.error(f"无法获取或创建物流服务: {order_data.get('logisticsText')}")
                return False

 
            status_id =0
            
            # 准备商品列表数据
            items_data = []
            for detail in order_details:
                item = {
                    'sku_code': detail['skuNo'],
                    'name': detail['skuName'],
                    'quantity': detail['num'],
                    'weight': detail.get('weight', 0),
                    'length': detail.get('length'),
                    'width': detail.get('width'),
                    'height': detail.get('height')
                }
                items_data.append(item)
            
            # 创建或更新包裹
            cursor.execute("""
                INSERT INTO logistics_package (
                    order_id, warehouse_id, tracking_no, status_id,
                    service_id, items, length, width, height, weight,
                    estimated_logistics_cost, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(6), NOW(6))
                ON DUPLICATE KEY UPDATE
                    warehouse_id = VALUES(warehouse_id),
                    tracking_no = COALESCE(%s, tracking_no),
                    status_id = VALUES(status_id),
                    service_id = VALUES(service_id),
                    items = VALUES(items),
                    length = VALUES(length),
                    width = VALUES(width),
                    height = VALUES(height),
                    weight = VALUES(weight),
                    estimated_logistics_cost = VALUES(estimated_logistics_cost),
                    updated_at = NOW(6)
            """, [
                order_id,
                order_data['warehouseNo'],
                order_data.get('logisticsNo'),
                status_id,
                service_id,
                json.dumps(items_data),
                order_data.get('length'),
                order_data.get('width'),
                order_data.get('height'),
                order_data.get('weight'),
                0,  # estimated_logistics_cost
                order_data.get('logisticsNo')
            ])
            
            return True
            
        except Exception as e:
            logger.error(f"创建或更新包裹时发生错误: {str(e)}")
            return False


    def register_tracking_number(self, order_data: Dict) -> bool:
        """
        注册物流单号
        
        Args:
            order_data: 订单数据，包含以下字段：
                - logisticsNo: 物流单号
                - tradeNo: 订单号
                - created: 创建时间
                - shopText: 店铺名称
                
        Returns:
            bool: 注册是否成功
        """
        try:
            if not order_data.get('logisticsNo'):
                return False

            tracking_data = [{
                "number": order_data['logisticsNo'],
                "order_no": order_data['tradeNo'],
                "order_time": datetime.fromisoformat(order_data['created'].replace('Z', '+00:00')).strftime('%Y/%m/%d'),
                "tag": f"订单号: {order_data['tradeNo']}",
                "remark": f"店铺: {order_data['shopText']}",
                "auto_detection": True
            }]
            
            # 注册物流单号
            register_result = self.tracking_api.register_tracking_numbers(tracking_data)
            if register_result:
                logger.info(f"成功注册物流单号: {order_data['logisticsNo']}")
                return True
            else:
                logger.warning(f"注册物流单号失败: {order_data['logisticsNo']}")
                return False
                
        except Exception as e:
            logger.error(f"注册物流单号时发生错误: {str(e)}")
            return False
        


    def get_tracking_info(self, cursor, package_id: int, tracking_number: str, carrier: Optional[int] = None) -> Optional[Dict]:
        """
        获取物流轨迹信息并更新包裹状态
        
        Args:
            cursor: 数据库游标
            package_id: 包裹ID
            tracking_number: 物流单号
            carrier: 运输商代码（可选）
            
        Returns:
            Dict: 轨迹信息，如果失败则返回None
        """
        try:
            tracking_data = [{
                "number": tracking_number,
                "carrier": carrier
            }]
            
            result = self.tracking_api.get_tracking_details(tracking_data)
            
            if not result:
                logger.warning(f"获取物流轨迹失败，包裹ID: {package_id}")
                return None
                
            if not result.get('accepted'):
                logger.warning(f"API未接受查询请求，包裹ID: {package_id}")
                return None

            # 状态映射关系
            status_mapping = {
                'InfoReceived': 2,
                'PickedUp': 3,
                'Departure': 4,
                'Arrival': 5,
                'AvailableForPickup': 6,
                'OutForDelivery': 7,
                'Delivered': 8,
                'Returning': 9,
                'Returned': 10
            }

            # 获取最新的轨迹信息
            track_info = result['accepted'][0].get('track_info', {})
            milestone = track_info.get('milestone', [])
            
            # 遍历里程碑，更新包裹状态
            latest_status_id = 1  # 默认状态：未发货
            for milestone_item in milestone:
                if milestone_item.get('time_utc'):
                    key_stage = milestone_item.get('key_stage')
                    
                    if key_stage in status_mapping:
                        status_id = status_mapping[key_stage]
                        if status_id > latest_status_id:
                            latest_status_id = status_id
                            
                            # 更新包裹状态
                            cursor.execute("""
                                UPDATE logistics_package 
                                SET status_id = %s, updated_at = NOW(6)
                                WHERE id = %s
                            """, [status_id, package_id])
                            
                            # 记录轨迹
                            cursor.execute("""
                                INSERT INTO logistics_tracking (
                                    package_id, status_id, location, description,
                                    tracking_time, created_at, updated_at
                                )
                                VALUES (%s, %s, %s, %s, %s, NOW(6), NOW(6))
                            """, [
                                package_id,
                                status_id,
                                milestone_item.get('location', ''),
                                milestone_item.get('description', ''),
                                datetime.fromisoformat(milestone_item['time_utc'].replace('Z', '+00:00'))
                            ])

            if latest_status_id > 1:
                logger.info(f"包裹状态已更新，包裹ID: {package_id}, 状态ID: {latest_status_id}")

            return result
            
        except Exception as e:
            logger.error(f"获取物流轨迹信息时发生错误: {str(e)}", exc_info=True)
            return None
