cd /code/magic_sync
git clone https://github.com/ysEthan/magic_sync.git

cd /code/magic/magic_sync
git fetch origin && git checkout -b s03_product origin/s03_product





"00 创建项目============================="
django-admin startproject mysite && rename mysite magic_sync
--关联远程仓库
git init && git add . && git commit -m "first commit" && git branch -M main && git remote add origin https://github.com/ysEthan/magic_sync.git && git push -u origin main





"03 商品同步============================="
git checkout -b s03_product
git add . && git commit -m "product" && git push




帮我重写@stock_in_sync.py同步入库单函数
需要实现的具体功能：
1，从API获取入库单数据
2，把数据写入到MYSQL数据库中，
3，每一条入库记录，需要创建一条库存记录，方便我们后续对库存做批次管理。

具体的功能实现，可以参考以下历史代码：



在页面上新增按钮来触发同步入库单
注意新增路由
注意添加视图函数





帮我重写  同步出库单函数
需要实现的具体功能：
1，从API获取出库单数据
2，把数据写入到MYSQL数据库中，
3，每一条出库记录，都需要相应在库存记录中扣减数量，扣减遵循FIFO原则，如果单条库存记录不够扣减，则拆分多条出库记录，按FIFO依次扣减，如果所有库存都不足以扣减，则跳过并记录错误。


具体的功能实现，可以参考以下历史代码：



在页面上新增按钮来触发同步出库单
注意新增路由
注意添加视图函数


帮我重写同步采购单函数
需要实现的具体功能：
1，从API获取采购单数据，
2，把数据写入到mysql数据库中
3，如果商品不存在，则新建

具体的功能实现，可以参考以下历史代码：




帮我重写订单同步函数@order_sync.py 
1，从API获取采购单数据，
2，把数据写入到mysql数据库中
3，如果商品不存在，则新建
4，同步更新或创建包裹
5，默认同步最近3天的订单

具体的功能实现，可以参考以下历史代码：

在页面上新增按钮来触发同步订单
注意新增路由
注意添加视图函数