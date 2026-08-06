# notes/ について

このフォルダは、チャットでのやり取りの中で分かった情報のうち、`data/`（取引データ）や
`scripts/`（パース処理）そのものには残らない文脈・前提・未解決事項をまとめたものです。
新しいセッションを始めるときは、まずここに目を通すと経緯を追いやすくなります。

最終更新: 2026-08-03

## ファイル一覧

- [`pipeline-workflow.md`](./pipeline-workflow.md) — **9月以降も明細を取り込み続けるための手順**。`data/raw/`に置くだけで動く形に2026-08-06にスクリプトを書き換え済み
- [`household-context.md`](./household-context.md) — 家族構成、カードの利用者、住居・収入按分の前提
- [`account-mapping.md`](./account-mapping.md) — どのカードがどの銀行口座から引き落とされているか
- [`open-issues.md`](./open-issues.md) — 未解決・要確認事項の一覧
- [`cards/aeon-card.md`](./cards/aeon-card.md) — イオンカード固有のメモ
- [`docomo/dcard-and-docomo-bank.md`](./docomo/dcard-and-docomo-bank.md) — dカード／ドコモの銀行／ahamo関連の状況
- [`../data/raw/README.md`](../data/raw/README.md) — アップロードされた明細書の原本アーカイブ（2026-08-03にこのリポジトリへ保存。それまではセッション用の一時領域にしかなく、消える可能性があった）

## 全体の前提

- ダッシュボード（`site/index.html`）は下記URLでArtifact公開中（デフォルト非公開）
  `https://claude.ai/code/artifact/e836a609-7153-4575-9111-401a4e0e5705`
- GitHubリポジトリ `MasatoshiSano/budget-book` は2026-07-30時点で非公開（private）設定を確認済み
- 作業ブランチ：`claude/sumitomo-card-statement-uauugs`
- サイトを更新する手順：`site/template.html` を編集 →
  `python3 site/build.py` で `site/index.html` を再生成 → Artifactツールで同じURLに再公開 → commit/push
