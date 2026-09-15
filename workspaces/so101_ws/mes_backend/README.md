# SO-101 MES Backend (Spring Boot)

最小可用后端骨架，包含：
- 工单 CRUD（内存实现）
- 工单下发到 ROS2（通过 rosbridge）
- STOMP WebSocket 状态推送（`/ws` + `/topic/task-status`）

## 运行

```bash
cd mes_backend
mvn spring-boot:run
```

默认配置：
- HTTP: `http://127.0.0.1:8080`
- rosbridge: `ws://127.0.0.1:9090`

## API

### 创建工单
```bash
curl -X POST http://127.0.0.1:8080/api/orders \
  -H "Content-Type: application/json" \
  -d '{"orderId":"order-001","actionTemplateId":"pick_place_red"}'
```

### 查询工单列表
```bash
curl http://127.0.0.1:8080/api/orders
```

### 下发工单
```bash
curl -X POST http://127.0.0.1:8080/api/orders/order-001/dispatch \
  -H "Content-Type: application/json" \
  -d '{"priority":1}'
```

### 连接 rosbridge
```bash
curl -X POST http://127.0.0.1:8080/api/ros/connect
```
