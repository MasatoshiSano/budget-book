# notes/ について

このフォルダは、チャットでのやり取りの中で分かった情報のうち、`data/`（取引データ）や
`scripts/`（パース処理）そのものには残らない文脈・前提・未解決事項をまとめたものです。
**このリポジトリを引き継ぐAIエージェント（Claudeに限らず、どのAIでも）は、作業を
始める前にまずこのフォルダ全体に目を通してください。** チャット履歴やセッションの
記憶に頼らなくても、このリポジトリの`notes/`・`data/`・`scripts/`・`site/`だけで
経緯と現状が把握できることを目指しています。

最終更新: 2026-09-12

## ファイル一覧

- [`pipeline-workflow.md`](./pipeline-workflow.md) — **月次で明細を取り込み続けるための手順**。`data/raw/`に置くだけで動く形にスクリプトを書き換え済み（2026-08-06）
- [`household-context.md`](./household-context.md) — 家族構成、カードの利用者、住居・収入按分の前提
- [`account-mapping.md`](./account-mapping.md) — どのカードがどの銀行口座から引き落とされているか
- [`open-issues.md`](./open-issues.md) — 未解決・要確認事項の一覧
- [`cards/aeon-card.md`](./cards/aeon-card.md) — イオンカード固有のメモ
- [`docomo/dcard-and-docomo-bank.md`](./docomo/dcard-and-docomo-bank.md) — dカード／ドコモの銀行／ahamo／リクルートカード比較の状況と結論
- [`docomo/ymobile-switch.md`](./docomo/ymobile-switch.md) — ahamoからY!mobileへの乗り換え検討（機種・特典・24ヶ月コスト試算）
- [`assets.md`](./assets.md) — 資産状況（証券口座の評価額等）のメモ。家計簿本体（フロー）とは別管理でダッシュボード未反映
- [`../data/raw/README.md`](../data/raw/README.md) — アップロードされた明細書の原本アーカイブ（2026-08-03にこのリポジトリへ保存。それまではセッション用の一時領域にしかなく、消える可能性があった）

## このプロジェクトの全体像（AIエージェント非依存の説明）

このリポジトリは「家計簿ダッシュボード」を作るためのもので、構成要素は次の4つだけです。

1. `data/raw/` — 明細書の原本（PDF/CSV）のアーカイブ。ソースごとにサブフォルダ分け。
2. `scripts/parse_*.py` — 上記を読み込んでカテゴリ分類し、`data/<ソース>_transactions.json`
   を生成するPythonスクリプト（ソースごとに1本）。
3. `scripts/consolidate.py` — 全ソースの`data/*_transactions.json`を統合し、
   カテゴリ体系を揃えて`data/unified_transactions.json`を生成する。
4. `site/template.html`（編集対象）→ `site/build.py`が`unified_transactions.json`を
   埋め込んで `site/index.html`（完成品、単体で開けば動く静的HTML）を生成する。

**このリポジトリ自体（gitの内容）がすべての正となる情報源です。** 特定のAIツール
（ClaudeのArtifact機能など）が使えなくても、`site/index.html`をブラウザで直接開けば
ダッシュボードとして動作します。デプロイ・共有の方法は問いません
（GitHub Pagesでホストする、ローカルで開く、別のAIエージェントの成果物公開機能を
使う、等）。

### 更新の基本手順（どのAIツールでも共通）

1. 新しい明細ファイルを `data/raw/<ソース名>/` に保存（詳細は
   [`pipeline-workflow.md`](./pipeline-workflow.md)）
2. 該当する `python3 scripts/parse_*.py` を実行
3. `python3 scripts/consolidate.py` を実行
4. `python3 site/build.py` を実行して `site/index.html` を再生成
5. 動作確認（ブラウザで開く、または自動テストがあれば実行）
6. `git add` / `git commit` / `git push`

Claude Code（このリポジトリで主に使われてきたツール）を使う場合は、手順4の後に
Artifact機能で同じURLに再公開する手順が追加で入るが、これは配布の利便性のための
追加ステップであり、リポジトリの正しさとは無関係。

## 個別の前提（Claude Code固有の情報）

- ダッシュボードは以下のURLでClaude Artifactとして公開中（デフォルト非公開）。
  ただしこれはClaude Code経由の配布手段の一つに過ぎず、他のAIエージェントは
  この URLを使う必要はない（`site/index.html`を直接使えばよい）。
  `https://claude.ai/code/artifact/e836a609-7153-4575-9111-401a4e0e5705`
- GitHubリポジトリ `MasatoshiSano/budget-book` は非公開（private）設定
  （2026-07-30時点で確認済み）。**この設定は維持すること**（家計の個人情報を
  含むため）。
- 作業ブランチ：`claude/sumitomo-card-statement-uauugs`
- サイトの給与額など、具体的な金額の一部（世帯収入の絶対額）はプライバシー上の
  理由でダッシュボード上には非表示にする方針（比率のみ掲載）。詳細は
  [`household-context.md`](./household-context.md)。
