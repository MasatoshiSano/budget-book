# budget-book

三井住友カード・PayPayカード・楽天カードの利用明細を1つの家計簿ダッシュボードにまとめるためのリポジトリ。

## 構成

```
data/    各カードの取引データ（JSON）と、3カードを統合したデータ
scripts/ 明細PDF/CSVをパースしてdata/以下のJSONを作るスクリプト
site/    ダッシュボード（1枚のHTML）のテンプレートとビルドスクリプト
```

- `data/sumitomo_transactions.json` / `paypay_transactions.json` / `rakuten_transactions.json`
  … カードごとの取引一覧（カテゴリ分類済み）
- `data/unified_transactions.json` … 3カードを共通カテゴリで統合したもの。ダッシュボードはこのファイルを読む
- `site/template.html` … デザイン・ロジックのソース（`__DATA_JSON__` 等のプレースホルダを含む）
- `site/build.py` … `template.html` + `unified_transactions.json` + フォント(base64) から `site/index.html` を生成
- `site/index.html` … 生成物。これをそのままブラウザで開くか、Artifactとして公開する

## 新しい月の明細を追加する手順

1. 新しいPDF/CSVをアップロード
2. カードに応じたパーススクリプトを実行し、該当する `data/*_transactions.json` を更新
   （三井住友: `parse_sumitomo.py` → `categorize_sumitomo.py`、PayPay: `parse_categorize_paypay.py`、
   楽天: `parse_rakuten.py` → `categorize_rakuten.py`）
3. `python3 scripts/consolidate.py` で `data/unified_transactions.json` を再生成
4. `python3 site/build.py` で `site/index.html` を再生成
