超軽量AIエージェントフレームワーク「fsm-agent-fw」を作りました。果たしてエージェントフレームワークと呼べるのかも微妙ですが、、

Finite State Machine（有限オートマトンともいう）とツール定義だけの超シンプルなPythonフレームワークです。DSLなしで純粋なPythonコードでAIエージェント作成できます。

「地図（FSM）」を持たせることで、LLMが迷子にならずに自律的に動けるようになります。
最小限のコードで、明確な思考プロセスを持つエージェントが作れます。

こちらから

https://github.com/shuent/fsm_agent_fw
https://pypi.org/project/fsm-agent-fw


## なぜ作ったか

元から、タスク管理の依存性ってDAGで表現できるよなーとか、エージェントはFSMだよな (LangGraphのグラフもそんな感じ)、とか考えてました。

最近のclaude Code などのAIオーケストレーターという概念から着想、大手LLMのSDKだけで、シンプルにエージェント設計できるんじゃね？-> FSMをLLMに渡してしまえ。
サブエージェントに仕事は任せて状態管理に専念してもらう、もシンプルなアーキテクチャーで実現できるんじゃないかと。

LangGraphはコードで状態管理をしてましたが、そこをLLMに任せてしまおう、というものです。

無料なのでAntigravityで作ってみました。

## できること
*   FSMによる状態管理: Pythonの辞書で「調査中」→「執筆中」といった状態遷移を定義できます。エージェントの行動をガードレールで囲い、暴走を防げます。
*   普通の関数をツール化: `def` で書いた普通のPython関数をデコレータで登録するだけで、LLMが使えるツールになります。
*   構造化スキーマの自動生成: 登録したツールとFSMの状態から、「今できること」と「次の行き先」を記述したシステムプロンプトや、Gemini/OpenAI向けのスキーマを自動生成します。

## できないこと
*   リッチなコンテキスト管理はしません: 会話履歴や巨大なテキストデータの管理機能はフレームワークから削ぎ落としました。
*   実行ループは隠蔽しません: `run()` メソッド一発で全部よしなに...という機能はありません。`while` ループは自分で書きます。これによって、どこで何が起きているかが完全に透明になり、デバッグが容易になります。
*   複雑なグラフ構造はありません: ノード、エッジ、リデューサーといった独自の概念は覚えなくて大丈夫です。あるのはFSMとツール、それだけです。

## こんな感じで使います
実際に、`Gemini 2.5 Flash Lite` と組み合わせて「リサーチ → 執筆 → レビュー」を行うエージェントの例です。
コード全体は `example/gemini_basic.py` にありますが、ポイントを絞って解説します。

### 1. ツールと「Hidden Context」の定義
ツールは普通の関数に `@tools.register` をつけるだけです。
ここで重要なのは `execution_context` という辞書を定義している点です。記事本文のような長いテキストは、LLMのコンテキストウィンドウを圧迫しないよう、この辞書（Hidden Context）に保存し、ツール間でのみ共有します。LLMには「保存しました」「読み込みました」という事実だけを伝えます。

```python
# コンテキスト（今回は単なる辞書）
execution_context = {}

@tools.register
def write_article(topic: str, research_summary: str) -> str:
    """リサーチ結果を元に記事を執筆する"""
    content = f"Title: {topic}\n\n..."
    
    # 1. Hidden Contextに保存
    execution_context["current_article"] = content
    
    # 2. 成果物をファイル保存
    with open("article.txt", "w") as f:
        f.write(content)

    # 3. LLMにはサマリーだけ返す（トークン節約）
    return f"Article on '{topic}' written and stored in context."

@tools.register
def review_article() -> str:
    """コンテキスト内の記事をレビューする"""
    # LLM経由ではなく、直接コンテキストから読み出す
    article_content = execution_context.get("current_article")
    
    if len(article_content) > 10:
        return "APPROVED"
    return "REJECTED"
```

### 2. FSM（地図）の定義
状態遷移を辞書で定義します。
「レビューがNGなら執筆に戻る」といったループ構造も単純なリストで表現できます。

```python
fsm = FSM(
    states={
        "start": ["researching"],
        "researching": ["writing"],
        "writing": ["reviewing"],
        "reviewing": ["writing", "end"], # レビューNGなら書き直し
        "end": []
    },
    initial_state="start",
    terminal_states=["end"]
)
```

### 3. メインループ（自律駆動）
`fsm.is_terminal()` になるまでループを回します。
ポイントは `generate_orchestrator_guide(fsm, tools)` です。これは、「現在の状態」と「そこから遷移できる状態」 を動的にプロンプトとして生成してくれるヘルパー関数です。
これをSystem Instructionに埋め込むことで、LLMは常に「自分の現在地」を把握しながら行動できます。

```python
while not fsm.is_terminal():
    # 動的ガイドの生成
    # 例: "Current State: researching. You can transition to: ['writing']..."
    orchestrator_guide = generate_orchestrator_guide(fsm, tools)
    
    system_instruction = f"""
    あなたは自律エージェントです。
    {orchestrator_guide}
    ゴール: {user_request}
    """

    # LLM呼び出し (Google GenAI SDK)
    response = client.models.generate_content(...)
    
    # ツール実行などの処理...
```

たったこれだけで、「リサーチが終わったら次は執筆だな」「レビューで落ちたから書き直そう」と判断できるエージェントが完成します。

## さいごに
まだプロトタイプなので、粗い部分もあるかと思いますが、コンセプト検証としてAntigravityと一緒に爆速で作ってみました。
「こういうのでいいんだよ、こういうので」と思ってもらえたら嬉しいです。よかったらGitHubでStarやPRをいただけると励みになります。
