# VisionDrive 智视驾

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
