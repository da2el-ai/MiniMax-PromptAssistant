# MiniMax-PromptAssistant

動画生成 AI「MiniMax-H3」用の英語プロンプトを、**日本語の入力から生成する Web アプリケーション**です。

公式プロンプトガイドの要点とユーザー入力をローカル LLM(llama.cpp)へ送り、ガイド準拠の構造化プロンプトを組み立てます。

<img src="./img/screenshot.png" alt="">

## 特徴

- 必要な項目を日本語で記述すると、MiniMax-H3 用に構造化されたプロンプトを出力
- 全 5 方式に対応（T2VA / I2VA / FL2VA / L2VA / RF2VA）
- ページを再読み込みしてもパラメーターは復元される

### 対応方式

| 方式 | 説明 | 参照するもの |
|---|---|---|
| T2VA | テキストのみから生成 | なし |
| I2VA | 最初のフレームを指定 | Picture 1(最初) |
| FL2VA | 最初と最後のフレームを指定 | Picture 1(最初)+ Picture 2(最後) |
| L2VA | 最後のフレームを指定 | Picture 1(最後) |
| RF2VA | フルリファレンスモード | 参照アセット(画像/動画/音声)を複数 |

※画像からのプロンプト生成は行いません。画像の内容はユーザー自身が文章で入力する仕組みです。

## 動作環境

| 必要なもの | 条件 | 備考 |
|---|---|---|
| Python | 3.10 以上 | バックエンド |
| uv | 最新版 | 仮想環境と依存を自動で用意する。pip でも代用可 |
| llama.cpp | 最新版 | `llama-server` を使用 |
| GPU | VRAM 12GB 以上を推奨 | CPU のみでも動くが非常に遅い |

## セットアップ

### 1. アプリを入手する

