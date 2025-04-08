import requests
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

# 配置日志记录
logger = logging.getLogger(__name__)
# 禁用 urllib3 的 DEBUG 日志
logging.getLogger('urllib3').setLevel(logging.WARNING)
# 禁用 requests 的 DEBUG 日志
logging.getLogger('requests').setLevel(logging.WARNING)
# 禁用 connectionpool 的 DEBUG 日志
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

class TrackingAPI:
    def __init__(self):
        self.base_url = "https://api.17track.net/track/v2.2"
        self.api_key = "D80F2A1B13D89A3AFF172F07B3C88F10"
        self.headers = {
            "17token": self.api_key,
            "Content-Type": "application/json"
        }

    def register_tracking_numbers(self, tracking_data: List[Dict]) -> Optional[Dict]:
        """
        注册物流单号
        
        Args:
            tracking_data: 物流单号信息列表，每个元素包含以下字段：
                - number: 物流单号（必填）
                - carrier: 运输商代码（可选）
                - order_no: 订单编号（可选）
                - order_time: 订单日期（可选）
                - tag: 自定义标签（可选）
                - remark: 自定义备注（可选）
                - email: 通知邮箱（可选）
                - lang: 翻译语言代码（可选）
                - param: 附加跟踪参数（可选）
                - auto_detection: 是否自动检测运输商（可选，默认True）
            
        Returns:
            Dict: 包含注册结果的字典，如果失败则返回None
        """
        try:
            # 验证单号数量
            if len(tracking_data) > 40:
                logger.error(f"单号数量超过限制: {len(tracking_data)}")
                return None

            # 记录请求信息
            logger.debug(f"发送请求到: {self.base_url}/register")
            logger.debug(f"请求头: {self.headers}")
            logger.debug(f"请求体: {json.dumps(tracking_data, ensure_ascii=False)}")

            # 发送请求
            response = requests.post(
                f"{self.base_url}/register",
                headers=self.headers,
                json=tracking_data
            )
            
            # 记录响应信息
            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应内容: {response.text}")
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 检查API响应
            if result.get("code") != 0:
                logger.error(f"API返回错误: {result.get('message')}")
                logger.error(f"完整响应: {json.dumps(result, ensure_ascii=False)}")
                return None
                
            return result.get("data")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"注册物流单号时发生错误: {str(e)}")
            return None

    def get_tracking_info(self, tracking_numbers: List[str]) -> Optional[Dict]:
        """
        获取物流轨迹信息
        
        Args:
            tracking_numbers: 物流单号列表
            
        Returns:
            Dict: 包含轨迹信息的字典，如果失败则返回None
        """
        try:
            # 准备请求参数
            payload = {
                "tracking_numbers": tracking_numbers
            }

            # 记录请求信息
            logger.debug(f"发送请求到: {self.base_url}/register")
            logger.debug(f"请求头: {self.headers}")
            logger.debug(f"请求体: {json.dumps(payload, ensure_ascii=False)}")

            # 发送请求
            response = requests.post(
                f"{self.base_url}/register",
                headers=self.headers,
                json=payload
            )
            
            # 记录响应信息
            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应内容: {response.text}")
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 检查API响应
            if result.get("code") != 0:
                logger.error(f"API返回错误: {result.get('message')}")
                logger.error(f"完整响应: {json.dumps(result, ensure_ascii=False)}")
                return None
                
            return result.get("data")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取轨迹信息时发生错误: {str(e)}")
            return None

    def get_tracking_details(self, tracking_numbers: List[Dict]) -> Optional[Dict]:
        """
        获取物流轨迹详情
        
        Args:
            tracking_numbers: 物流单号列表，每个元素包含以下字段：
                - number: 物流单号（必填）
                - carrier: 运输商代码（可选）
            
        Returns:
            Dict: 包含轨迹详情的字典，如果失败则返回None
        """
        try:
            # 验证单号数量
            if len(tracking_numbers) > 40:
                logger.error(f"单号数量超过限制: {len(tracking_numbers)}")
                return None

            # 记录请求信息
            logger.debug(f"发送请求到: {self.base_url}/gettrackinfo")
            logger.debug(f"请求头: {self.headers}")
            logger.debug(f"请求体: {json.dumps(tracking_numbers, ensure_ascii=False)}")

            # 发送请求
            response = requests.post(
                f"{self.base_url}/gettrackinfo",
                headers=self.headers,
                json=tracking_numbers
            )
            
            # 记录响应信息
            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应内容: {response.text}")
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 检查API响应
            if result.get("code") != 0:
                logger.error(f"API返回错误: {result.get('message')}")
                logger.error(f"完整响应: {json.dumps(result, ensure_ascii=False)}")
                return None
                
            return result.get("data")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取轨迹详情时发生错误: {str(e)}")
            return None

