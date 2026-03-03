# 🤖 AI 智能简历分析系统

> 自动解析 PDF 简历，利用大语言模型提取关键信息，并对简历与岗位需求进行智能匹配评分。

[![GitHub Pages](https://img.shields.io/badge/Demo-GitHub%20Pages-blue)](https://your-username.github.io/resume-ai/)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-teal)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📐 项目架构

```
resume-ai/
├── backend/                  # Python FastAPI 后端服务
│   ├── app/
│   │   ├── api/
│   │   │   ├── resume.py     # 简历上传与解析接口
│   │   │   └── match.py      # 岗位匹配评分接口
│   │   ├── services/
│   │   │   ├── pdf_parser.py   # PDF 文本提取与清洗
│   │   │   ├── ai_service.py   # AI 模型调用（DashScope/OpenAI）
│   │   │   └── cache_service.py # Redis / 内存缓存
│   │   ├── models/
│   │   │   └── schemas.py    # Pydantic 数据模型
│   │   └── main.py           # FastAPI 应用入口
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                 # 纯 HTML/CSS/JS 前端（可部署至 GitHub Pages）
│   ├── index.html
│   └── src/
│       ├── style.css
│       └── app.js
├── .github/
│   └── workflows/
│       └── deploy-pages.yml  # 自动部署至 GitHub Pages
└── README.md
```

---

## 🚀 技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| 后端框架 | **FastAPI** | 高性能异步框架，原生支持 Pydantic 类型校验，自动生成 OpenAPI 文档 |
| PDF 解析 | **pdfplumber + PyMuPDF** | 双引擎兼容，pdfplumber 精度高，PyMuPDF 作为降级方案 |
| AI 模型 | **通义千问（qwen-plus）** | 符合阿里云生态要求，中文理解能力强，支持 DashScope API |
| 缓存 | **Redis + 内存降级** | 优先使用 Redis 持久缓存，无 Redis 时自动降级为进程内存缓存 |
| 运行环境 | **阿里云函数计算 FC** | Serverless 架构，按需计费，支持 Docker 镜像部署 |
| 前端 | **原生 HTML/CSS/JS** | 零依赖，直接托管于 GitHub Pages，无需构建步骤 |

---

## ⚙️ 功能模块

### 模块一：简历上传与解析
- `POST /api/resume/upload` — 上传 PDF 文件（最大 10MB）
- 双引擎文本提取（pdfplumber → PyMuPDF 降级）
- 文本清洗：去除特殊字符、合并多余空白、规范化换行

### 模块二：关键信息提取（AI）
- 通义千问大模型分析简历文本，提取：
  - ✅ **必选**：姓名、电话、邮箱、地址
  - ⭐ **加分**：求职意向、期望薪资、工作年限、学历、项目经历、技能列表

### 模块三：简历评分与匹配（AI）
- `POST /api/match/` — 传入 `resume_id` + 岗位 JD 文本
- AI 分析返回：
  - 技能匹配率（已匹配 / 缺失技能列表）
  - 工作经验相关性评分（0~1）
  - 综合评分（0~100）
  - 录用建议（推荐 / 考虑 / 不推荐）
  - AI 分析摘要

### 模块四：结果返回与缓存
- 所有响应均为结构化 JSON
- **两级缓存**：
  - 解析结果按 `resume_id` 缓存
  - 匹配结果按 `resume_id + JD哈希` 缓存
- 优先读取缓存，避免重复 AI 调用

### 模块五：前端页面
- 三步引导式交互：上传 → 查看解析 → 岗位匹配
- 支持拖拽上传、文件预览
- 动态评分环形图表
- 技能匹配可视化（进度条 + 标签）
- 支持 **Mock 演示模式**（无需后端）
- 一键导出分析结果为 JSON

---

## 🛠️ 本地开发

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/resume-ai.git
cd resume-ai
```

### 2. 后端环境配置

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

复制环境变量文件并填写 API Key：

```bash
cp .env.example .env
# 编辑 .env，填写 DASHSCOPE_API_KEY
```

启动后端服务：

```bash
uvicorn app.main:app --reload --port 8000
```

访问 API 文档：`http://localhost:8000/docs`

### 3. 前端本地预览

直接用浏览器打开 `frontend/index.html`，或使用 Live Server：

```bash
# 使用 VS Code Live Server 扩展
# 或 Python 简易 HTTP 服务器：
cd frontend
python -m http.server 3000
```

---

## ☁️ 阿里云函数计算 FC 部署

### Docker 镜像部署

```bash
cd backend

# 构建镜像
docker build -t resume-ai-backend:latest .

# 本地测试
docker run -p 8000:8000 \
  -e DASHSCOPE_API_KEY=your_key \
  -e REDIS_URL=redis://your-redis:6379/0 \
  resume-ai-backend:latest
```

### 环境变量配置

在函数计算控制台配置以下环境变量：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `AI_BACKEND` | AI 后端类型 | `dashscope` |
| `DASHSCOPE_API_KEY` | 通义千问 API Key | `sk-xxx` |
| `AI_MODEL` | 模型名称 | `qwen-plus` |
| `REDIS_URL` | Redis 连接串（可选） | `redis://host:6379/0` |
| `CACHE_ENABLED` | 是否启用缓存 | `true` |

---

## 🌐 前端 GitHub Pages 部署

推送代码后，GitHub Actions 自动将 `frontend/` 目录部署至 GitHub Pages。

手动部署：
1. 进入仓库 **Settings → Pages**
2. 将 Source 设为 `GitHub Actions`
3. 推送代码，触发 `.github/workflows/deploy-pages.yml`

---

## 📡 API 文档

### `POST /api/resume/upload`

上传 PDF 简历并解析。

**请求**：`multipart/form-data`，字段名 `file`

**响应**：
```json
{
  "success": true,
  "resume_id": "uuid-xxx",
  "message": "简历解析成功",
  "data": {
    "resume_id": "uuid-xxx",
    "basic_info": { "name": "张三", "phone": "138...", "email": "...", "address": "..." },
    "job_intent": { "position": "后端工程师", "expected_salary": "25K" },
    "background": {
      "years_of_experience": "3年",
      "education": "本科",
      "projects": ["项目A", "项目B"],
      "skills": ["Python", "FastAPI", "Redis"]
    },
    "created_at": "2026-03-03T00:00:00Z"
  }
}
```

### `POST /api/match/`

**请求体**：
```json
{
  "resume_id": "uuid-xxx",
  "job_description": "招聘 Python 后端工程师，要求熟悉 FastAPI..."
}
```

**响应**：
```json
{
  "resume_id": "uuid-xxx",
  "overall_score": 82.5,
  "skill_match": {
    "matched": ["Python", "FastAPI"],
    "missing": ["Kubernetes"],
    "match_rate": 0.75
  },
  "experience_relevance": 0.85,
  "ai_analysis": "候选人技术栈匹配度高...",
  "recommendation": "推荐",
  "created_at": "2026-03-03T00:00:00Z"
}
```

### `GET /api/resume/{resume_id}`

获取已缓存的简历解析数据。

---

## 📝 错误处理

所有错误均返回统一格式：
```json
{
  "success": false,
  "message": "错误描述",
  "detail": "详细信息（可选）"
}
```

| 状态码 | 场景 |
|--------|------|
| 400 | 文件格式不支持 / 参数无效 |
| 404 | 简历 ID 不存在或已过期 |
| 413 | 文件超过 10MB 限制 |
| 422 | PDF 无法解析 / 文本提取失败 |
| 500 | 服务器内部错误 / AI 服务不可用 |

---

## 🔗 相关链接

- **线上演示**：https://your-username.github.io/resume-ai/
- **后端 API 文档**：https://your-backend.example.com/docs
- **通义千问 DashScope**：https://dashscope.aliyun.com
- **阿里云函数计算**：https://fc.console.aliyun.com

---

## 📄 License

MIT License © 2026