[Releases](https://github.com/da2el-ai/MiniMax-PromptAssistant/releases) から zip をダウンロードして
展開します。

ソースから動かす場合は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

### 2. llama-server を起動する

llama.cpp のインストール方法の説明は省略します。<br>
お使いの環境に合わせてセットアップしてください。

モデルは筆者は [gemma-4-12B-it-qat-q4_0-uncensored-heretic-Q4_0](https://huggingface.co/llmfan46/gemma-4-12B-it-qat-q4_0-uncensored-heretic-GGUF) を使用しています。

```bash
llama-server -m <モデルフォルダ>/<モデル名>.gguf -c 16384 -ngl 99 --jinja --host 127.0.0.1 --port 8080
```

Windows(PowerShell)の場合:

```powershell
llama-server.exe -m <モデルフォルダ>\<モデル名>.gguf -c 16384 -ngl 99 --jinja --host 127.0.0.1 --port 8080
```

起動オプションの意味は [llama-server の起動オプション](#llama-server-の起動オプション) を参照してください。**`--jinja` は本アプリの動作に必要です。**

ブラウザで <http://127.0.0.1:8080> を開き、llama.cpp の Web UI が表示されれば起動できています。

### 3. MiniMax-PromptAssistant を起動する

展開したフォルダで次を実行します。

#### ◆ uv を使う場合

```bash
uv run serve.py
```

初回は仮想環境の作成と依存の導入が自動で走るため、少し時間がかかります。

#### ◆ pip を使う場合

```bash
python3 -m venv .venv    # 初回のみ
.venv/bin/pip install .  # 初回のみ
.venv/bin/python serve.py
```

```powershell
# Windows(PowerShell)
python -m venv .venv          # 初回のみ
.venv\Scripts\pip install .   # 初回のみ
.venv\Scripts\python serve.py
```

#### ◆ 実行後

サーバーが起動し、ブラウザで <http://127.0.0.1:8000> が開きます。

起動ログに `llama-server 接続先: http://127.0.0.1:8080/v1` と出れば、接続先の設定も正しく読めています。

> `serve.py` は画面(フロントエンド)と API(バックエンド)を同じポートで動かします。以降の説明で「バックエンドを再起動する」とあるのは、この `serve.py` を `Ctrl + C` で止めて実行し直すことを指します。

#### ◆ `serve.py` 起動オプション

| オプション | 既定値 | 説明 |
|---|---|---|
| `--port` | `8000` | 待ち受けポート |
| `--host` | `127.0.0.1` | 待ち受けアドレス。LAN の他端末から使うなら `0.0.0.0` |
| `--no-browser` | — | 起動時にブラウザを開かない |

> `--host 0.0.0.0` を指定すると、同じネットワーク上の誰でも画面と API を開けるようになります。
> 信頼できるネットワークでのみ使用してください。

llama-server の接続先を変えたい場合は、`backend/.env.example` を `backend/.env` にコピーして
編集します(設定項目は [環境変数](#環境変数) を参照)。

既定のまま(llama-server が `127.0.0.1:8080`)で動く場合、`.env` の作成は不要です。

## 使い方

1. 左カラム上部の**方式**(T2VA / I2VA / FL2VA / L2VA / RF2VA)を選ぶ
2. **尺**(秒)と**スタイル**を指定する。スタイルは「自動」にすると内容から推定される
3. **ショット**に、場面の説明・カメラワーク・セリフを日本語で書く。「ショットを追加」で複数
   ショットに分割できる
4. 必要に応じて画面内テキスト・環境音・BGM を指定する
5. 「プロンプトを生成」を押すと、英語プロンプトが右カラムに表示される

補足:

- `Ctrl + Enter` / `⌘ + Enter` で生成できます
- 入力内容は自動で localStorage に保存され、次回アクセス時に復元されます。初期状態に戻したい
  ときはヘッダーの「入力をクリア」を押してください
- ヘッダーに llama-server との疎通状態を表示し、5 秒間隔で更新します
- カット時刻は、未入力のショットについて前後の確定値の間に均等配分されます
- 生成結果の下の「デバッグ: 送信パラメーター」を開くと、実際に送信した JSON を確認できます

## 動作の仕組み

書式が厳密に決まっている部分は LLM に任せず、Python 側で確定させています。

- **コードが決める**: 先頭の指示行、フィールド名、各ショットのカット時刻(`MM:SS.mmm`)、
  話者 ID(`S1`, `S2` …)、参照アセットのラベル(`<Picture N>` など)、環境音 / BGM の `N/A`
- **LLM が書く**: 英語の描写本文(`integrated_multimodal_description`)、`overall_soundscape`、
  `non_diegetic_music`、RF2VA の各セクション

生成結果は [backend/validator.py](backend/validator.py) で検証し、違反があればその内容を LLM に
伝えて再生成します(既定で最大 3 回)。主な検証項目は次のとおりです。

- `[Shot 1]` から `[Shot N]` が過不足なく順番に現れ、`[Shot 1]` にはタイムスタンプが付かない
- `[Shot 2]` 以降のカット時刻が、コード側で確定した値と完全一致する
- `<d>` タグが開閉対応し、内側の先頭に言語タグがある
- **ユーザーが入力したセリフが翻訳・改変されず、逐語で `<d>` 内に含まれる**
- 画面内テキストが原文のまま二重引用符で含まれる

再生成しても残った違反は、レスポンスの `warnings` に日本語で載せて画面に表示します。

## 環境変数

`backend/.env`(または実際の環境変数)で設定します。設定例は
[backend/.env.example](backend/.env.example) にあります。

| 変数 | 既定値 | 説明 |
|---|---|---|
| `LLM_BASE_URL` | `http://127.0.0.1:8080/v1` | llama-server の OpenAI 互換 API のベース URL |
| `LLM_MODEL` | `local-model` | モデル名。llama-server は単一モデルのため任意の識別子でよい |
| `LLM_API_KEY` | (空) | llama-server を `--api-key` 付きで起動した場合に設定する |
| `LLM_TIMEOUT_SEC` | `300` | 1 回のリクエストのタイムアウト(秒) |
| `LLM_TEMPERATURE` | `0.7` | 生成の多様性。0.6〜0.8 が目安 |
| `LLM_TOP_P` | `0.9` | nucleus sampling の閾値 |
| `LLM_MAX_TOKENS` | `4096` | 生成の最大トークン数。出力が途中で切れる場合は増やす |
| `LLM_RESPONSE_FORMAT` | `json_schema` | 構造化出力の指定方法(`json_schema` / `json_object` / `none`) |
| `LLM_DISABLE_THINKING` | `true` | 思考モード(`reasoning_content`)を無効化する |
| `GENERATE_MAX_RETRIES` | `3` | 検証 NG 時の再生成回数の上限 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | CORS 許可オリジン(カンマ区切り)。**通常の起動では使われない**(開発用) |

> `.env` は**起動時に一度だけ**読み込みます。`.env` を変えたらバックエンドを再起動してください。

### 外部の OpenAI 互換 API を使う場合

バックエンドは OpenAI 互換の `/chat/completions` を呼ぶだけなので、`LLM_BASE_URL` と
`LLM_API_KEY` を書き換えれば外部サービスでも技術的には動きます(**動作保証の対象外**。
入力内容がそのサービスへ送信される点にも注意してください)。その場合は次の 2 つも変更します。

- `LLM_MODEL` — 既定の `local-model` ではなく、実際のモデル ID を指定する
- `LLM_DISABLE_THINKING=false` — 思考モードの無効化に使う `chat_template_kwargs` は llama.cpp
  独自の拡張のため、外部サービスでは未知パラメーターとして拒否されます(自動フォールバックで
  最終的には通りますが、初回に無駄な失敗リクエストが発生します)

## llama-server の起動オプション

### 必須・重要なオプション

| オプション | 例 | 説明 |
|---|---|---|
| `-m`, `--model` | `-m ~/models/model.gguf` | 読み込む GGUF ファイルのパス |
| `-c`, `--ctx-size` | `-c 16384` | コンテキスト長(トークン数)。**16384 以上を推奨** |
| `-ngl`, `--n-gpu-layers` | `-ngl 99` | GPU にオフロードする層数。`99` で全層を GPU に載せる |
| `--jinja` | `--jinja` | **本アプリでは必須。** 下記参照 |
| `--host` | `--host 127.0.0.1` | 待ち受けアドレス。既定は `127.0.0.1` |
| `--port` | `--port 8080` | 待ち受けポート。既定は `8080` |

#### `--jinja` が必要な理由

本アプリはプロンプトの自由記述部分を **JSON で受け取る** ため、リクエストに次の 2 つを付けます。

- `response_format: {"type": "json_schema", ...}` — 出力を JSON スキーマに従わせる
- `chat_template_kwargs: {"enable_thinking": false}` — モデルの思考モードを止める

これらはモデル同梱の Jinja チャットテンプレートを使って処理されるため、`--jinja` を付けずに
起動すると無視されたりエラーになったりします。付け忘れると、生成が失敗するか品質が大きく落ちます。

なお `--jinja` なしでも動かせるよう、バックエンドは失敗時に
`json_schema` → `json_object` → 指定なし、system ロールの user 統合、思考モード無効化の取りやめ、
の順に自動フォールバックします(詳細は [backend/llm_client.py](backend/llm_client.py))。
ただし出力の安定性は下がるため、`--jinja` を付けるのが本来の使い方です。

#### `-c`(コンテキスト長)の決め方

システムプロンプトに圧縮版のガイド要点と Few-shot 例を載せるため、入力側だけで数千トークンを
使います。**16384 を基準**にしてください。RF2VA で参照アセットを多く登録する場合や、ショット数が
多い場合は `32768` にすると余裕ができます。

`-c` を増やすと KV キャッシュのぶん VRAM 使用量が増えます。載り切らない場合は下記の対処を
検討してください。

#### `-ngl`(GPU オフロード)の決め方

- **VRAM に余裕がある**: `-ngl 99` で全層を GPU に載せる(最速)
- **VRAM が足りない**: `-ngl 20` のように数値を下げ、載る層数まで減らす。起動ログに
  `offloaded N/M layers to GPU` と出るので、そこで実際の状況を確認できます
- **GPU を使わない**: `-ngl 0`。動作はしますが、1 回の生成に数分かかることがあります

### 調整に使えるオプション

| オプション | 例 | 説明 |
|---|---|---|
| `-fa`, `--flash-attn` | `-fa on` | Flash Attention を有効化。対応 GPU ではメモリ使用量が減り高速になる |
| `--cache-type-k` / `--cache-type-v` | `--cache-type-k q8_0` | KV キャッシュを量子化して VRAM を節約する(`-fa` と併用) |
| `-t`, `--threads` | `-t 8` | CPU スレッド数。CPU 推論時に効く |
| `-np`, `--parallel` | `-np 2` | 並列処理するリクエスト数。1 人で使うなら既定のままでよい |
| `--api-key` | `--api-key secret` | API キーを要求する。設定した場合は `LLM_API_KEY` にも同じ値を設定する |
| `-v`, `--verbose` | `-v` | 詳細ログを出す。プロンプトが意図通り渡っているかの確認に使える |

`--temp` や `--top-p` などの生成パラメーターは、**リクエスト側の値(`LLM_TEMPERATURE` /
`LLM_TOP_P`)が優先される**ため、llama-server 側で指定する必要はありません。

### VRAM が足りないときの優先順位

1. `-fa on` を付ける
2. `--cache-type-k q8_0 --cache-type-v q8_0` で KV キャッシュを量子化する
3. `-c` を `16384` まで下げる(これ以上下げるとガイド要点が入り切らなくなる)
4. より小さい量子化(Q4_K_M → Q4_0 など)のモデルに替える
5. `-ngl` を下げて一部を CPU に逃がす(速度は落ちる)

## トラブルシューティング

### `LLM の応答に JSON が含まれていません` と出る

モデルの思考モード(`reasoning_content`)が有効だと、思考だけで `max_tokens` を使い切り、
本文(`content`)が空のまま返ってくることがあります。

1. llama-server に `--jinja` が付いているか確認する
2. `LLM_MAX_TOKENS` を `8192` などに増やす
3. それでも起きる場合は `LLM_DISABLE_THINKING=false` を試す(テンプレートが
   `enable_thinking` に対応せずエラーになっているケース)

`content` が空でも `reasoning_content` に JSON があれば、そちらから回収を試みます。

### `llama-server に接続できません` と出る

- llama-server が起動しているか(<http://127.0.0.1:8080> が開けるか)
- `LLM_BASE_URL` の末尾が `/v1` になっているか
- ポートを変えた場合、`.env` を更新してバックエンドを**再起動**したか

バックエンドの起動ログに出る `llama-server 接続先: ...` で、実際の接続先を確認できます。

### `.env` を変えたのに反映されない

`.env` は起動時に一度だけ読み込みます。`serve.py` を `Ctrl + C` で止めて実行し直してください。

### 生成に時間がかかる / 応答がない

`-ngl` が足りず CPU 推論になっている可能性があります。llama-server の起動ログで
`offloaded N/M layers to GPU` を確認してください。長時間かかる場合は `LLM_TIMEOUT_SEC` を
増やすことで打ち切りを避けられます。

### 生成が途中で切れる

`LLM_MAX_TOKENS` を増やしてください。ショット数が多い場合や RF2VA では、既定の `4096` では
足りないことがあります。

### 出力の品質が安定しない

- `--jinja` が付いているか確認する(最も影響が大きい)
- より大きい量子化(Q5_K_M / Q6_K)のモデルに替える
- `LLM_TEMPERATURE` を `0.6` 程度まで下げる

## 開発

ソースから動かす手順、フロントエンドの編集方法、リリースの作り方は
[CONTRIBUTING.md](CONTRIBUTING.md) にまとめています。

## ライセンス

[MIT License](LICENSE)

MiniMax-H3 および公式プロンプトガイドは、それぞれの権利者に帰属します。本アプリは
MiniMax の公式プロダクトではありません。
