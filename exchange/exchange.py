from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum, unique
from typing import List, Tuple

import model.exchange
from model.candle import Candle, Interval
from model.pair import Pair
from service.dbservice import DBService


@unique
class OrderSide(Enum):
    BUY = 1
    SELL = 2


class Order:
    pair: Pair


class MarketOrder(Order):
    side: OrderSide
    volume: float

    def __init__(self, pair: Pair, side: OrderSide, volume: float):
        self.pair = pair
        self.side = side
        self.volume = volume


class LimitOrder(Order):
    side: OrderSide
    volume: float
    price: float

    def __init__(self, pair: Pair, side: OrderSide, volume: float, price: float):
        self.pair = pair
        self.side = side
        self.volume = volume
        self.price = price


class OrderId:
    pair: Pair
    id: int

    def __init__(self, pair: Pair, id: int):
        self.pair = pair
        self.id = id

    def __repr__(self):
        return f'<OrderId(pair={self.pair}, id={self.id}>'


class ExchangeHandler(ABC):
    name: str
    dbservice: DBService
    exchange: model.exchange.Exchange

    def __init__(self, dbservice: DBService):
        self.dbservice = dbservice
        self.exchange = dbservice.getExchange(self.name)

    @abstractmethod
    def _convertIntervalString(self, interval: Interval) -> str:
        return interval.value

    @abstractmethod
    def _convertPairSymbol(self, pair: Pair) -> str:
        return pair.asset + pair.currency

    @abstractmethod
    def _convertDate(self, date: datetime) -> str:
        return datetime.strftime(date, '%Y-%m-%d %H:%M:%S')

    @abstractmethod
    def _getHistoricalKlinesFromServer(self, pair: Pair, interval: Interval, periodStart: datetime,
                                       periodEnd: datetime) -> List[Candle]:
        pass

    def _fetchMissingHistoricalKlines(self, pair: Pair, interval: Interval,
                                      missingPeriods: List[Tuple[datetime, datetime]]) -> None:
        for periodStart, periodEnd, in missingPeriods:
            candles = self._getHistoricalKlinesFromServer(pair, interval, periodStart, periodEnd)
            self.dbservice.addCandles(candles)

    def getHistoricalKlines(self, pair: Pair, interval: Interval, periodStart: datetime, periodEnd: datetime) -> List[
        Candle]:
        missingPeriods = self.dbservice.findMissingCandlePeriods(self.exchange, pair, interval, periodStart, periodEnd)
        if missingPeriods:
            self._fetchMissingHistoricalKlines(pair, interval, missingPeriods)
            return self.getHistoricalKlines(pair, interval, periodStart, periodEnd)
        else:
            return self.dbservice.findCandles(self.exchange, pair, interval, periodStart, periodEnd)

    @abstractmethod
    def getPortfolio(self):
        pass

    # Get balance for a given asset
    @abstractmethod
    def getAssetBalance(self, asset: str):
        pass

    # Create an exchange order
    @abstractmethod
    def placeOrder(self, order: Order):
        pass

    # Check an exchange order status
    @abstractmethod
    def checkOrder(self, orderId):
        pass

    # Cancel an exchange order
    @abstractmethod
    def cancelOrder(self, orderId):
        pass

    @abstractmethod
    def getAllOrders(self, pair: Pair) -> List[Order]:
        pass

    @abstractmethod
    def getAllOpenOrders(self, pair: Pair) -> List[Order]:
        pass