def format_tracking_info(tracking_data: List[Dict]) -> str:
    """
    格式化轨迹信息为易读的字符串
    
    Args:
        tracking_data: 轨迹数据列表
        
    Returns:
        str: 格式化后的轨迹信息
    """
    if not tracking_data:
        return "未找到轨迹信息"
        
    formatted_info = []
    for track in tracking_data:
        track_info = [
            f"单号: {track.get('number', 'N/A')}",
            f"承运商: {track.get('carrier_code', 'N/A')}",
            f"状态: {track.get('status', 'N/A')}"
        ]
        
        if track.get('destination_country'):
            track_info.append(f"目的国: {track['destination_country']}")
            
        if track.get('tracking_info'):
            track_info.append("\n轨迹详情:")
            for info in track['tracking_info']:
                # 转换时间戳为可读格式
                time_str = datetime.fromtimestamp(info.get('time', 0)).strftime('%Y-%m-%d %H:%M:%S')
                track_info.append(
                    f"- {time_str} "
                    f"{info.get('location', '未知地点')}: "
                    f"{info.get('status', 'N/A')}"
                )
                
        formatted_info.append("\n".join(track_info))
        
    return "\n\n".join(formatted_info)

def format_register_result(result: Dict) -> str:
    """
    格式化注册结果为易读的字符串
    
    Args:
        result: 注册结果字典
        
    Returns:
        str: 格式化后的注册结果
    """
    if not result:
        return "注册失败"
        
    formatted_info = []
    
    # 处理成功注册的单号
    if result.get("accepted"):
        formatted_info.append("成功注册的单号:")
        for item in result["accepted"]:
            info = [
                f"单号: {item.get('number', 'N/A')}",
                f"运输商代码: {item.get('carrier', 'N/A')}"
            ]
            if item.get('tag'):
                info.append(f"标签: {item['tag']}")
            if item.get('email'):
                info.append(f"邮箱: {item['email']}")
            if item.get('lang'):
                info.append(f"语言: {item['lang']}")
            formatted_info.append("\n".join(info))
    
    # 处理被拒绝的单号
    if result.get("rejected"):
        formatted_info.append("\n被拒绝的单号:")
        for item in result["rejected"]:
            info = [f"单号: {item.get('number', 'N/A')}"]
            if item.get('tag'):
                info.append(f"标签: {item['tag']}")
            if item.get('error'):
                error = item['error']
                info.append(f"错误代码: {error.get('code', 'N/A')}")
                info.append(f"错误信息: {error.get('message', 'N/A')}")
            formatted_info.append("\n".join(info))
    
    return "\n\n".join(formatted_info)

