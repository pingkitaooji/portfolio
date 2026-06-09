# 健康風險評估報告系統

這是一個以 Django 建立的健康風險評估報告系統。系統模擬機台上傳 SNP 檔案，後端接收後產生伺服器統一流水號，解析 SNP 內容，執行 PC / NC check，進行模擬風險計算，並可由醫療端建立病人資料與 PDF 報告。

> 注意：目前風險計算與 PDF 報告皆為 DEMO / 作品集展示用途，不可作為臨床診斷或醫療決策依據。

## 目前功能

- 醫療端登入
- SNP 檔案上傳
- 上傳後由系統自動給予伺服器統一流水號
- 隨機產生 DEMO SNP 資料
- SNP 原始資料預覽
- 解析 SNP 位點、染色體、位置與 genotype
- PC check / NC check
- 模擬風險計算並保存至資料庫
- 在 SNP 資料頁建立病人資料並產生報告
- PDF 報告保存與下載
- 報告列表點選預覽
- SNP 檔案與報告刪除

## 系統頁面

- `/`：總覽。顯示已上傳 SNP、待處理 SNP、已建立報告、PC / NC 通過數與風險計算狀態。
- `/snp/`：SNP 資料。上傳或產生 DEMO SNP，查看 SNP 內容，建立病人資料並產生報告。
- `/reports/`：報告列表。查看所有報告、預覽內容、下載 PDF、刪除報告。
- `/api/snp-upload/`：機台上傳 API。

## CqCalling：qPCR Cq Calling Engine

`sites/CqCalling/` 是第二個 Django 作品站，展示可移植到儀器端的 qPCR 訊號分析流程：

- 輸入 40-cycle 螢光訊號，範圍 0-100
- 產生多種 demo 訊號情境
- 執行 4PL sigmoid fitting
- 以二次微分最大值取得 Cq value
- 輸出 IR、R²、QC 與 instrument-ready JSON

目前 CqCalling 已由 Django + Gunicorn 提供頁面，核心演算法由 Python endpoint `/api/analyze/` 執行；前端只負責輸入、圖表與結果渲染。

## PrimerQC：Primer Pair Quality Prediction

`sites/PrimerQC/` 是第三個 Django 作品站，展示引子對品質與可用性預測流程：

- 輸入 forward / reverse primer 與 amplicon length
- 產生隨機 demo primer pair
- 抽取 Primer3-style 熱力學與結構特徵：GC%、Tm、3' GC、homopolymer、self complementarity、hairpin proxy、hetero dimer proxy
- 使用前端 demo 模型輸出 PASS / REVIEW / FAIL 與可用機率
- 回填真實實驗驗證欄位，並以瀏覽器 localStorage 保存預測紀錄
- 使用 `modlebuild/` 中的真實熱力學資料比較多個機器學習模型
- 頁面下方呈現模型測試結果與最佳模型摘要

目前 PrimerQC 已由 Django + Gunicorn 提供頁面，序列清理、Primer3-style proxy feature、品質預測由 Python endpoint `/api/predict/` 執行。下一步可讓後端呼叫 `primer3-py` 抽取正式特徵，再載入 `best_primer_model.joblib` 做即時推論並寫入資料庫。

> 機密資料注意：PrimerQC 原始訓練 CSV 已移至 `private_data/PrimerQC/`，並已加入 `.gitignore` 與 Docker build 排除。公開展示只保留模型評估摘要與去識別來源檔名。

## 技術架構

- Backend：Django 6
- Database：SQLite（本機預設）或 PostgreSQL（Docker）
- Static files：WhiteNoise
- App server：Gunicorn
- Container：Docker / Docker Compose
- File storage：
  - 本機：`media/`
  - Docker demo：Docker named volume `media_data`
  - 正式部署建議：S3 / Spaces / Blob Storage

## 資料模型

- `SNPRecord`
  - 機台流水號
  - 伺服器統一流水號
  - SNP 原始檔
  - SNP 筆數
  - PC check / NC check
  - 狀態

- `RiskAssessment`
  - 對應一筆 SNPRecord
  - 總風險分數
  - 各類風險計算結果

- `Patient`
  - 病人名稱
  - 性別
  - 醫院端流水號

