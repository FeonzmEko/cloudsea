# 云海预测 Agent

一个本地自用的命令行云海预测工具。输入景区名称后，程序会调用 Windy Point Forecast API 获取未来 24 小时气象数据，再交给 DeepSeek 分析并输出结构化 JSON 预测报告。

当前项目只做纯后端命令行，不包含 Web 服务、数据库或前端。

## 功能

- 支持固定景区配置，默认包含黄山、庐山、张家界、峨眉山、泰山、武夷山。
- 支持景区简称模糊匹配，例如 `峨眉` 可匹配 `峨眉山`。
- 调用 Windy 获取温度、湿度、风、低云量、降水等数据。
- 使用 DeepSeek 输出云海概率、最佳观景窗口、关键因素和建议。
- 输出合法 JSON，方便后续复制、保存或接入其他脚本。

## 环境要求

- Python 3.11 或更高版本
- Windy API Key
- DeepSeek API Key

## 安装依赖

建议在项目根目录创建虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

如果不使用虚拟环境，也可以直接运行：

```powershell
pip install -r requirements.txt
```

## 配置私人 API Key

复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`：

```env
WINDY_API_KEY=你的_windy_api_key
DEEPSEEK_API_KEY=你的_deepseek_api_key
AMAP_API_KEY=你的_高德_api_key
LOG_LEVEL=INFO
```

`AMAP_API_KEY` 为可选项：配置后即可查询内置列表之外的任意地名（详见下文）。不配置时，只能查询 `config/locations.json` 里的景区。

`.env` 只保存在本机，已经被 `.gitignore` 忽略。不要把真实 API Key 提交到仓库或发给别人。

## 使用方式

查看支持的景区：

```powershell
python src/main.py --list-locations
```

预测指定景区：

```powershell
python src/main.py --location 黄山
```

也可以使用简称：

```powershell
python src/main.py --location 峨眉
```

查询内置列表之外的地名（需配置 `AMAP_API_KEY`）：

```powershell
python src/main.py --location 武功山
```

此时程序会先用高德把地名解析为经纬度（由「经纬度转换 Agent」完成），再进行云海预测。

临时调整日志级别：

```powershell
python src/main.py --location 黄山 --log-level DEBUG
```

## 输出示例

结果以表格形式直接打印在终端，包含预测地点、云海概率、关键天气、总结、观赏建议、安全提醒和穿衣提醒：

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 云海预测                                                                │
├──────────────┬──────────────────────────────────────────────────────────┤
│ 预测地点     │ 黄山                                                     │
│ 云海概率     │ 高 ★★★  值得冲！（把握程度 82%）                         │
│ 预测时间     │ 2026-06-02 06:00                                         │
│ 最佳观赏时段 │ 明日清晨 05:30-07:00                                     │
│ 关键天气     │ 湿度 92%、山顶风速 1.8 m/s、低云覆盖 75%、逆温层 有      │
│ 简要总结     │ ...                                                      │
│ 观赏建议     │ ...                                                      │
│ 安全提醒     │ ...                                                      │
│ 穿衣提醒     │ ...                                                      │
└──────────────┴──────────────────────────────────────────────────────────┘
```

## 添加自己的景区

编辑 `config/locations.json`，按下面格式追加一项：

```json
{ "name": "云台山", "lat": 35.4300, "lon": 113.4300, "elevation": 1308 }
```

字段说明：

- `name`：景区中文名。
- `lat`：纬度。
- `lon`：经度。
- `elevation`：海拔，单位米。

保存后可用 `python src/main.py --list-locations` 检查是否加载成功。

## 常见问题

`未配置 WINDY_API_KEY 环境变量`

检查 `.env` 是否存在，并确认 `WINDY_API_KEY` 已填写。

`未配置 DEEPSEEK_API_KEY 环境变量`

检查 `.env` 是否存在，并确认 `DEEPSEEK_API_KEY` 已填写。

`未找到景区`

先运行 `python src/main.py --list-locations` 查看支持的名称，或把新景区添加到 `config/locations.json`。

`Agent 输出非合法 JSON` 或 `预测结果格式不完整`

说明模型返回内容没有满足结构要求。可以重试一次；如果频繁出现，使用 `--log-level DEBUG` 查看原始输出。

## Web 界面

除了命令行，项目还提供了一个 Web 界面。

### 启动后端

```powershell
python src/server.py
```

后端默认监听 `http://localhost:8000`。

### 生产模式（推荐）

先构建前端：

```powershell
cd frontend
npm install
npm run build
cd ..
```

然后直接启动后端即可，前端页面会自动从 `frontend/dist` 提供：

```powershell
python src/server.py
```

打开浏览器访问 `http://localhost:8000`。

### 开发模式（前后端分离热更新）

终端 1 - 后端：

```powershell
python src/server.py
```

终端 2 - 前端（Vite dev server，自动代理 API 到后端）：

```powershell
cd frontend
npm run dev
```

打开浏览器访问 `http://localhost:5173`。

## 开发检查

运行测试：

```powershell
pytest tests/ -v
```

运行代码检查：

```powershell
ruff check src tests
```
