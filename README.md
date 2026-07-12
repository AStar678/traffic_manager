# VisionDrive 智视驾

## 阿里云真实短信

后端默认使用 Mock 验证码。如需在 macOS/Linux 上启用阿里云号码认证短信：

1. 复制 `backend/.env.example` 为 `backend/.env.local` 并填写已审核的账号、签名和模板配置。
2. 在项目根目录执行 `backend/run-backend-aliyun.sh`。

`.env.local` 已被 Git 忽略，禁止把 AccessKey 写入 `application.yml` 或其他受版本控制的文件。启动日志出现“阿里云号码认证服务初始化成功”表示真实短信发送器已加载；只有调用发送验证码接口时才会产生短信费用。

### 注册与验证码接口

发送验证码时必须明确用途，注册验证码与登录验证码不能混用：

```json
POST /api/v1/auth/send-code
{"phone":"13800138000","purpose":"REGISTER"}
```

`purpose` 可取 `REGISTER` 或 `LOGIN`。注册时必须提交已验证的手机号；短信登录仅允许已经注册的手机号。

```json
POST /api/v1/auth/register
{
  "username":"vision_user",
  "email":"user@example.com",
  "password":"StrongPass123!",
  "phone":"13800138000",
  "code":"123456"
}
```

注册成功会返回 JWT 并自动登录。验证码 5 分钟有效、最多尝试 5 次、验证成功后立即失效；同一手机号的发送冷却与每日限额由登录和注册用途共享。

## 云端 MySQL

复制 `backend/.env.example` 为 `backend/.env.local`，填写云数据库、JWT 和 SSH 隧道配置后执行：

```bash
cd backend
./run-backend-cloud.sh
```

脚本会建立本机到服务器 MySQL 的 SSH 隧道，再启动后端；退出后端时隧道会一并关闭。车辆配置接口只从 JWT 获取当前用户 ID，不接受客户端指定 userId。

### 用户识别结果表

三类识别结果分别保存在以下表中：

- `license_plate_recognition_result`：车牌识别结果
- `police_gesture_recognition_result`：交警手势识别结果
- `user_gesture_recognition_result`：用户手势识别结果

三张表均使用 `(user_id, created_at)` 联合主键，并包含 `recognition_result`（完整识别结果 JSON）和 `image_source`（图片 URL、摄像头编号或沙盘流标识）。`user_id` 外键关联 `user.id`，删除用户时同步删除其识别结果。建表脚本见 `scripts/create_recognition_result_tables.sql`。

> 车载视觉感知与人机交互Web系统

## 项目简介

本项目面向智慧交通与智能座舱场景，构建一个前后端分离的Web系统，融合**计算机视觉**（车牌检测OCR、人体关键点检测、手部关键点检测）、**大语言模型**（LLM API调用、自然语言告警摘要生成）、**智能体技术**（自主感知-决策-告警）。

## 技术架构

```
┌─────────────────────────────────┐
│   前端  Vue 3 + Element Plus     │  端口: 5173
└──────────────┬──────────────────┘
               │ HTTP REST + WebSocket
┌──────────────┴──────────────────┐
│   后端  Java Spring Boot         │  端口: 8080
│   · 用户认证 · 文件管理          │
│   · 数据库 · Alert Agent         │
└──────────────┬──────────────────┘
               │ HTTP REST (内部)
┌──────────────┴──────────────────┐
│   算法服务  Python FastAPI       │  端口: 8000
│   · 车牌识别 · 交警手势 · 车主手势 │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 虚拟摄像头服务 Python FastAPI    │  端口: 8010
│ · 本机摄像头 · 测试视频 · 测试图片 │
│ · WebRTC预览 · PNG/JPEG抓拍      │
└─────────────────────────────────┘
```

## 项目结构

```
vision-drive/
├── frontend/        # Vue 3 前端
├── backend/         # Java Spring Boot 后端
├── algorithm/       # Python FastAPI 算法微服务
├── camera_service/  # Python FastAPI 虚拟摄像头微服务
├── docs/            # 项目文档
├── data/            # 测试数据与样本
├── docker/          # Docker 部署配置
└── scripts/         # 工具脚本
```

## 快速开始

完整启动步骤、后台运行和健康检查见：[启动教程](docs/启动教程.md)。

### 1. 前端
```bash
cd frontend
npm install
npm run dev
```

### 2. 后端
```bash
cd backend
mvn spring-boot:run
```

### 3. 算法服务
```bash
cd algorithm
pip install -r requirements.txt
python main.py
```

### 4. 虚拟摄像头服务
```bash
cd camera_service
../algorithm/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8010
```

前端默认读取 `http://127.0.0.1:8010`，也可以通过 `VITE_CAMERA_URL` 覆盖。
摄像头服务自带独立管理台：`http://127.0.0.1:8010/ui`，不接入主前端路由。

## 团队

| 角色 | 职责 |
|---|---|
| 组长 / 后端工程师 | Java后端 + API + DB + Agent + 项目管理 |
| 前端工程师 | Vue3前端 + 页面 + 组件 + WebSocket |
| 算法工程师 | 模型选型 + 推理pipeline + 精度测试 |
| 测试工程师 | 测试用例 + 功能/性能测试 + 部署 |
| 文档与项目管理 | 文档撰写 + 日报 + PPT（也参与开发） |

## 文档

- [启动教程](docs/启动教程.md)
- [产品需求文档](docs/prd/产品需求文档.md)
- [产品设计文档](docs/design/产品设计文档.md)
- [后端算法通讯协议](docs/design/后端算法通讯协议.md)