- `Report`
  - 報告編號
  - 病人
  - SNP 資料
  - PDF 檔案
  - 風險摘要

## 模擬風險計算

風險計算模組位於：

```text
sites/health-risk/reports/risk_calculator.py
```

目前包含三個展示用風險類別：

- 心血管風險
- 第二型糖尿病風險
- 藥物代謝注意事項

每一類風險會依指定 SNP 位點與 genotype 權重計分，並將結果寫入 `RiskAssessment`。報告產生時會讀取資料庫中的風險結果，確保報告預覽與 PDF 使用同一份計算資料。

## 本機執行

健康風險評估報告系統現在是獨立子專案，先進入它自己的資料夾：

```bash
cd sites/health-risk
```

安裝套件：

```bash
python -m pip install -r requirements.txt
```

建立資料庫：

```bash
python manage.py migrate
```

建立管理者帳號：

```bash
python manage.py createsuperuser
```

啟動開發伺服器：

```bash
python manage.py runserver 127.0.0.1:8000
```

開啟：

```text
http://127.0.0.1:8000/login/
```

目前 demo 帳號：

```text
clinic_admin / demo123
```

## Docker 執行

先複製環境設定：

```bash
copy .env.example .env
```

如果是在 macOS / Linux：

```bash
cp .env.example .env
```

啟動：

```bash
docker compose up -d --build
```

啟動後可直接開啟健康風險評估報告系統本機入口：

```text
http://127.0.0.1:8000/login/
```

Docker Compose 會啟動：

- `reverse-proxy`：Nginx 子網域入口
- `portfolio`：履歷作品集首頁
- `web`：Django + Gunicorn
- `db`：PostgreSQL 16
- `cqcalling`：Django + Gunicorn，qPCR Cq calling demo
- `primerqc`：Django + Gunicorn，Primer Pair Quality Prediction
- `postgres_data`：PostgreSQL 資料 volume
- `media_data`：SNP 檔案與 PDF 報告 volume

容器啟動時會自動：

- 等待 PostgreSQL
- 執行 migration
- 收集 static files
- 建立或更新 demo superuser

## 作品集平台整合

目前專案已整理成「個人作品網站 + 多個作品子站」的 Docker 架構：

```text
www.yourdomain.com          履歷作品集首頁
health.yourdomain.com       健康風險評估報告系統
cqcalling.yourdomain.com    CqCalling
primerqc.yourdomain.com     PrimerQC
```

建議將三個作品拆成獨立 Git repository 管理，入口頁目前預留以下 GitHub 連結位置：

```text
https://github.com/pingkitaooji/portfolio
```

目前本機環境未偵測到 `git` 指令；安裝 Git 或提供正式 repo URL 後，可再將佔位連結替換成實際連結並初始化各子專案版本紀錄。

對應的專案資料夾：

```text
.
├─ sites/
│  ├─ portfolio/            www.yourdomain.com 的靜態作品集首頁
│  ├─ health-risk/          health.yourdomain.com 的 Django 健康風險評估報告系統
│  │  ├─ reports/           Django app
│  │  ├─ healthrisk/        Django project settings
│  │  ├─ templates/         健康系統 templates
│  │  ├─ static/            健康系統 static files
│  │  ├─ docker/            Django 容器 entrypoint
│  │  ├─ Dockerfile
│  │  ├─ manage.py
│  │  └─ requirements.txt
│  ├─ CqCalling/            Django qPCR Cq calling demo
│  │  ├─ cqcalling_site/    Django project settings
│  │  ├─ templates/         qPCR 頁面 templates
│  │  ├─ static/            qPCR styles、scripts、hero image
│  │  ├─ docker/            Django 容器 entrypoint
│  │  ├─ Dockerfile
│  │  ├─ manage.py
│  │  └─ requirements.txt
│  ├─ PrimerQC/             Django Primer Pair Quality Prediction，引子對品質預測展示
│  │  ├─ primerqc_site/     Django project settings
│  │  ├─ templates/         Primer 頁面 templates
│  │  ├─ static/            Primer styles、scripts、hero image、模型結果展示資料
│  │  ├─ modlebuild/        訓練資料、模型評估腳本與最佳模型檔
│  │  ├─ docker/            Django 容器 entrypoint
│  │  ├─ Dockerfile
│  │  ├─ manage.py
│  │  └─ requirements.txt
│  └─ _shared/assets/       共用原始圖片備份
├─ infrastructure/
│  └─ nginx/default.conf    子網域 reverse proxy 設定
├─ archive/
│  └─ legacy-static-demo/   舊版單頁原型保留區
├─ docker-compose.yml       多站整合啟動設定
├─ .env.example
└─ README.md
```