def format_tracking_details(result: Dict) -> str:
    """
    格式化轨迹详情为易读的字符串
    
    Args:
        result: 轨迹详情数据
        
    Returns:
        str: 格式化后的轨迹详情
    """
    if not result:
        return "未找到轨迹详情"
        
    formatted_info = []
    
    # 处理成功获取的单号
    if result.get("accepted"):
        formatted_info.append("成功获取轨迹的单号:")
        for item in result["accepted"]:
            track_info = item.get("track_info", {})
            info = [
                f"单号: {item.get('number', 'N/A')}",
                f"运输商代码: {item.get('carrier', 'N/A')}"
            ]
            
            # 添加发货信息
            if track_info.get("shipping_info"):
                shipping = track_info["shipping_info"]
                if shipping.get("shipper_address"):
                    shipper = shipping["shipper_address"]
                    info.append("\n发货地址:")
                    info.append(f"国家: {shipper.get('country', 'N/A')}")
                    info.append(f"省份: {shipper.get('state', 'N/A')}")
                    info.append(f"城市: {shipper.get('city', 'N/A')}")
                    info.append(f"邮编: {shipper.get('postal_code', 'N/A')}")
                
                if shipping.get("recipient_address"):
                    recipient = shipping["recipient_address"]
                    info.append("\n收货地址:")
                    info.append(f"国家: {recipient.get('country', 'N/A')}")
                    info.append(f"省份: {recipient.get('state', 'N/A')}")
                    info.append(f"城市: {recipient.get('city', 'N/A')}")
                    info.append(f"邮编: {recipient.get('postal_code', 'N/A')}")
            
            # 添加最新状态
            if track_info.get("latest_status"):
                status = track_info["latest_status"]
                info.append(f"\n最新状态: {status.get('status', 'N/A')}")
                if status.get("sub_status"):
                    info.append(f"子状态: {status['sub_status']}")
            
            # 添加最新事件
            if track_info.get("latest_event"):
                event = track_info["latest_event"]
                info.append("\n最新事件:")
                info.append(f"时间: {event.get('time_iso', 'N/A')}")
                info.append(f"描述: {event.get('description', 'N/A')}")
                info.append(f"地点: {event.get('location', 'N/A')}")
            
            # 添加时效信息
            if track_info.get("time_metrics"):
                metrics = track_info["time_metrics"]
                info.append("\n时效信息:")
                info.append(f"订单后天数: {metrics.get('days_after_order', 'N/A')}")
                info.append(f"运输天数: {metrics.get('days_of_transit', 'N/A')}")
                info.append(f"最后更新天数: {metrics.get('days_after_last_update', 'N/A')}")
                
                if metrics.get("estimated_delivery_date"):
                    delivery = metrics["estimated_delivery_date"]
                    info.append(f"预计送达: {delivery.get('from', 'N/A')} 至 {delivery.get('to', 'N/A')}")
            
            # 添加包裹信息
            if track_info.get("misc_info"):
                misc = track_info["misc_info"]
                info.append("\n包裹信息:")
                info.append(f"重量: {misc.get('weight_raw', 'N/A')}")
                info.append(f"件数: {misc.get('pieces', 'N/A')}")
                info.append(f"尺寸: {misc.get('dimensions', 'N/A')}")
                info.append(f"服务类型: {misc.get('service_type', 'N/A')}")
            
            formatted_info.append("\n".join(info))
    
    # 处理被拒绝的单号
    if result.get("rejected"):
        formatted_info.append("\n被拒绝的单号:")
        for item in result["rejected"]:
            info = [f"单号: {item.get('number', 'N/A')}"]
            if item.get('error'):
                error = item['error']
                info.append(f"错误代码: {error.get('code', 'N/A')}")
                info.append(f"错误信息: {error.get('message', 'N/A')}")
            formatted_info.append("\n".join(info))
    
    return "\n\n".join(formatted_info)

# 使用示例
if __name__ == "__main__":
    # 创建API实例
    tracking_api = TrackingAPI()
    
    # # 测试注册物流单号
    # tracking_data = [
    #     {
    #         "number": "YDH1009542464AZ",
    #         "carrier": 190200,  # 运输商代码
    #         "order_no": "TEST123456",  # 订单编号
    #         "order_time": "2024/3/26",  # 订单日期
    #         "tag": "测试单号",  # 自定义标签
    #         "remark": "测试备注",  # 自定义备注
    #         "auto_detection": True  # 自动检测运输商
    #     }
    # ]
    
    # result = tracking_api.register_tracking_numbers(tracking_data)
    
    # if result:
    #     print(format_register_result(result))
    # else:
    #     print("注册物流单号失败")

    # 测试获取轨迹详情
    tracking_data = [
        {
            "number": "YDH1009586592AZ",
            "carrier": 190200
        }
    ]
    
    result = tracking_api.get_tracking_details(tracking_data)
    if result:
        print(format_tracking_details(result))
    else:
        print("获取轨迹详情失败")
