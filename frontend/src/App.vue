<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchLocations, predict } from './api'
import type { Location, PredictionResult } from './api'
import {
  Search,
  Location as LocationIcon,
  Sunny,
  Timer,
  WindPower,
  Umbrella,
} from '@element-plus/icons-vue'

const query = ref('')
const locations = ref<Location[]>([])
const loading = ref(false)
const result = ref<PredictionResult | null>(null)
const error = ref('')

const suggestions = computed(() => {
  const q = query.value.trim()
  const list = q
    ? locations.value.filter(l => l.name.includes(q))
    : locations.value
  return list.map(l => ({ value: l.name, elevation: l.elevation }))
})

onMounted(async () => {
  try {
    locations.value = await fetchLocations()
  } catch { /* ignore */ }
})

function handleSelect(item: Record<string, unknown>) {
  query.value = item.value as string
  doPredict()
}

async function doPredict() {
  const q = query.value.trim()
  if (!q) return
  loading.value = true
  error.value = ''
  result.value = null

  try {
    const res = await predict(q)
    if (res.error) {
      error.value = res.message || res.error
    } else {
      result.value = res
      try { locations.value = await fetchLocations() } catch { /* ignore */ }
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '请求失败，请检查后端服务是否启动'
  } finally {
    loading.value = false
  }
}

function probColor(p: string) {
  if (p === '高') return '#67c23a'
  if (p === '中') return '#e6a23c'
  return '#f56c6c'
}
function probStars(p: string) {
  if (p === '高') return '★★★'
  if (p === '中') return '★★☆'
  return '★☆☆'
}
function probLabel(p: string) {
  if (p === '高') return '值得冲！'
  if (p === '中') return '碰碰运气'
  return '建议改天'
}
</script>

<template>
  <div class="page">
    <!-- Hero -->
    <header class="hero">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <h1 class="title">
          <span class="icon-cloud">☁</span> 云海预测
        </h1>
        <p class="desc">输入任意山峰或景区名，AI 实时分析云海出现概率</p>

        <div class="search-box">
          <el-autocomplete
            v-model="query"
            :fetch-suggestions="(_q: string, cb: (list: {value: string; elevation: number}[]) => void) => cb(suggestions)"
            placeholder="输入景区名称，如：黄山、武功山、牛背山..."
            size="large"
            clearable
            :prefix-icon="Search"
            @select="handleSelect"
            @keyup.enter="doPredict"
            style="width: 100%"
          >
            <template #default="{ item }">
              <div class="suggestion-item">
                <span>{{ item.value }}</span>
                <el-tag size="small" type="info" round>{{ item.elevation }}m</el-tag>
              </div>
            </template>
          </el-autocomplete>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            :disabled="!query.trim()"
            @click="doPredict"
          >
            {{ loading ? '分析中' : '开始预测' }}
          </el-button>
        </div>
      </div>
    </header>

    <main class="main">
      <!-- Loading -->
      <div v-if="loading" class="loading-area">
        <div class="loading-card">
          <div class="wave-loader">
            <span></span><span></span><span></span><span></span><span></span>
          </div>
          <p class="loading-text">正在获取气象数据并分析云海条件</p>
          <p class="loading-sub">大约需要 30-60 秒，请耐心等待...</p>
        </div>
      </div>

      <!-- Error -->
      <el-alert
        v-if="error"
        :title="error"
        type="error"
        show-icon
        closable
        style="margin-bottom: 24px"
        @close="error = ''"
      />

      <!-- Result -->
      <template v-if="result">
        <!-- Probability Banner -->
        <div class="prob-card" :style="{ borderColor: probColor(result.probability) }">
          <div class="prob-left">
            <span class="prob-stars" :style="{ color: probColor(result.probability) }">
              {{ probStars(result.probability) }}
            </span>
            <div class="prob-info">
              <span class="prob-text" :style="{ color: probColor(result.probability) }">
                云海概率：{{ result.probability }}
              </span>
              <span class="prob-label">{{ probLabel(result.probability) }}</span>
            </div>
          </div>
          <el-tag
            :color="probColor(result.probability) + '22'"
            :style="{ borderColor: probColor(result.probability), color: probColor(result.probability) }"
            size="large"
            round
          >
            置信度 {{ Math.round(result.confidence * 100) }}%
          </el-tag>
        </div>

        <!-- Info Grid -->
        <div class="grid-2">
          <el-card shadow="never" class="info-card">
            <template #header>
              <div class="card-header">
                <el-icon><LocationIcon /></el-icon>
                <span>基本信息</span>
              </div>
            </template>
            <div class="info-list">
              <div class="info-item">
                <span class="info-label">预测地点</span>
                <span class="info-value">{{ result.location }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">预测时间</span>
                <span class="info-value">{{ result.prediction_time }}</span>
              </div>
              <div class="info-item" style="border: none">
                <span class="info-label">最佳时段</span>
                <span class="info-value">{{ result.best_window }}</span>
              </div>
            </div>
          </el-card>

          <el-card shadow="never" class="info-card">
            <template #header>
              <div class="card-header">
                <el-icon><Sunny /></el-icon>
                <span>关键天气</span>
              </div>
            </template>
            <div class="weather-grid">
              <div class="weather-cell">
                <el-icon class="weather-icon" :size="20"><Umbrella /></el-icon>
                <span class="weather-val">{{ result.key_factors.humidity }}%</span>
                <span class="weather-label">湿度</span>
              </div>
              <div class="weather-cell">
                <el-icon class="weather-icon" :size="20"><WindPower /></el-icon>
                <span class="weather-val">{{ result.key_factors.wind_speed }} m/s</span>
                <span class="weather-label">风速</span>
              </div>
              <div class="weather-cell">
                <el-icon class="weather-icon" :size="20"><Sunny /></el-icon>
                <span class="weather-val">{{ result.key_factors.low_cloud }}%</span>
                <span class="weather-label">低云</span>
              </div>
              <div class="weather-cell">
                <el-icon class="weather-icon" :size="20"><Timer /></el-icon>
                <el-tag :type="result.key_factors.temp_inversion ? 'success' : 'info'" size="small" round>
                  {{ result.key_factors.temp_inversion ? '有逆温' : '无逆温' }}
                </el-tag>
                <span class="weather-label">逆温层</span>
              </div>
            </div>
          </el-card>
        </div>

        <!-- Text Cards -->
        <el-card shadow="never" class="text-card">
          <template #header>
            <div class="card-header"><span>📝</span><span>分析总结</span></div>
          </template>
          <p>{{ result.summary }}</p>
        </el-card>

        <el-card shadow="never" class="text-card">
          <template #header>
            <div class="card-header"><span>🎯</span><span>观赏建议</span></div>
          </template>
          <p>{{ result.advice }}</p>
        </el-card>

        <div class="grid-2" v-if="result.safety_tips || result.clothing_tips">
          <el-card v-if="result.safety_tips" shadow="never" class="text-card">
            <template #header>
              <div class="card-header"><span>⚠️</span><span>安全提醒</span></div>
            </template>
            <p>{{ result.safety_tips }}</p>
          </el-card>
          <el-card v-if="result.clothing_tips" shadow="never" class="text-card">
            <template #header>
              <div class="card-header"><span>🧥</span><span>穿衣提醒</span></div>
            </template>
            <p>{{ result.clothing_tips }}</p>
          </el-card>
        </div>
      </template>

      <!-- Tags -->
      <section v-if="locations.length" class="tags-section">
        <p class="tags-title">快速查询</p>
        <div class="tags-list">
          <el-tag
            v-for="loc in locations"
            :key="loc.name"
            class="loc-tag"
            effect="plain"
            round
            @click="query = loc.name; doPredict()"
          >
            {{ loc.name }}
          </el-tag>
        </div>
      </section>
    </main>
  </div>
</template>

<style>
html.dark {
  color-scheme: dark;
}

*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --page-bg: #0c1219;
  --card-bg: #141c27;
  --card-border: #1e2d3d;
  --text: #e4ecf5;
  --text-dim: #7e8fa3;
  --accent: #409eff;
  --max-w: 780px;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
    'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  background: var(--page-bg);
  color: var(--text);
  min-height: 100vh;
}

/* ---- Element Plus 暗色覆写 ---- */
.el-card {
  --el-card-bg-color: var(--card-bg) !important;
  --el-card-border-color: var(--card-border) !important;
  border-radius: 12px !important;
  color: var(--text) !important;
}
.el-card__header {
  border-bottom-color: var(--card-border) !important;
  padding: 14px 20px !important;
}
.el-autocomplete {
  --el-input-bg-color: #1a2535;
  --el-input-border-color: var(--card-border);
  --el-input-text-color: var(--text);
  --el-input-placeholder-color: var(--text-dim);
  flex: 1;
}
.el-input__wrapper {
  background-color: #1a2535 !important;
  box-shadow: 0 0 0 1px var(--card-border) inset !important;
}
.el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px var(--accent) inset !important;
}
.el-alert {
  border-radius: 12px !important;
}

