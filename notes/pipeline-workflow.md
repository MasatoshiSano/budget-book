# データ取り込みパイプライン（9月以降も続けるための手順）

最終更新: 2026-08-06

## 前提：もう「このセッション固有」の情報には依存していない

2026-08-06以前は、`scripts/parse_*.py`が「このセッションのアップロード先
ディレクトリ（`/root/.claude/uploads/<セッションID>/`）」や「ファイル名→月」の
手書き対応表にハードコードされていて、**セッションが変わると動かなくなる**
状態だった（実際、`data/*_transactions.json`への最終書き出しがscratchpad止まり
で、リポジトリのスクリプトだけでは再現できないものもあった）。

2026-08-06に全スクリプトを見直し、**`data/raw/<ソース名>/`に置いた明細ファイル
から直接読み込んで`data/<ソース名>_transactions.json`まで一気に生成する**よう
書き換えた。お支払月・利用日も基本的に明細本文（PDFのヘッダーやCSVの列）から
自動抽出するようにし、ファイル名に依存する手書きの月対応表は撤去した
（三井住友・PayPay・楽天・住信SBI銀行・ゆうちょが対象。イオンカードだけ後述の
理由で引き続き手動）。書き換え後、再実行した結果が旧`data/*.json`と全件・
全カテゴリ一致することを確認済み。

## 9月分が来たら、これをやる

1. 新しい明細ファイル（三井住友・PayPay・楽天・イオン・住信SBI銀行・ゆうちょの
   うち届いたもの）を、**ファイル名は何でもいいので**次のフォルダに保存する：
   - `data/raw/sumitomo/`（PDF）
   - `data/raw/paypay/`（CSV）
   - `data/raw/rakuten/`（PDF）
   - `data/raw/bank_sbi/`（PDF、住信SBIネット銀行）
   - `data/raw/yucho/`（CSV、cp932エンコード）
   - `data/raw/aeon/`（PDF。ただしイオンは後述のとおり自動パース非対応）
2. 該当するスクリプトを再実行する（複数ソース分あれば全部）：
   ```
   python3 scripts/parse_sumitomo.py
   python3 scripts/parse_categorize_paypay.py
   python3 scripts/parse_rakuten.py
   python3 scripts/parse_bank.py
   python3 scripts/parse_yucho.py
   ```
   各スクリプトは**そのフォルダに置かれている全ファイル**を毎回まとめて読み
   直し、`data/<ソース名>_transactions.json`を再生成する（差分追記ではなく
   全量再生成なので、フォルダの中身さえ正しければ何回実行しても安全）。
3. `python3 scripts/consolidate.py` で `data/unified_transactions.json` に統合
4. `python3 site/build.py` で `site/index.html` を再生成
5. Artifactツールで同じURLに再公開、Playwrightで簡単に動作確認、commit/push

## イオンカードだけ別扱い（自動パース不可）

`scripts/parse_aeon.py`はPDFを自動で読み取っていない。イオンの明細PDFはテキスト
抽出結果が数字が1桁ずつバラバラになる崩れ方をするため、**明細を目視で書き起こし
て`ROWS_YYYYMM`というPythonのリストに手で追記する**運用になっている（書き起こし
た合計が明細書記載の「今回ご利用金額合計」と一致することをアサーションで検算
している）。9月分が来たら、`scripts/parse_aeon.py`の`ROWS_202608`の下に
`ROWS_202609`を追記し、`STATEMENTS`リストにも1行足す形になる。詳細は
[`cards/aeon-card.md`](./cards/aeon-card.md)。

## 各ソースの「どこから月を読み取っているか」（トラブル時の参考）

| ソース | 入力 | 月の情報源 |
|---|---|---|
| 三井住友 | `data/raw/sumitomo/*.pdf` | PDF内の「お支払い日 YYYY年M月D日」ヘッダーを正規表現抽出 |
| PayPay | `data/raw/paypay/*.csv` | 各行の「当月お支払日」列 |
| 楽天 | `data/raw/rakuten/*.pdf` | PDF内の「お支払日」行 |
| 住信SBI銀行 | `data/raw/bank_sbi/*.pdf` | 明細の取引日そのもの（「YYYY年MM月DD日」形式の行） |
| ゆうちょ | `data/raw/yucho/*.csv` | 各行の「取引日」列（取引IDで重複除去。ゆうちょのCSVは期間指定でエクスポートされ、複数ファイルの日付範囲が重なることがあるため） |
| イオン | 手動転記（`ROWS_YYYYMM`） | 明細書記載の支払日をコメントに手書き |

いずれも「明細ファイルのファイル名」には一切依存していない（旧バージョンは
ファイル名→月のハードコード辞書に依存していたが、これは撤去済み）。

## カテゴリ分類ルールについて

`scripts/parse_sumitomo.py` / `parse_categorize_paypay.py` / `parse_rakuten.py`
それぞれの中に、店名文字列に対するキーワードマッチのルール（`RULES`）が埋め
込まれている。新しい店・新しいサブスクなどが出てきて「その他」に分類されて
しまう場合は、該当スクリプトの`RULES`に店名キーワードを追記して再実行すれば
直る（過去分もまとめて再分類される）。

海外旅行時の決済（現地通貨のレストラン・交通・レジャーなど）を自動で
「旅行・宿泊」にまとめる処理は`scripts/consolidate.py`の`is_overseas_spend()`
にあり、三井住友の全行に対して全ソース共通のルールとして最後に適用される
（メモにEURを含む／店名・メモに「海外」を含む／英字＋括弧書きの都市名パターン、
のいずれか）。
