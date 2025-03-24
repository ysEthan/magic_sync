import os
import uuid
import json
import time
import logging
import tempfile
import hashlib
import requests
from datetime import datetime
from django.db import connection
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

logger = logging.getLogger(__name__)

class ProductSyncBase:
    """商品同步基类"""
    
    def __init__(self):
        self.app_name = os.getenv('API_APP_NAME', 'mathmagic')
        self.app_key = os.getenv('API_APP_KEY', '82be0592545283da00744b489f758f99')
        self.sid = os.getenv('API_SID', 'mathmagic')
        self.api_url = os.getenv('API_URL', 'https://openapi.qizhishangke.com/api/openservices/product/v1/getItemList')
        self.image_upload_url = os.getenv('IMAGE_UPLOAD_URL', 'http://175.178.46.108:8002/api/products/products/upload_image/')
        self.image_base_url = os.getenv('IMAGE_BASE_URL', 'http://175.178.46.108:8002')
        self.media_prefix = os.getenv('MEDIA_PREFIX', 'http://175.178.46.108:8002/media/')

    def generate_filename(self, sku_code):
        """生成基于时间戳、SKU编码和UUID的文件名"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4()).replace('-', '')[:8]
        return f"{timestamp}_{sku_code}_{unique_id}.jpg"

    def get_relative_path(self, full_url):
        """从完整URL中提取相对路径"""
        if full_url.startswith('/media/'):
            return full_url[7:]
        filename = os.path.basename(full_url)
        return f"products/{filename}"

    def generate_sign(self, body):
        """生成API签名"""
        headers = {
            'Content-Type': 'application/json'
        }

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

    def upload_image(self, image_url, sku_code):
        """上传图片到目标系统"""
        try:
            logger.info(f"开始下载图片: {image_url}")
            response = requests.get(image_url)
            if response.status_code != 200:
                raise Exception(f"下载图片失败: {image_url}")

            new_filename = self.generate_filename(sku_code)
            logger.info(f"生成新文件名: {new_filename}")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
                logger.info(f"临时文件保存在: {temp_path}")

            logger.info(f"开始上传图片到: {self.image_upload_url}")
            with open(temp_path, 'rb') as f:
                files = {
                    'image': (
                        new_filename,
                        f,
                        'image/jpeg'
                    )
                }
                response = requests.post(self.image_upload_url, files=files)
                logger.info(f"上传响应状态码: {response.status_code}")
                logger.info(f"上传响应内容: {response.text}")
                
            os.unlink(temp_path)
            logger.info("临时文件已删除")

            if response.status_code not in [200, 201]:
                raise Exception(f"上传图片失败: HTTP状态码 {response.status_code}")

            result = response.json()
            logger.info(f"图片上传返回结果: {json.dumps(result, ensure_ascii=False)}")
            
            if 'image_url' not in result:
                raise Exception("上传响应中未包含 image_url")
            
            if result['image_url'].startswith('/media/'):
                target_path = result['image_url'][7:]
            else:
                target_path = result['image_url']
                
            logger.info(f"图片上传成功，相对路径: {target_path}")
            return target_path

        except Exception as e:
            logger.error(f"处理图片时发生错误: {str(e)}")
            logger.exception("详细错误信息:")
            return None

    def process_products(self, products):
        """处理商品数据并保存到数据库"""
        processed_count = 0
        with connection.cursor() as cursor:
            for product in products:
                try:
                    logger.info(f"Processing product: {product['goodsNo']}")

                    # 处理SPU数据
                    cursor.execute("""
                        INSERT INTO products_spu (
                            id, code, name, product_type, remark,
                            sales_channel, brand_id, category_id,
                            is_active, created_at, updated_at
                        )
                        VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, NOW(6), NOW(6)
                        )
                        ON DUPLICATE KEY UPDATE 
                        name = VALUES(name),
                        product_type = VALUES(product_type),
                        remark = VALUES(remark),
                        sales_channel = VALUES(sales_channel),
                        brand_id = VALUES(brand_id),
                        category_id = VALUES(category_id),
                        is_active = VALUES(is_active),
                        updated_at = NOW(6)
                    """, (
                        product['goodsId'],
                        product['goodsNo'],
                        product['goodsName'],
                        product.get('prop1', 'ready_made'),
                        product.get('remark', ''),
                        '',  # sales_channel
                        None,  # brand_id
                        1,  # category_id
                        True
                    ))

                    # 处理图片
                    image_url = product.get('imgUrl')
                    target_image_url = None
                    if image_url:
                        target_image_url = self.upload_image(image_url, product['specNo'])

                    # 处理SKU数据
                    cursor.execute("""
                        INSERT INTO products_product (
                            id, code, name, spu_id,
                            material, color, plating_process,
                            surface_treatment, weight, length,
                            width, height, other_dimensions,
                            suppliers_list, is_reviewed, is_active,
                            created_at, updated_at, images, main_image
                        )
                        VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            NOW(6), NOW(6), %s, %s
                        )
                        ON DUPLICATE KEY UPDATE 
                        name = VALUES(name),
                        spu_id = VALUES(spu_id),
                        material = VALUES(material),
                        color = VALUES(color),
                        plating_process = VALUES(plating_process),
                        surface_treatment = VALUES(surface_treatment),
                        weight = VALUES(weight),
                        length = VALUES(length),
                        width = VALUES(width),
                        height = VALUES(height),
                        other_dimensions = VALUES(other_dimensions),
                        suppliers_list = VALUES(suppliers_list),
                        is_active = VALUES(is_active),
                        images = VALUES(images),
                        main_image = VALUES(main_image),
                        updated_at = NOW(6)
                    """, [
                        product['specId'],
                        product['specNo'],
                        product['specName'],
                        product['goodsId'],
                        product.get('prop8', ''),
                        product.get('prop2', ''),
                        product.get('prop4', ''),
                        product.get('prop10', ''),
                        float(product.get('weight', 0) or 0),
                        float(product.get('length', 0) or 0),
                        float(product.get('width', 0) or 0),
                        float(product.get('height', 0) or 0),
                        product.get('prop3', ''),
                        json.dumps(product.get('providerList', [])),
                        False,
                        True,
                        json.dumps([target_image_url] if target_image_url else []),
                        target_image_url or ''
                    ])

                    # 处理申报品名
                    try:
                        declare_name_en = product.get('declareNameEn')
                        if not declare_name_en:
                            # 如果英文申报名为空，调用update_declareName进行处理
                            from .product_update_declareName import update_declareName
                            logger.info(f"Product {product['goodsNo']} has no declare name, updating...")
                            update_declareName(product=product)
                        else:
                            logger.info(f"Product {product['goodsNo']} already has declare name: {declare_name_en}")
                    except Exception as e:
                        logger.error(f"Error updating declareName for product {product['goodsNo']}: {str(e)}")
                        continue

                    processed_count += 1

                except Exception as e:
                    logger.error(f"Error processing product {product['goodsNo']}: {str(e)}")
                    continue




        return processed_count 