.page {
  min-height: 100vh;
}

/* Hero */
.hero {
  position: relative;
  overflow: hidden;
  padding: 60px 20px 48px;
}
.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 120% 80% at 50% 20%, rgba(64, 158, 255, 0.08) 0%, transparent 60%),
    linear-gradient(180deg, #0e1a28 0%, var(--page-bg) 100%);
  z-index: 0;
}
.hero-content {
  position: relative;
  z-index: 1;
  max-width: var(--max-w);
  margin: 0 auto;
}
.title {
  text-align: center;
  font-size: 2.5rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  margin-bottom: 10px;
}
.icon-cloud {
  display: inline-block;
  animation: float 3s ease-in-out infinite;
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
.desc {
  text-align: center;
  color: var(--text-dim);
  margin-bottom: 32px;
  font-size: 1rem;
}
.search-box {
  display: flex;
  gap: 12px;
  max-width: 600px;
  margin: 0 auto;
}
.suggestion-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

/* Main */
.main {
  max-width: var(--max-w);
  margin: 0 auto;
  padding: 0 20px 60px;
}

/* Loading */
.loading-area {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}
.loading-card {
  text-align: center;
}
.wave-loader {
  display: flex;
  justify-content: center;
  gap: 4px;
  margin-bottom: 20px;
}
.wave-loader span {
  display: block;
  width: 6px;
  height: 24px;
  border-radius: 3px;
  background: var(--accent);
  animation: wave 1.2s ease-in-out infinite;
}
.wave-loader span:nth-child(2) { animation-delay: 0.1s; }
.wave-loader span:nth-child(3) { animation-delay: 0.2s; }
.wave-loader span:nth-child(4) { animation-delay: 0.3s; }
.wave-loader span:nth-child(5) { animation-delay: 0.4s; }
@keyframes wave {
  0%, 40%, 100% { transform: scaleY(0.4); opacity: 0.4; }
  20% { transform: scaleY(1); opacity: 1; }
}
.loading-text {
  color: var(--text);
  font-size: 1rem;
  margin-bottom: 6px;
}
.loading-sub {
  color: var(--text-dim);
  font-size: 0.85rem;
}

/* Probability Banner */
.prob-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--card-bg);
  border: 1px solid;
  border-radius: 14px;
  padding: 20px 24px;
  margin-bottom: 16px;
}
.prob-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.prob-stars {
  font-size: 2rem;
  letter-spacing: 4px;
}
.prob-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.prob-text {
  font-size: 1.2rem;
  font-weight: 700;
}
.prob-label {
  color: var(--text-dim);
  font-size: 0.9rem;
}