`infrastructure/nginx/default.conf` 會依照瀏覽器送出的 Host 分流：

- `www.yourdomain.com` 或 `yourdomain.com` -> `portfolio`
- `health.yourdomain.com` -> `web` Django 健康風險評估報告系統
- `cqcalling.yourdomain.com` -> `cqcalling`
- `primerqc.yourdomain.com` -> `primerqc`

正式部署時 DNS 請將以下紀錄指向同一台主機 IP：

```text
A     yourdomain.com          <server-ip>
CNAME www                     yourdomain.com
CNAME health                  yourdomain.com
CNAME cqcalling               yourdomain.com
CNAME primerqc                yourdomain.com
```

本機測試子網域時，可以先在 hosts file 加上：

```text
127.0.0.1 yourdomain.com
127.0.0.1 www.yourdomain.com
127.0.0.1 health.yourdomain.com
127.0.0.1 cqcalling.yourdomain.com
127.0.0.1 primerqc.yourdomain.com
```

Windows hosts file 位置：

```text
C:\Windows\System32\drivers\etc\hosts
```

加完後啟動：

```bash
docker compose up -d --build
```

即可測試：

```text
http://www.yourdomain.com
http://health.yourdomain.com
http://cqcalling.yourdomain.com
http://primerqc.yourdomain.com
```

如果暫時不改 hosts file，也可以繼續用：

```text
http://127.0.0.1:8000/login/
```

直接測試健康風險評估報告系統。

本機也提供各作品的直接測試 port：

```text
http://127.0.0.1/        作品集首頁
http://127.0.0.1:8000/   健康風險評估報告系統
http://127.0.0.1:8002/   CqCalling
http://127.0.0.1:8003/   PrimerQC
```

開發階段 CqCalling / PrimerQC 仍會載入各自的 `dev-links.js`。當網址是 `127.0.0.1` 或 `localhost` 時，頁面上的正式子網域連結會自動改成本機 port；正式部署到 `yourdomain.com` 時則維持正式子網域連結。

## 機台上傳 API

Endpoint：

```text
POST /api/snp-upload/
```

欄位：

- `machine_serial`
- `data_file`

範例：

```bash
curl -X POST ^
  -F "machine_serial=MC-DEMO-0001" ^
  -F "data_file=@sample_snp.csv" ^
  http://127.0.0.1:8000/api/snp-upload/
```

回傳會包含：

- `server_serial`
- `snp_count`
- `pc_check_passed`
- `nc_check_passed`
- `overall_risk_score`
- `risk_results`

## 正式部署建議

目前已經可以用單一 Docker Compose 在同一台主機上跑多個子站。正式上線時建議再補：

- 將 `.env` 中的 `DJANGO_DEBUG` 改為 `0`
- 將 `DJANGO_SECRET_KEY` 換成正式 secret
- 將 `DJANGO_ALLOWED_HOSTS` 設為正式網域，例如 `health.yourdomain.com`
- 使用 HTTPS，可以接 Cloudflare、Caddy，或在 Nginx 加 Certbot
- PostgreSQL 建議使用 managed database 或建立固定備份策略
- SNP 原始檔與 PDF 長期建議改用 S3 / Spaces / Blob Storage
- 醫療類資料若進一步真實化，需要補權限控管、操作紀錄、資料加密與隱私法規評估

## 驗證

目前已執行：

```bash
cd sites/health-risk
python manage.py check
python manage.py test reports --verbosity 2
python manage.py collectstatic --noinput
cd ../..
docker compose config
docker compose up -d --build
docker compose exec -T web python manage.py test reports --verbosity 1
```
