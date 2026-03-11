import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd

from scripts.masters_indicators import (
    _extract_saved_csv_path,
    find_or_fetch_csv,
    step1_weinstein_filter,
    step2_wyckoff_volume,
    step3_darvas_breakout,
)


def make_df(length: int, close_start: float = 10.0, close_step: float = 0.1, volume: float = 1000.0):
    dates = pd.date_range(end=datetime.today(), periods=length, freq="D")
    close = [close_start + close_step * i for i in range(length)]
    data = {
        "date": dates,
        "open": [c * 0.99 for c in close],
        "close": close,
        "high": [c * 1.01 for c in close],
        "low": [c * 0.98 for c in close],
        "volume": [volume for _ in range(length)],
    }
    return pd.DataFrame(data)


class TestMastersIndicators(unittest.TestCase):
    def test_extract_saved_csv_path(self):
        stdout = "正在获取...\n数据已保存: /tmp/600519.csv\n共 10 条记录\n"
        path = _extract_saved_csv_path(stdout)
        self.assertEqual(path, "/tmp/600519.csv")

    @patch("scripts.masters_indicators.subprocess.run")
    @patch("scripts.masters_indicators.glob.glob")
    @patch("scripts.masters_indicators.os.path.exists")
    def test_find_or_fetch_csv_returns_parsed_path(self, mock_exists, mock_glob, mock_run):
        mock_glob.return_value = []
        mock_exists.return_value = True
        mock_run.return_value = type(
            "RunResult",
            (),
            {
                "returncode": 0,
                "stdout": "正在获取...\n数据已保存: /tmp/600519_20250101_20250301.csv\n",
                "stderr": "",
            },
        )()

        path = find_or_fetch_csv("600519", 250)
        self.assertEqual(path, "/tmp/600519_20250101_20250301.csv")

    @patch("scripts.masters_indicators.subprocess.run")
    @patch("scripts.masters_indicators.glob.glob")
    @patch("scripts.masters_indicators.os.path.exists")
    def test_find_or_fetch_csv_fallback_to_latest_glob(self, mock_exists, mock_glob, mock_run):
        mock_exists.return_value = False
        mock_glob.side_effect = [[], ["data/600519_20250501_20260311.csv"]]
        mock_run.return_value = type(
            "RunResult",
            (),
            {"returncode": 0, "stdout": "done without explicit path", "stderr": ""},
        )()

        path = find_or_fetch_csv("600519", 250)
        self.assertEqual(path, "data/600519_20250501_20260311.csv")

    def test_step1_neutral_when_not_enough_data(self):
        df = make_df(149)
        result = step1_weinstein_filter(df)
        self.assertEqual(result["status"], "NEUTRAL")

    def test_step1_pass_on_uptrend(self):
        df = make_df(200, close_start=10.0, close_step=0.2, volume=2000.0)
        result = step1_weinstein_filter(df)
        self.assertEqual(result["status"], "PASS")

    def test_step2_no_division_by_zero_when_only_up_days(self):
        df = make_df(12, close_start=10.0, close_step=0.5, volume=1000.0)
        result = step2_wyckoff_volume(df)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(any("比值 ∞x" in line for line in result["details"]))

    def test_step2_neutral_with_zero_volume_flat_prices(self):
        df = make_df(12, close_start=10.0, close_step=0.0, volume=0.0)
        result = step2_wyckoff_volume(df)
        self.assertEqual(result["status"], "NEUTRAL")

    def test_step3_neutral_when_not_enough_data(self):
        df = make_df(29, close_start=10.0, close_step=0.1, volume=1000.0)
        result = step3_darvas_breakout(df)
        self.assertEqual(result["status"], "NEUTRAL")

    def test_step3_handles_zero_volume_gracefully(self):
        df = make_df(60, close_start=20.0, close_step=0.02, volume=0.0)
        result = step3_darvas_breakout(df)
        self.assertIn(result["status"], ("PASS", "NEUTRAL", "FAIL"))
        self.assertTrue(any("成交量基准为 0" in line for line in result["details"]))

    def test_step3_pass_on_box_breakout_with_volume(self):
        df = make_df(60, close_start=100.0, close_step=0.0, volume=1000.0)
        # 构造近 30 日窄幅箱体 + 最后一天放量接近突破
        for i in range(30, 59):
            base = 100.0 + ((i % 5) - 2) * 0.4
            df.at[i, "open"] = base * 0.995
            df.at[i, "close"] = base
            df.at[i, "high"] = base * 1.01
            df.at[i, "low"] = base * 0.99
            df.at[i, "volume"] = 1000.0

        df.at[59, "open"] = 109.0
        df.at[59, "close"] = 110.0
        df.at[59, "high"] = 111.0
        df.at[59, "low"] = 108.0
        df.at[59, "volume"] = 4000.0

        result = step3_darvas_breakout(df)
        self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
