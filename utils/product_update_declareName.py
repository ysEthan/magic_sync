import os
import json
import time
import logging
import hashlib
import requests
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 设置日志记录器
logger = logging.getLogger(__name__)

# 中英文映射字典
TRANSLATION_MAP = {
    "戒指": "ring",
    "胸针": "brooch",
    "摆件": "ornament",
    "材料": "material",
    "耳饰": "Earrings",
    "charms挂件": "Charms pendant",
    "冰箱贴": "refrigerator magnet",
    "耳环": "earring",
    "项链": "necklace",
    "键帽": "keycap",
    "KE1113": "KE1113",
    "手链": "Bracelet",
    "恶魔之眼项链": "Devil's Eye Necklace",
    "爱心项链": "Heart Necklace",
    "鹦鹉胸针": "Parrot brooch",
    "毛绒": "Plush",
    "小挂件": "Small pendant",
    "pantone色卡": "Pantone color card",
    "电镀色卡": "color chart",
    "铜": "copper",
    "树脂": "resin",
    "手镯": "bracelet",
    "宠物牌": "Pet tag",
    "毛绒玩具": "Plush toys",
    "配件": "accessory",
    "链条": "chain",
    "静土之歌心形耳夹款": "Quiet Earth Song Heart shaped Ear Clip",
    "钥匙牌": "key tag",
    "陶瓷摆件底座": "Ceramic ornament base",
    "陶瓷装饰摆件": "Ceramic decorative ornaments",
    "陶瓷餐具": "Ceramic tableware",
    "玩偶": "doll",
    "绒布袋": "Velvet bag",
    "售后卡": "After sales card",
    "纸袋": "paper bag",
    "包装盒": "packaging box",
    "手办": "Garage Kit",
    "吊坠": "Pendant",
    "鬼娃娃": "Ghost doll",
    "戒子": "Ring",
    "香炉": "censer",
    "宠物项圈": "pet collar",
    "PVC动物玩具10cm": "PVC animal toy 10cm",
    "铜做旧+滴油吊坠链45+5cm": "Copper antique+drip oil pendant chain 45+5cm",
    "铜做旧吊坠链50+5cm": "Copper antique pendant chain 50+5cm",
    "吊牌": "Tag",
    "样品卡": "sample card",
    "色板卡": "Color palette card",
    "盒子": "box",
    "面罩": "face shield",
    "面饰": "Finishing",
    "手提袋": "tote",
    "贴条": "Stick strips",
    "培育蓝宝": "Cultivate Blue Treasure",
    "手饰": "Jewelry",
    "首饰套装": "Jewelry Set",
    "包装耗材": "Packaging consumables",
    "GRA证书": "GRA certificate",
    "套装": "suit",
    "物料": "material",
    "腿链": "Leg chain",
    "鼻饰": "Nose accessories",
    "腰链": "waist chain",
    "身体链": "Body Chain",
    "脚链": "anklet"
}

def translate_to_english(text):
    """使用映射表将中文文本翻译成英文"""
    try:
        # 尝试直接从映射表中获取翻译
        if text in TRANSLATION_MAP:
            translated = TRANSLATION_MAP[text]
            logger.info(f"找到映射翻译: {text} -> {translated}")
            return translated
        
        # 如果找不到完全匹配，尝试查找包含关系
        for cn, en in TRANSLATION_MAP.items():
            if cn in text:
                translated = text.replace(cn, en)
                logger.info(f"使用部分映射翻译: {text} -> {translated}")
                return translated
        
        # 如果没有找到任何匹配，返回默认值
        logger.warning(f"未找到翻译映射: {text}，使用默认值 'others Accessories'")
        return "others Accessories"
            
    except Exception as e:
        logger.error(f"翻译出错: {str(e)}")
        return "others Accessories"  # 发生错误时也返回默认值

def generate_sign(body):
    """生成API签名"""
    app_name = os.getenv('API_APP_NAME', 'mathmagic')
    app_key = os.getenv('API_APP_KEY', '82be0592545283da00744b489f758f99')
    sid = os.getenv('API_SID', 'mathmagic')
    
    headers = {
        'Content-Type': 'application/json'
    }

    timestamp = str(int(time.time()))
    sign_str = f"{app_key}appName{app_name}body{body}sid{sid}timestamp{timestamp}{app_key}"
    sign = hashlib.md5(sign_str.encode()).hexdigest()
    
    params = {
        "appName": app_name,
        "sid": sid,
        "sign": sign,
        "timestamp": timestamp,
    }
    return params, headers

def update_declareName(product):
    """更新商品的申报名称
    Args:
        product: 商品数据字典
    """
    try:
        logger.info(f"开始更新商品申报名称: {product['goodsNo']}")
        # print(1234564640638)
        
        # 获取英文翻译
        english_name = translate_to_english(product['goodsName'])
        logger.info(f"商品名称翻译结果: {product['goodsName']} -> {english_name}")
        
        # 构造更新数据，只包含必要字段
        update_data = [{
            "goodsNo": product['goodsNo'],
            "goodsName": product['goodsName'],
            "specList": [{
                "specNo": product['specNo'],
                "specName": product['specName'],
                "declareNameCn": product['goodsName'],  # 使用商品名称作为中文申报名
                "declareNameEn": english_name,  # 使用翻译后的英文名称
                "declarePrice": float(product.get('declarePrice', 0)) or 2  # 如果原值为0或不存在，则使用2
            }]
        }]

        # 转换为JSON字符串
        body_str = json.dumps(update_data, ensure_ascii=False, separators=(",", ":"))
        params, headers = generate_sign(body_str)

        # 调用API更新商品
        api_url = os.getenv('API_UPDATE_URL', 'https://openapi.qizhishangke.com/api/openservices/product/v1/push/spec')
        logger.info(f"调用API更新商品，URL: {api_url}")
        logger.info(f"请求参数: {params}")
        logger.info(f"请求数据: {body_str}")
        
        response = requests.post(api_url, params=params, headers=headers, data=body_str.encode('utf-8'))
        logger.error(f"API响应状态码: {response.status_code}")
        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.text}")

        result = response.json()
        if result['code'] != 200:
            raise Exception(f"业务处理失败: {result['message']}")

        logger.info(f"成功更新商品申报名称: {product['goodsNo']}")
        return True

    except Exception as e:
        logger.error(f"更新商品申报名称失败 {product['goodsNo']}: {str(e)}")
        return False