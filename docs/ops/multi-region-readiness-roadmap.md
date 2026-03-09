# Ops-01 Multi-region Readiness Roadmap

**P2-J**：多區域部署準備（Roadmap）。

## 目標

- 支援多區域（multi-region）部署，以降低延遲、滿足資料在地化與高可用需求。
- 本文件為路線圖與檢查清單，實作依 Phase 排程。

## 檢查清單（依序）

| 項目 | 說明 | 狀態 |
|------|------|------|
| **1. 無狀態應用** | API / Frontend 不依賴單機 session；session 存 Redis 或 JWT。 | ✅ 已採用 JWT + Redis（WS） |
| **2. DB 拓樸** | 單區主庫 + 讀副本，或未來多區主庫（需 conflict resolution）。 | 單區 + read replica 就緒 |
| **3. Redis / 快取** | 若多區，需 Redis 叢集或每區獨立 + 同步策略。 | 單區 Redis 可選 |
| **4. 靜態 / CDN** | 前端靜態資源與媒體走 CDN，邊緣快取。 | 可接 Vercel/Render CDN |
| **5. 健康與路由** | `/health`、`/health/slo` 可被區域負載均衡探測；就近路由。 | 已有 health 端點 |
| **6. 資料在地化** | 若需 GDPR/在地儲存，定義資料存放區與複寫策略。 | 待 Phase 定義 |
| **7. 災難復原** | 跨區備份、RTO/RPO 目標、failover 演練。 | 見 backup-restore-runbook |

## 後續

- Phase 2+ 再細化多區主庫與 conflict 策略。
- 與 Code Yellow 協議、Chaos 演練配合，確保跨區演練納入排程。
