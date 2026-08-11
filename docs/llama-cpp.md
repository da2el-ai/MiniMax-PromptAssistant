# llama.cpp(ローカル LLM)で動かす

自分の PC で LLM を動かす場合の手順です。外部サービスに入力内容を送らずに済み、
利用料もかかりません。そのかわり相応の GPU が必要です。

OpenRouter などの外部サービスを使う場合は [openrouter.md](openrouter.md) を参照してください。

## 1. llama.cpp を用意する

llama.cpp 自体のインストール方法は、公式リポジトリ
(<https://github.com/ggml-org/llama.cpp>)の手順に従ってください。お使いの OS と GPU に
合わせたビルド済みバイナリが配布されています。

モデルは筆者は [gemma-4-12B-it-qat-q4_0-uncensored-heretic-Q4_0](https://huggingface.co/llmfan46/gemma-4-12B-it-qat-q4_0-uncensored-heretic-GGUF) を使用しています。

## 2. llama-server を起動する

```bash
llama-server -m <モデルフォルダ>/<モデル名>.gguf -c 16384 -ngl 99 --jinja --host 127.0.0.1 --port 8080
```

**`--jinja` は本アプリの動作に必要です。** 理由は[後述](#--jinja-が必要な理由)します。

ブラウザで <http://127.0.0.1:8080> を開き、llama.cpp の Web UI が表示されれば起動できています。

## 3. `.env` を設定する

`backend/.env` を次のように設定します。既定値のままなので、ホストとポートを変えていなければ
書き換えは不要です。

```dotenv
LLM_BASE_URL=http://127.0.0.1:8080/v1
LLM_MODEL=local-model
LLM_API_KEY=
```

- `LLM_MODEL` — llama-server は単一モデルを読み込むため、任意の識別子でかまいません
- `LLM_API_KEY` — llama-server を `--api-key` 付きで起動した場合のみ、同じ値を設定します

設定できたら README の[アプリを起動する](../README.md#3-minimax-promptassistant-を起動する)に
進んでください。

## 起動オプション

### 必須・重要なオプション

| オプション | 例 | 説明 |
|---|---|---|
| `-m`, `--model` | `-m ~/models/model.gguf` | 読み込む GGUF ファイルのパス |
| `-c`, `--ctx-size` | `-c 16384` | コンテキスト長(トークン数)。**16384 以上を推奨** |
| `-ngl`, `--n-gpu-layers` | `-ngl 99` | GPU にオフロードする層数。`99` で全層を GPU に載せる |
| `--jinja` | `--jinja` | **本アプリでは必須。** 下記参照 |
| `--host` | `--host 127.0.0.1` | 待ち受けアドレス。既定は `127.0.0.1` |
| `--port` | `--port 8080` | 待ち受けポート。既定は `8080` |

### `--jinja` が必要な理由

本アプリはプロンプトの自由記述部分を **JSON で受け取る** ため、リクエストに次の 2 つを付けます。

- `response_format: {"type": "json_schema", ...}` — 出力を JSON スキーマに従わせる
- `chat_template_kwargs: {"enable_thinking": false}` — モデルの思考モードを止める

これらはモデル同梱の Jinja チャットテンプレートを使って処理されるため、`--jinja` を付けずに
起動すると無視されたりエラーになったりします。付け忘れると、生成が失敗するか品質が大きく落ちます。

なお `--jinja` なしでも動かせるよう、バックエンドは失敗時に
`json_schema` → `json_object` → 指定なし、system ロールの user 統合、思考モード無効化の取りやめ、
の順に自動フォールバックします(詳細は [backend/llm_client.py](../backend/llm_client.py))。
ただし出力の安定性は下がるため、`--jinja` を付けるのが本来の使い方です。

### `-c`(コンテキスト長)の決め方

システムプロンプトに圧縮版のガイド要点と Few-shot 例を載せるため、入力側だけで数千トークンを
使います。**16384 を基準**にしてください。RF2VA で参照アセットを多く登録する場合や、ショット数が
多い場合は `32768` にすると余裕ができます。

`-c` を増やすと KV キャッシュのぶん VRAM 使用量が増えます。載り切らない場合は
[VRAM が足りないときの優先順位](#vram-が足りないときの優先順位)を検討してください。

### `-ngl`(GPU オフロード)の決め方

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
