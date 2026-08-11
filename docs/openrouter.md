# OpenRouter(外部サービス)で動かす

[OpenRouter](https://openrouter.ai/) は、多数の LLM を OpenAI 互換 API 経由でまとめて
使えるサービスです。GPU を用意しなくても本アプリを動かせます。

ローカル LLM で動かす場合は [llama-cpp.md](llama-cpp.md) を参照してください。

## 事前に知っておくこと

- **入力内容が OpenRouter と、その先のモデル提供元に送信されます。** 公開したくない内容を
  扱う場合はローカル LLM を使ってください
- **従量課金です。** 生成 1 回ごとに料金が発生します(モデルによって単価は大きく異なります)
- モデルによっては表現の規制が強く、生成を拒否されることがあります

## 1. API キーを取得する

1. <https://openrouter.ai/> でアカウントを作る
2. [Credits](https://openrouter.ai/settings/credits) からクレジットを購入する
3. [Keys](https://openrouter.ai/settings/keys) で API キーを発行する(`sk-or-v1-` で始まる文字列)

API キーは再表示できないため、発行時にコピーして控えておいてください。

## 2. `.env` を設定する

`backend/.env` を次のように設定します。

```dotenv
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=cognitivecomputations/dolphin-mistral-24b-venice-edition
LLM_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

この 3 つ以外は既定値のままで動作を確認しています。

- `LLM_MODEL` — [Models](https://openrouter.ai/models) に載っているモデル ID をそのまま指定します
- `LLM_API_KEY` — 手順 1 で取得したキー。**このファイルを他人に渡さないでください**

設定できたら README の[アプリを起動する](../README.md#3-minimax-promptassistant-を起動する)に
進んでください。

## モデルの選び方

- **JSON 出力に対応していること。** 本アプリは `response_format` で JSON を要求します。
  対応していないモデルでも自動フォールバックで動きますが、出力が不安定になります
- **指示追従性が高いこと。** ガイド準拠の細かい書式を守らせるため、極端に小さいモデルだと
  検証エラーで再生成を繰り返し、そのぶん料金がかさみます
- **表現の規制が緩いこと。** 動画の内容によっては、規制の強いモデルだと生成を拒否されます

## 料金を抑えるには

- ヘッダーの接続確認は**起動時の 1 回だけ**です。以降は「接続確認」ボタンを押したときにのみ
  リクエストを送るので、画面を開いたままでも料金は発生しません
- `GENERATE_MAX_RETRIES` を下げると、検証 NG 時の再生成回数が減ります(既定は `3`)
- OpenRouter には無料枠のモデル(ID が `:free` で終わるもの)もあります。品質は落ちますが
  動作確認には使えます

## うまく動かないとき

### `HTTP 400` が返る

思考モードを止めるために送っている `chat_template_kwargs` を、モデルによっては拒否します。
その場合は `.env` に次を追加してください。

```dotenv
LLM_DISABLE_THINKING=false
```

なお、この設定がなくてもバックエンドは自動でフォールバックして最終的には成功しますが、
初回に無駄なリクエストが 1 回発生します。

### `HTTP 401` が返る

`LLM_API_KEY` が正しいか、キーが失効していないかを確認してください。`.env` を変更したら
バックエンドの**再起動**が必要です。

### `HTTP 402` が返る

クレジット残高が不足しています。[Credits](https://openrouter.ai/settings/credits) を確認して
ください。

### 生成に時間がかかる

混雑しているモデルや、思考モードを持つモデルでは応答が遅くなります。`LLM_TIMEOUT_SEC` を
増やすか、別のモデルを試してください。
