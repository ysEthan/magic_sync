from django.apps import AppConfig

class MysiteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mysite'

    def ready(self):
        """
        在Django应用启动时执行
        """
        try:
            # 只在主进程中启动调度器
            import os
            if os.environ.get('RUN_MAIN', None) != 'true':
                from utils import scheduler
                scheduler.start()
        except Exception as e:
            print(f"Error starting scheduler: {e}") 