# 本地演示安全与运行配置

2026-09-11：取消 local-admin 兜底和默认密码。所有 API（登录除外）需要 X-Session-Token；管理员操作仍额外要求管理员角色，会话固定 8 小时失效。

启动前从安全的部署环境注入 `SO101_ADMIN_PASSWORD` 和 `SO101_OPERATOR_PASSWORD`，未设置的角色禁止登录；不要把密码写入仓库。管理员用户名为 admin；员工使用其姓名及操作员密码。当前不是完整的多用户身份系统，默认保持 127.0.0.1，勿直接公网部署。

不再自动 sudo/chmod 666 串口。由设备所有者配置 dialout 组或最小权限 udev 规则，重新登录后确认访问权限。

`SO101_CAMERA` 覆盖摄像头，默认数字索引 0。ROS 桥读取 `SO101_ROS2_SETUP`、`SO101_ROS2_WS_SETUP`、`SO101_ROS2_SCENE_DIR`。历史基线仍为 Humble/Gazebo Classic；缺少 setup 文件会明确拒绝启动。设置 Jazzy 路径并不等于完成迁移，需单独验证场景、消息类型和仿真依赖。

本次未连接舵机、未验证运动、未拆分历史单文件、未删除业务记录或发布包。