/* Grid */
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.info-card,
.text-card {
  margin-bottom: 16px;
}
.grid-2 .info-card,
.grid-2 .text-card {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text);
}

.info-list .info-item {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 10px 0;
  border-bottom: 1px solid var(--card-border);
  gap: 12px;
}
.info-list .info-item .info-value {
  text-align: right;
  word-break: break-all;
}
.info-label {
  color: var(--text-dim);
  font-size: 0.9rem;
}
.info-value {
  font-weight: 500;
}

/* Weather Grid */
.weather-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.weather-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 0;
}
.weather-icon {
  color: var(--accent);
}
.weather-val {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text);
}
.weather-label {
  font-size: 0.78rem;
  color: var(--text-dim);
}

.text-card p {
  line-height: 1.8;
  color: var(--text);
  font-size: 0.95rem;
}

/* Tags */
.tags-section {
  margin-top: 40px;
  text-align: center;
}
.tags-title {
  color: var(--text-dim);
  font-size: 0.85rem;
  margin-bottom: 14px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}
.loc-tag {
  cursor: pointer;
  transition: all 0.2s;
  --el-tag-bg-color: var(--card-bg) !important;
  --el-tag-border-color: var(--card-border) !important;
  --el-tag-text-color: var(--text) !important;
}
.loc-tag:hover {
  --el-tag-border-color: var(--accent) !important;
  --el-tag-text-color: var(--accent) !important;
  transform: translateY(-2px);
}

/* Responsive */
@media (max-width: 640px) {
  .hero { padding: 40px 16px 32px; }
  .title { font-size: 1.8rem; }
  .search-box { flex-direction: column; }
  .grid-2 { grid-template-columns: 1fr; }
  .prob-card { flex-direction: column; gap: 12px; align-items: flex-start; }
  .prob-stars { font-size: 1.5rem; }
}
</style>
