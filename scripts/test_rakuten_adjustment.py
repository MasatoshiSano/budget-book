# -*- coding: utf-8 -*-
# Locks in: Rakuten statements that zero out via 調整額/返金額 must not
# leave the cancelled spend in the dashboard totals.
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from parse_rakuten import (  # noqa: E402
    parse_refund_yen,
    parse_statements,
    reversal_name,
    statement_balance,
    statements_to_rows,
)


class StatementBalanceTests(unittest.TestCase):
    def test_no_adjustment(self):
        self.assertEqual(statement_balance(84671, 84671, 0), 0)

    def test_february_2026_cancelled_toshi(self):
        # ご請求金額 0円, 明細 23,044円, 返金額 26,950円
        # → 1月の投信積立 49,994円のキャンセルを1行で戻す
        self.assertEqual(statement_balance(0, 23044, 26950), -49994)

    def test_adjustment_without_refund(self):
        self.assertEqual(statement_balance(4000, 5000, 0), -1000)

    def test_refund_parser_february_header(self):
        text = (
            'お支払日 返済方法 引落口座 請求確定日 利用獲得ポイント 調整額 返金額\n'
            '2026/02/27 口座振替 ゆうちょ銀行 2026/02/19 0ポイント -23,044円 26,950円\n'
        )
        self.assertEqual(parse_refund_yen(text), 26950)

    def test_refund_parser_zero(self):
        text = '279ポイント 0円 0円'
        self.assertEqual(parse_refund_yen(text), 0)

    def test_reversal_reuses_matching_merchant(self):
        prior = [{'name': '楽天証券投信積立０．５％〜', 'amount': 49994}]
        self.assertEqual(
            reversal_name(-49994, prior),
            '楽天証券投信積立０．５％〜（キャンセル・返金）',
        )

    def test_reversal_fallback(self):
        self.assertEqual(
            reversal_name(-100, [{'name': 'ETC', 'amount': 370}]),
            '請求調整（キャンセル・返金）',
        )


class RealFebruaryStatementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.statements = parse_statements()
        cls.rows = statements_to_rows(cls.statements)

    def test_every_statement_matches_cash(self):
        for s in self.statements:
            cash = s['header_total'] - s['refund']
            self.assertTrue(s['match'], msg=s['file'])
            self.assertEqual(s['parsed_sum'], cash, msg=s['file'])

    def test_february_net_is_the_refund_not_the_line_items(self):
        feb = [r for r in self.rows if r['pay_date'] == '2026-02-27']
        self.assertEqual(sum(r['amount'] for r in feb), -26950)
        reversals = [r for r in feb if r['amount'] < 0]
        self.assertEqual(len(reversals), 1)
        self.assertEqual(reversals[0]['amount'], -49994)
        self.assertEqual(reversals[0]['category'], '投資')
        self.assertIn('投信積立', reversals[0]['name'])

    def test_january_investment_is_netted_to_zero_across_months(self):
        toshi = [r for r in self.rows if '投信積立' in r['name']]
        self.assertEqual(sum(r['amount'] for r in toshi), 0)


if __name__ == '__main__':
    unittest.main()
