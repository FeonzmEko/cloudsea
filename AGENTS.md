# 云海预测 Agent — Codex 指令文档

## 项目简介
一个供个人使用的云海预测后端服务，支持多个固定景区。
用户输入景区名称，Agent 调用 Windy Point Forecast API 获取气象数值，
交由 DeepSeek 综合分析后，输出结构化的云海预测报告（JSON）。

未来计划接入前端，当前阶段只做纯后端。

---

## 技术栈
- Python 3.11+
- LangChain（Agent + Tool 框架）
- DeepSeek（通过 ChatOpenAI 兼容接口接入）
- Windy Point Forecast API v2（气象数值预报）
- python-dotenv（环境变量管理）

---

## 项目结构
```
sea_of_clouds/
├── config/
│   └── locations.json        # 景区名称、经纬度、海拔配置
├── src/
│   ├── tools/
│   │   └── windy_tool.py     # Windy API 封装为 LangChain Tool
│   ├── agent/
│   │   ├── agent.py          # LangChain Agent 主逻辑
│   │   └── prompts.py        # System Prompt
│   └── main.py               # 入口，接受景区名称参数
├── tests/
│   ├── test_windy_tool.py
│   └── test_agent.py
├── .env.example
├── requirements.txt
└── AGENTS.md
```

---

## 常用命令
- 运行预测：`python src/main.py --location 黄山`
- 运行全部测试：`pytest tests/ -v`
- 单独测试 Tool：`pytest tests/test_windy_tool.py -v`
- 依赖安装：`pip install -r requirements.txt`
- 代码检查：`ruff check src/`

---

## 开发顺序（严格按此顺序实现）
1. `config/locations.json` — 景区配置数据
2. `src/tools/windy_tool.py` — Windy API Tool
3. `src/agent/prompts.py` — System Prompt
4. `src/agent/agent.py` — Agent 主逻辑
5. `src/main.py` — 入口
6. `tests/` — 单元测试
7. `requirements.txt` 和 `.env.example`

---

## 关键约定

### 环境变量（从 .env 读取，禁止硬编码）
```
WINDY_API_KEY=你的key
DEEPSEEK_API_KEY=你的key
```

### 景区配置
- 所有景区信息从 `config/locations.json` 读取，不得硬编码在代码里
- 字段：name（中文名）、lat（纬度）、lon（经度）、elevation（海拔，米）
- 用户输入景区名称时，做模糊匹配（支持简称，如"黄山"匹配"黄山风景区"）

### Windy API
- Endpoint：`https://api.windy.com/point-forecast/v2`
- 请求方式：POST，Content-Type: application/json
- 请求 body 示例：
```json
{
  "lat": 30.1302,
  "lon": 118.1689,
  "model": "gfs",
  "parameters": ["temp", "rh", "wind_u-surface", "wind_v-surface", "clouds_low", "precip"],
  "levels": ["surface", "800h", "850h"],
  "key": "YOUR_API_KEY"
}
```
- 需要获取的字段：temp（地面+850hPa，用于判断逆温）、rh（相对湿度）、wind_u/wind_v（风速分量）、clouds_low（低云量）、precip（降水）
- API 有频率限制，调用需加 try/except，失败时返回清晰错误信息
- 返回的时间序列数据，只取未来 24 小时的切片传给 AI

### DeepSeek 接入方式
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    temperature=0.3,  # 预测类任务用低温度
)
```

### Agent 输出格式
Agent 最终必须输出合法 JSON，结构如下：
```json
{
  "location": "黄山",
  "prediction_time": "2026-05-23 06:00",
  "probability": "高",
  "best_window": "明日清晨 05:30-07:00",
  "confidence": 0.82,
  "summary": "明日清晨逆温层明显，湿度92%，风速<2m/s，云海概率极高",
  "key_factors": {
    "humidity": 92,
    "wind_speed": 1.8,
    "temp_inversion": true,
    "low_cloud": 75
  },
  "advice": "建议明日 05:00 前到达观景台"
}
```
- 如果 AI 输出非 JSON，main.py 需捕获并提示错误，不能崩溃
- probability 只允许三个值："高" / "中" / "低"

### 编码规范
- 所有函数必须有 docstring 和类型注解
- 不要使用 print 调试，统一用 logging（level 从环境变量控制）
- 单个文件不超过 200 行，超过则拆分

---

## 景区初始列表（写入 locations.json）
| 名称 | 纬度 | 经度 | 海拔(m) |
|------|------|------|---------|
| 黄山 | 30.1302 | 118.1689 | 1864 |
| 庐山 | 29.5748 | 115.9926 | 1474 |
| 张家界 | 29.1170 | 110.4793 | 1890 |
| 峨眉山 | 29.5197 | 103.3260 | 3099 |
| 泰山 | 36.2544 | 117.1057 | 1545 |
| 武夷山 | 27.7167 | 117.9833 | 2158 |

---

## 不要做的事
- 不要引入数据库，景区配置用 JSON 文件就够
- 不要实现 HTTP 服务（FastAPI 等），当前阶段只做命令行入口
- 不要自己训练模型，预测完全依赖 DeepSeek 分析气象数据
- 不要在代码里写死任何景区名称或坐标
