# FSM Agent Framework

**FSM（有限オートマトン）ベースの超軽量AIエージェントフレームワーク**

LangGraphのような複雑な抽象化を排除し、LLMの推論能力と構造化出力を最大限に活かすことで、「最小限のコード」と「明確な思考プロセス」を両立します。

---

## フレームワークが提供するもの

このフレームワークは、以下の**2つのコアコンポーネント**のみを提供します：

### 1. `FSM` クラス
状態遷移の定義と検証を行うシンプルなクラスです。

```python
from fsm_agent import FSM

fsm = FSM(
    states={
        "start": ["researching"],
        "researching": ["writing"],
        "writing": ["reviewing"],
        "reviewing": ["writing", "end"],
        "end": []
    },
    initial_state="start",
    terminal_states=["end"]
)

# 使用例
fsm.get_next_states()  # 現在の状態から遷移可能な状態のリストを取得
fsm.transition("researching")  # 状態遷移（検証付き）
fsm.is_terminal()  # 終了状態かどうかを判定
```

**機能:**
- 状態遷移の定義と検証
- 現在の状態の管理
- 遷移可能な状態の取得
- 終了状態の判定

### 2. `ToolRegistry` クラス
Python関数をツールとして登録・管理するクラスです。

```python
from fsm_agent import ToolRegistry

tools = ToolRegistry()

@tools.register
def research_web(topic: str) -> str:
    """指定されたトピックについてWeb調査を行う"""
    return f"Research completed: {topic}"

@tools.register
def write_article(content: str) -> str:
    """記事を執筆する"""
    return f"Article: {content}"

# 使用例
tools.execute("research_web", topic="AI")
tools.get_tool_schemas()  # LLM向けのツールスキーマを取得
```

**機能:**
- デコレータによるツール登録
- ツールの実行
- LLM向けスキーマの自動生成（OpenAI/Anthropic形式）
- 登録されたツールの一覧取得

### 3. ヘルパー関数

```python
# Anthropic形式のツールスキーマ生成
tools_to_anthropic_schema(tool_registry)

# オーケストレーター用のガイドテキスト生成
generate_orchestrator_guide(fsm, tool_registry)
```

---

## このフレームワークで作るエージェントの設計思想

### 3つの役割分担

フレームワークを使ってエージェントを構築する際は、以下の3つの役割を意識します：

#### ① FSM（地図）
「どの状態から、どの状態へ遷移できるか」を定義したプレーンな辞書データ。

- **役割**: エージェントが逸脱しないためのガードレール
- **設計方針**: ワークフローなら一方向、自律タスクなら分岐やループ
- **AIへの提示**: プロンプトで「現在の状態」と「遷移可能な選択肢」を常に提示

#### ② ツール（道具箱）
Python関数として登録されたツール群。

- **役割**: 現実世界（API、DB、計算）への作用
- **設計方針**: 「特化型エージェント」も「単なるツール」も区別せず、すべてPython関数として定義
- **統一インターフェース**: サブエージェント呼び出しも、単一ツール実行も、同じ「関数実行」として抽象化

#### ③ オーケストレーター（脳）
会話履歴を管理し、FSMの上で意思決定を行うLLM。

- **役割**: FSMの操作、ツールの選択、コンテキストの維持
- **思考プロセス**:
  1. 会話履歴（コンテキスト）を読み込む
  2. 現在のステートと、FSMに基づく「次の選択肢」を照らし合わせる
  3. 「次に何をすべきか」を構造化出力として宣言する
- **実装**: ユーザーが自由に実装（フレームワークは強制しない）

---

## 基本的な使い方

### ステップ1: FSMとツールを定義

```python
from anthropic import Anthropic
from fsm_agent import FSM, ToolRegistry, generate_orchestrator_guide, tools_to_anthropic_schema

# ツール定義
tools = ToolRegistry()

@tools.register
def research_web(topic: str) -> str:
    """指定されたトピックについてWeb調査を行う"""
    return f"Research completed: {topic} is important because..."

@tools.register
def write_article(research_result: str) -> str:
    """調査結果を元に記事を執筆する"""
    return f"Article: Based on research, here's the article..."

@tools.register
def review_article(article: str) -> str:
    """記事をレビューする"""
    if len(article) > 50:
        return "APPROVED"
    else:
        return "REJECTED: Too short"

# FSM定義
fsm = FSM(
    states={
        "start": ["researching"],
        "researching": ["writing"],
        "writing": ["reviewing"],
        "reviewing": ["writing", "end"],  # NGなら執筆に戻る
        "end": []
    },
    initial_state="start",
    terminal_states=["end"]
)
```

