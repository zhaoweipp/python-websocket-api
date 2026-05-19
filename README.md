# Python WebSocket Serial Transparent Bridge

## 功能
- 串口收到的数据原样推送到前端：事件 `serial:data`
- 前端发送的数据原样写入串口：事件 `serial:write`
- 使用 engine.io 的 `sid` 作为客户端唯一标识
- 不做命令语义解析，不做协议解析，仅透明转发

## 增强点
- 串口粘包处理：读线程按“空闲间隔”聚合，空闲超过 `STICKY_IDLE_SECONDS` 后推送一包
- Socket 心跳：使用 socket.io/engine.io 内建 ping/pong（`ping_interval=25`, `ping_timeout=20`）
- 自动重连：前端 `reconnection: true`
- ACK：前端 `emit` 回调接收后端返回 `{ok: true/false}`

## 运行
```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

## 环境变量
- `SERIAL_PORT` 默认 `/dev/ttyUSB0`
- `SERIAL_BAUDRATE` 默认 `115200`
- `SERIAL_TIMEOUT` 默认 `0.05`
- `STICKY_IDLE_SECONDS` 默认 `0.02`
