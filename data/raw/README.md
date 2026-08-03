# data/raw/ — オリジナルの明細書アーカイブ

アップロードされた明細PDF/CSVの原本を、`scripts/`のパース対象として再利用しやすいよう
ソース別・月別（`YYYY-MM.pdf`または`.csv`）に整理したもの。元のアップロードファイルは
セッション用の一時ディレクトリにしかなく永続化されないため、2026-08-03にこのリポジトリへ
コピーして保存した。

## フォルダ対応表

| フォルダ | 内容 | 対応するパーススクリプト | 月ラベルの基準 |
|---|---|---|---|
| `sumitomo/` | 三井住友カード ご利用明細（1〜7月） | `scripts/parse_sumitomo.py` | お支払い日の月 |
| `paypay/` | PayPayカード ご利用明細CSV（1〜7月） | `scripts/parse_categorize_paypay.py` | 明細ファイル名のYYYYMM |
| `rakuten/` | 楽天カード ご請求明細書（1〜7月） | `scripts/parse_rakuten.py` | ご請求月 |
| `bank_sbi/` | 住信SBIネット銀行 取引明細書（1〜7月） | `scripts/parse_bank.py` | 対象期間の開始月 |
| `yucho/` | ゆうちょ銀行 入出金明細CSV（6〜7月分のみ） | `scripts/parse_yucho.py` | 明細の対象期間 |
| `aeon/` | イオンカード ご利用明細書（4〜8月） | `scripts/parse_aeon.py` | お支払い日の月 |

## 欠けているもの

- 三井住友・PayPay・楽天・住信SBI：8月以降分は未取得
- イオンカード：4月がカード契約開始月のため、それ以前は存在しない（探す必要なし）
- アメックス：明細自体が未取得（`../../notes/open-issues.md`参照）
- ahamo：2026年7月契約開始（本人明言）だが明細は未取得

新しい月の明細が届いたら、このフォルダに同じ命名規則（`YYYY-MM.拡張子`）で追加し、
対応するパーススクリプトの`FILES`リストを更新してから`scripts/consolidate.py`を再実行する。
