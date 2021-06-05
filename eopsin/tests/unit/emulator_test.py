import datetime
import os
import unittest

import sqlalchemy as sql

import eopsin as eop


class TestBinanceEmulator(unittest.TestCase):

    def __init__(self, *args):
        super().__init__(*args)
        engine = sql.create_engine("sqlite://", echo=False, future=True)
        self.dbService = eop.DBService(engine)
        self.BINANCE_API_KEY = os.environ['BINANCE_TEST_API_KEY']
        self.BINANCE_API_SECRET = os.environ['BINANCE_TEST_API_SECRET']
        self.binance = eop.BinanceHandler(self.dbService, self.BINANCE_API_KEY, self.BINANCE_API_SECRET, testnet=True)

    def setUp(self) -> None:
        self.emulator = eop.ExchangeEmulator(self.binance, portfolio={'BTC': 100})

    def test_basicDelegation(self):
        pair = self.dbService.getPair('BTC', 'USDT')
        interval = eop.Interval.DAY_1
        begin = datetime.datetime(2021, 5, 10, 10, 0, 00)
        end = datetime.datetime(2021, 5, 10, 12, 0, 00)
        self.assertEqual(self.binance._getHistoricalKlinesFromServer(pair, interval, begin, end),
                         self.emulator._getHistoricalKlinesFromServer(pair, interval, begin, end),
                         "_getHistoricalKlinesFromServer should be delegated to the underlying handler")

    def test_portfolio(self):
        self.assertEqual(100, self.emulator.getAssetBalance('BTC'))
        self.assertEqual({'BTC': 100}, self.emulator.getPortfolio())

        self.emulator.getPortfolio()['ETH'] = 100
        self.assertEqual(0, self.emulator.getAssetBalance('ETH'), "Dict changes should not affect the simulator state")

    def test_marketOrder(self):
        pair = self.dbService.getPair('BTC', 'USDT')
        order = eop.MarketOrder.newSell(pair, 30)
        orderId = self.emulator.placeOrder(order)

        self.assertEqual(self.emulator.checkOrder(orderId), eop.OrderStatus.FILLED)
        self.assertEqual(70, self.emulator.getAssetBalance('BTC'))
        self.assertGreater(self.emulator.getAssetBalance('USDT'), 0)


class CourseRecorder(eop.Strategy):
    name = 'CourseRecorder'

    def __init__(self, exchange: eop.ExchangeHandler):
        self.exchange = exchange
        self.candles = []
        self.exchange.events[eop.Interval.MINUTE_1] += self.recordLastMinuteCandle

    def recordLastMinuteCandle(self, *args, **kwargs):
        pair = self.exchange.dbservice.getPair('BTC', 'USDT')
        candle = self.exchange.getLastCompleteCandleBefore(pair, eop.Interval.MINUTE_1, self.exchange.getTime())
        self.candles.append(candle)


class TestBinanceEmulatorBacktesting(unittest.TestCase):

    def __init__(self, *args):
        super().__init__(*args)
        engine = sql.create_engine("sqlite://", echo=False, future=True)
        dbService = eop.DBService(engine)
        BINANCE_API_KEY = os.environ['BINANCE_TEST_API_KEY']
        BINANCE_API_SECRET = os.environ['BINANCE_TEST_API_SECRET']
        self.binance = eop.BinanceHandler(dbService, BINANCE_API_KEY, BINANCE_API_SECRET)

    def setUp(self) -> None:
        self.emulator = eop.ExchangeEmulator(self.binance, portfolio={'BTC': 100})

    def test_newMinuteCandleTrigger(self):
        recorder = CourseRecorder(self.emulator)
        periodStart = datetime.datetime(2021, 4, 1, 10, 0, 0)
        periodEnd = datetime.datetime(2021, 4, 1, 10, 10, 0)
        self.emulator.backtest(periodStart, periodEnd)
        self.assertEqual(10, len(recorder.candles), "The Recorder should shave seen 10 1-minute candles")

        # Test against some known values
        openTimes = (periodStart + i * eop.Interval.MINUTE_1.timedelta() for i in range(10))
        closes = [58862.22, 58911.0, 58894.03, 58955.12, 58945.23, 58886.39, 58932.13, 58951.38, 58910.0, 58898.31]

        for openTime, close, candle in zip(openTimes, closes, recorder.candles):
            self.assertEqual(openTime, candle.openTime)
            self.assertEqual(close, candle.close)


if __name__ == '__main__':
    unittest.main()
