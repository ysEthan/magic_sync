import hashlib
import base64
import hmac
import time
import requests
import json
import logging
from django.db import connection
from datetime import datetime

logger = logging.getLogger(__name__)

class FeishuNotification:
    def __init__(self):
        self.secret = 'qJQkYxO9hIEZyrACaMTAtb'
        self.webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/ff7f7f54-6bb2-494c-9809-89b44c8836f8"
        self.erp_url = "https://kj.qizhishangke.com/s/erp/#/orders/order_processing?type=pendingr"

    def get_order_stats(self):
        """获取订单统计数据"""
        try:
            with connection.cursor() as cursor:
                query = """
                select 
                    DATE_FORMAT(order_place_time, '%m-%d') as week_format,
                    count(id) as order_count,
                    sum(if(`status`='已发货',1,0)) as shipped,
                    sum(if(status in ('待处理','配货中'),1,0)) as pending
                from trade_order
                where status <>'已取消' and shop_id=5
                group by 1
                order by 1 desc 
                limit 6
                """
                
                cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
                
                return results
                
        except Exception as e:
            logger.error(f"查询订单统计数据失败: {str(e)}")
            return None

    def gen_sign(self, timestamp):
        """生成签名"""
        string_to_sign = f'{timestamp}\n{self.secret}'
        hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        return base64.b64encode(hmac_code).decode('utf-8')

    def format_order_stats(self, stats):
        if not stats:
            return "暂无订单数据"
            
        text = "📊 最近6天订单统计\n"
        text += "日期    订单数  已发货  待处理\n"
        
        for row in stats:
            total = int(row['order_count'])
            shipped = int(row['shipped'])
            pending = int(row['pending'])
            
            # 使用空格对齐，移除分隔线
            text += f"{row['week_format']}  {total:2d}      {shipped:2d}      {pending:2d}\n"
        
        # 汇总信息放在同一行
        total_orders = sum(int(row['order_count']) for row in stats)
        total_shipped = sum(int(row['shipped']) for row in stats)
        total_pending = sum(int(row['pending']) for row in stats)
        ship_rate = (total_shipped / total_orders * 100) if total_orders > 0 else 0
        
        text += f"总计: {total_orders}  已发货: {total_shipped}  待处理: {total_pending}  发货率: {ship_rate:.1f}%"
        
        return text

    def send_message(self, text1, text2='', text3='', text4='', title="📦 订单统计报告"):
        try:
            # 获取订单统计数据
            order_stats = self.get_order_stats()
            stats_text = self.format_order_stats(order_stats)
            
            timestamp = str(int(time.time()))
            data = {
                "timestamp": timestamp,       
                "sign": self.gen_sign(timestamp), 
                "msg_type": "interactive",
                "card": {
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "content": stats_text,
                                "tag": "lark_md"
                            }
                        }
                    ],
                    "header": {
                        "title": {
                            "content": title,
                            "tag": "plain_text"
                        },
                        "template": "blue"
                    }
                }
            }

            # 添加ERP链接按钮
            data["card"]["elements"].append({
                "actions": [{
                    "tag": "button",
                    "text": {
                        "content": "🔗 查看详情",
                        "tag": "lark_md"
                    },
                    "url": self.erp_url,
                    "type": "primary",
                    "value": {}
                }],
                "tag": "action"
            })

            json_data = json.dumps(data)
            response = requests.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                data=json_data
            )
            
            result = response.json()
            if result['code'] != 0:
                logger.error(f"发送消息失败: {response.text}")
                return False
            else:
                logger.info(f"消息发送成功: {response.text}")
                return True

        except Exception as e:
            logger.error(f"发送消息时发生错误: {str(e)}")
            return False

# 创建一个全局的通知实例
feishu = FeishuNotification()

def send_order_sync_notification(sync_type, processed_count, total_count, error_message=None):
    # 发送订单同步状态通知
    sync_type_text = "订单" + ("完整同步" if sync_type == 'full' else "增量同步")
    
    if error_message:
        title = f"🔴 {sync_type_text}失败"
        return feishu.send_message("", title=title)
    else:
        title = f"✅ {sync_type_text}完成"
        return feishu.send_message("", title=title)
