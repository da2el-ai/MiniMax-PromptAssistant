# 開発ガイド

MiniMax-PromptAssistant をソースから動かす場合の手順です。使うだけであれば
[README.md](../README.md) のセットアップに従ってください。

## 前提

README の[動作環境](../README.md#動作環境)に加えて **Node.js 20 以上**が必要です。
フロントエンドのビルド結果(`frontend/dist`)はリポジトリに含めていないため、
自分でビルドする必要があります。

## ソースから動かす

```bash
git clone https://github.com/da2el-ai/MiniMax-PromptAssistant.git
cd MiniMax-PromptAssistant

# フロントエンドをビルドして dist を作る
cd frontend && npm install && npm run build && cd ..

uv run serve.py
```

`frontend/dist` がないまま起動すると、API だけが動いて画面は表示されません
(起動ログに警告が出ます)。

## フロントエンドを編集する

Vite 開発サーバーを使うと変更が即座に反映されます。ターミナルを 2 つ使います。

```bash
# ターミナル 1: バックエンド(Python ソースの変更で自動再起動する)
uv run uvicorn main:app --app-dir backend --reload --port 8000
```

```bash
# ターミナル 2: Vite 開発サーバー
cd frontend && npm run dev
```

ブラウザで <http://localhost:5173> を開きます。`/api` へのリクエストは Vite が
`http://127.0.0.1:8000` へプロキシします。バックエンドのポートを変えている場合は、
環境変数 `BACKEND_URL` で指定します。

```bash
BACKEND_URL=http://127.0.0.1:9000 npm run dev
```

`--reload` が検知するのは Python ソースの変更だけです。`backend/.env` を変えた場合は
手動で再起動してください。

## そのほかのコマンド

```bash
# フロントエンドの型チェック
cd frontend && npm run typecheck

# API の疎通確認
curl http://127.0.0.1:8000/api/health
```

起動中は <http://127.0.0.1:8000/docs> で、自動生成された API ドキュメントを参照できます。

| エンドポイント | 説明 |
|---|---|
| `POST /api/generate` | 日本語の入力から英語プロンプトを生成する |
| `GET /api/health` | バックエンドと LLM API の疎通を返す |

## リリースを作る

`v1.0.0` 形式のタグを push すると、GitHub Actions が配布用 zip を作って Releases に公開します
([.github/workflows/release.yml](../.github/workflows/release.yml))。

1. `pyproject.toml` の `version` を新しいバージョンに更新してコミットする
2. 同じ番号でタグを打って push する

```bash
git tag v1.0.0
git push origin v1.0.0
```

タグと `pyproject.toml` の `version` が一致しない場合、ワークフローは失敗してリリースを作りません。
更新忘れを防ぐための確認です。

フロントエンドはワークフロー内で `npm ci && npm run build` を実行してビルドします。zip に同梱
されるのは次のとおりです。

| 同梱するもの | 備考 |
|---|---|
| `backend/` | `.env` と `__pycache__` は除外される |
| `frontend/dist/` | ワークフロー内でビルドしたもの |
| `img/` | README の画像 |
| `serve.py` / `pyproject.toml` / `uv.lock` | 起動と依存の定義 |
| `README.md` / `docs/` / `LICENSE` | ドキュメント |

リリースノートは、前回のタグからのコミットを元に GitHub が自動生成します。

## ディレクトリ構成

```text
MiniMax-PromptAssistant/
  pyproject.toml         # Python の依存定義
  serve.py               # 起動スクリプト(uv run serve.py)
  docs/                  # 開発ガイド・LLM API のセットアップ手順
  backend/
    main.py              # FastAPI アプリ本体・フロントエンドの配信
    config.py            # 環境変数による設定
    models.py            # リクエスト/レスポンスのモデル
    llm_client.py        # LLM API クライアント(フォールバック処理を含む)
    prompt_builder.py    # システムプロンプト構築・定型部分の確定
    validator.py         # フォーマット検証
    .env.example
    templates/           # 方式ごとのシステムプロンプト
      _common.md  t2va.md  i2va.md  fl2va.md  l2va.md  rf2va.md
  frontend/
    dist/                # ビルド結果。バックエンドがここを配信する
    src/
      App.vue
      main.ts
      style.css
      api/client.ts      # バックエンドとの通信
      types/api.ts       # API の型定義
      utils/             # フォーム初期値・localStorage 保存
      components/        # 入力フォーム・結果表示の各コンポーネント
```
