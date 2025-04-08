from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django.conf import settings
import logging
from datetime import datetime, timedelta
from .product_sync_by_date import sync_products_by_date
from .order_sync import order_sync
from .purchase_sync import purchase_sync
from notification.order_alert import notify_order_sync_success, notify_order_sync_error

logger = logging.getLogger(__name__)

def sync_daily_data():
    """执行每日数据同步"""
    try:
        # 1. 同步商品数据
        logger.info("开始同步商品数据...")
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        sync_products_by_date(start_time=start_time.strftime('%Y-%m-%d %H:%M:%S'),
                            end_time=end_time.strftime('%Y-%m-%d %H:%M:%S'))
        logger.info("商品数据同步完成")

        # 2. 同步订单数据
        logger.info("开始同步订单数据...")
        success_count, error_count = order_sync.sync_orders(
            start_time=start_time.strftime('%Y-%m-%d %H:%M:%S'),
            end_time=end_time.strftime('%Y-%m-%d %H:%M:%S')
        )
        logger.info(f"订单数据同步完成，成功: {success_count}，失败: {error_count}")

        # 3. 同步采购单数据
        logger.info("开始同步采购单数据...")
        success_count, error_count = purchase_sync.sync_purchase_orders(
            start_time=start_time.strftime('%Y-%m-%d %H:%M:%S'),
            end_time=end_time.strftime('%Y-%m-%d %H:%M:%S')
        )
        logger.info(f"采购单数据同步完成，成功: {success_count}，失败: {error_count}")

        logger.info("所有数据同步任务完成")
    except Exception as e:
        logger.error(f"数据同步失败: {str(e)}")
        logger.exception("详细错误信息:")

def sync_incremental_data():
    """执行每小时增量订单同步"""
    try:
        logger.info("开始执行增量订单同步...")
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)  # 只同步最近1小时的数据
        
        success_count, error_count = order_sync.sync_orders(
            start_time=start_time.strftime('%Y-%m-%d %H:%M:%S'),
            end_time=end_time.strftime('%Y-%m-%d %H:%M:%S')
        )
        logger.info(f"增量订单同步完成，成功: {success_count}，失败: {error_count}")

        # 发送同步完成通知
        notify_order_sync_success(success_count, error_count)

    except Exception as e:
        error_message = f"增量订单同步失败: {str(e)}"
        logger.error(error_message)
        logger.exception("详细错误信息:")
        # 发送同步失败通知
        notify_order_sync_error(error_message)

def start():
    """启动定时任务调度器"""
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # 删除所有已存在的任务
    scheduler.remove_all_jobs()

    # 添加每天凌晨2点的数据同步任务
    scheduler.add_job(
        sync_daily_data,
        trigger=CronTrigger(hour=2, minute=0),
        id='daily_sync',
        name='每天凌晨2点同步数据',
        replace_existing=True
    )

    # 添加每小时30分的增量订单同步任务
    scheduler.add_job(
        sync_incremental_data,
        trigger=CronTrigger(minute=30),  # 每小时的第30分钟执行
        id='hourly_order_sync',
        name='每小时同步订单数据',
        replace_existing=True
    )

    try:
        logger.info("正在启动调度器...")
        scheduler.start()
        logger.info("调度器启动成功")
    except Exception as e:
        logger.error(f"启动调度器失败: {str(e)}")
        logger.exception("详细错误信息:")
        raise
