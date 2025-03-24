cd /code/magic_page
git clone https://github.com/ysEthan/magic_page.git

cd /code/magic/magic_page
git fetch origin && git checkout -b f08_procurement origin/f08_procurement





"00 创建项目============================="
npm create vue@3.14.1
--关联远程仓库
	git init && git add . && git commit -m "first commit" && git branch -M main && git remote add origin https://github.com/ysEthan/magic_page.git && git push -u origin main

"01 提交默认分支============================="
git checkout -b b01_init
git add . && git commit -m "init" && git push

npm install
npm run dev




"03 用户认证============================="
git checkout -b b03_user_auth
git add . && git commit -m "user_auth" && git push

我要搭建一个ERP系统，主要满足供应链管理、和生产管理的需求，采用前后端分离的架构来设计。
本项目是基于Vue3框架的前端项目，后端采用Django框架

系统主要包含：用户认证、商品管理、生产管理，采购管理、库存管理、销售管理、物流管理。以及一些报表页面

注意，我们已经在Vue的项目根目录下，后端已经完成了用户认证功能，接下来，让我们在前端也实现用户认证相关的功能

以下是关于后端接口的说明文档，

以下是Django用户认证相关的模型文件：
以下是Django用户认证相关的视图函数：



"04 商品管理============================="
git checkout -b b04_product
git add . && git commit -m "b04_product" && git push


我们已经完成了用户认证的部分

接下来，我们要继续完成商品管理的部分，请先帮我新建4个基础的空白页面，品牌管理/分类管理/SPU管理/SKU管理，页面上暂时不需要任何内容

四个页面文件都放在views/product下即可，避免目录层级太多



"05 生产管理============================="
git checkout -b f05_production
git add . && git commit -m "production" && git push

git add . && git commit -m "test" && git checkout b04_product && git branch -D f05_production


我们已经完成了商品管理模块，现在，让我们继续实现生产管理。
后端功能已经完成，请参考API
模型文件
视图文件，
帮我实现前段相关功能，首先，创建一个任务管理的视图

新增/编辑任务的表单
生产步骤的管理
任务状态的流转
评论功能

调整列表，
把属性列中的优先级，单独放一列


"06 生产步骤============================="
git checkout -b f06_production_step
git add . && git commit -m "production_step" && git push

接下来让我们完善生产步骤管理
首先需要实现添加步骤的功能,请参考一下API文档，模型文件，文件，实现前端功能，
再任务详情页面的按钮，添加实际的功能

调整任务详情的页面展示
1，各类信息分模块展示
2，调整紧凑一些

添加步骤时报错了，帮我排查解决



"07 采购管理 ============================="
git checkout -b f07_procurement
git add . && git commit -m "procurement" && git push

接下来让我们继续实现采购管理模块。
后端功能已经完成，,请参考一下API文档，模型文件，视图文件，序列化器文件实现前端功能，


接下来让我们继续实现库存管理模块。
后端功能已经完成，,请参考一下API文档，模型文件，视图文件，序列化器文件实现前端功能，


接下来让我们继续完善订单管理的部分
后端功能已经完成，,请参考一下API文档，模型文件，视图文件，序列化器文件实现前端功能，



接下来让我们继续完善物流管理的部分
后端功能已经完成，,请参考一下API文档，模型文件，视图文件，序列化器文件实现前端功能，

继续实现包裹管理页面


"08 采购管理优化 ============================="
git checkout -b f08_procurement

git add . && git commit -m "procurement p" && git push