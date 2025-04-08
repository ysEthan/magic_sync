import hashlib
import base64
import hmac
import time
import requests
import json
import logging

logger = logging.getLogger(__name__)

class FeishuNotification:
    def __init__(self):
        self.secret = 'qJQkYxO9hIEZyrACaMTAtb'
        self.webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/ff7f7f54-6bb2-494c-9809-89b44c8836f8"
        self.erp_url = "https://kj.qizhishangke.com/s/erp/#/orders/order_processing?type=pendingr"

    def gen_sign(self, timestamp):
        """生成签名"""
        string_to_sign = f'{timestamp}\n{self.secret}'
        hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        return base64.b64encode(hmac_code).decode('utf-8')

    def send_message(self, text1, text2='', text3='', text4='', title="Ring Ring Ring"):
        try:
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
                                "content": text1,
                                "tag": "lark_md"
                            }
                        }
                    ],
                    "header": {
                        "title": {
                            "content": title,
                            "tag": "plain_text"
                        }
                    }
                }
            }

            # 添加额外的消息内容
            for text in [text2, text3, text4]:
                if text:
                    data["card"]["elements"].append({
                        "tag": "div",
                        "text": {
                            "content": text,
                            "tag": "lark_md"
                        }
                    })

            # 添加ERP链接按钮
            data["card"]["elements"].append({
                "actions": [{
                    "tag": "button",
                    "text": {
                        "content": "ERP链接",
                        "tag": "lark_md"
                    },
                    "url": self.erp_url,
                    "type": "default",
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
        text1 = f"**同步失败**\n错误信息：{error_message}"
    else:
        title = f"✅ {sync_type_text}完成"
        text1 = f"**同步完成**\n- 处理数量：{processed_count}\n- 总数量：{total_count}"

    text2 = f"同步时间：{time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    return feishu.send_message(text1, text2, title=title)