### ステップ2: オーケストレーターを実装

```python
client = Anthropic()

# システムプロンプト
system = [
    {
        "type": "text",
        "text": f"""
あなたはコンテンツ制作チームのリーダーです。

{generate_orchestrator_guide(fsm, tools)}

## あなたの役割
1. FSMの状態に従ってワークフローを進める
2. 各状態で適切なツールを選択・実行する
3. レビューで承認されるまで執筆を繰り返す
        """
    }
]

messages = [
    {"role": "user", "content": "AIの最新動向について記事を作成してください"}
]

# 特殊ツール: 状態遷移
def transition_state(next_state: str, reason: str = "") -> str:
    """状態を遷移する"""
    fsm.transition(next_state)
    return f"Transitioned to: {next_state}"

tools.register(transition_state)
```

### ステップ3: メインループ

```python
# メッセージ駆動型自律ループ
while not fsm.is_terminal():
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system,
        messages=messages,
        tools=tools_to_anthropic_schema(tools)
    )
    
    messages.append({"role": "assistant", "content": response.content})
    
    # ツール実行
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            result = tools.execute(block.name, **block.input)
            
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result)
            })
    
    if tool_results:
        messages.append({"role": "user", "content": tool_results})
    
    if response.stop_reason == "end_turn":
        break

print("Workflow completed!")
```

---

## アーキテクチャ: メッセージ駆動型自律ループ

オーケストレーター（LLM）と実行環境（Python）の間で、以下のサイクルを回します：

```
┌─────────────────────────────────────────┐
│ 1. 注入 (Context Injection)              │
│    - 会話履歴                            │
│    - 現在のステート                       │
│    - 遷移可能なステート                   │
│    - 使用可能なツール                     │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 2. 宣言 (AI Declaration)                 │
│    - LLMが次のアクションを構造化出力      │
│    - call_tool または transition         │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 3. 実行 (Execution)                      │
│    - Pythonがツール実行 or 状態遷移       │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 4. 蓄積 (Memory Accumulation)            │
│    - 実行結果を messages に追記           │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 5. 判定 (Termination Check)              │
│    - 終了状態に到達したか確認             │
└─────────────────────────────────────────┘
```

---

## 設計哲学

### なぜこの「薄さ」なのか

#### 1. **「地図」を渡せばLLMは歩ける**
現代のLLMは、FSMのような論理的な制約をプロンプトで与えれば、外部の複雑な制御ロジックなしで自律的に動けます。

#### 2. **ツールとエージェントのフラット化**
「ここからはエージェントの仕事、ここからはツールの仕事」という境界を消し、すべてをPython関数として定義することで、設計を極限までシンプルにします。

#### 3. **構造化出力への全面的な信頼**
パースエラーに怯える時代は終わりました。OpenAIやAnthropicの構造化出力機能を直接使うことで、LLMの「宣言」をそのままコードのロジックに直結させます。

#### 4. **オーケストレーション部分はユーザーが実装**
フレームワークは最小限のプリミティブ（FSM、ToolRegistry）のみを提供。ループの書き方、エラーハンドリング、ロギングなどは、ユーザーの要件に合わせて自由に実装できます。

---

## LangGraphとの違い

| 項目 | FSM Agent | LangGraph |
|------|-----------|-----------|
| **抽象化レベル** | 最小限（FSM + ToolRegistry） | 高レベル（Graph, Node, Edge） |
| **ループ制御** | ユーザーが実装 | フレームワークが提供 |
| **状態管理** | シンプルなFSM | StateGraph with reducers |
| **学習コスト** | 低（Pythonの基礎のみ） | 中〜高（独自概念多数） |
| **カスタマイズ性** | 完全に自由 | フレームワークの範囲内 |
| **適用範囲** | シンプルなワークフロー〜中規模タスク | 大規模・複雑なマルチエージェント |

---

## ライセンス

MIT

---

## まとめ

このフレームワークは、**最小限のプリミティブ**を提供することで、LLMの推論能力を最大限に引き出します。

- **フレームワークが提供**: `FSM` と `ToolRegistry`
- **ユーザーが実装**: オーケストレーションループ、プロンプト設計、エラーハンドリング
- **LLMが担当**: 状態遷移の判断、ツール選択、タスク実行

シンプルさと柔軟性を両立した、新しいエージェントフレームワークです。