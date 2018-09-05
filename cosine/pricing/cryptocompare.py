"""
# 
# 27/08/2018
# Oladotun Rominiyi - Copyright © 2018. all rights reserved.
"""
__author__ = 'dotun rominiyi'

# IMPORTS
from decimal import Decimal
from socketIO_client import SocketIO
from cosine.core.instrument import CosinePairInstrument
from .base_feed import CosineBaseFeed


# MODULE CLASSES
class CryptoCompareSocketIOFeed(CosineBaseFeed):

    def __init__(self, name, pool, cxt, **kwargs):
        super().__init__(name, pool, cxt, **kwargs)
        self._socketio = None


    def _snapshot_cache(self):
        # nothing to do since we'll auto-snapshot on subscription to the websockets feed...
        pass


    def _setup_events(self, worker):
        worker.events.OnRawTick += self._on_raw_tick


    def _on_raw_tick(self, msg):
        # decode & cache pricing...
        FIELDS = {
            'TYPE': 0x0
        , 'MARKET': 0x0
        , 'FROMSYMBOL': 0x0
        , 'TOSYMBOL': 0x0
        , 'FLAGS': 0x0
        , 'PRICE': 0x1
        , 'BID': 0x2
        , 'OFFER': 0x4
        , 'LASTUPDATE': 0x8
        , 'AVG': 0x10
        , 'LASTVOLUME': 0x20
        , 'LASTVOLUMETO': 0x40
        , 'LASTTRADEID': 0x80
        , 'VOLUMEHOUR': 0x100
        , 'VOLUMEHOURTO': 0x200
        , 'VOLUME24HOUR': 0x400
        , 'VOLUME24HOURTO': 0x800
        , 'OPENHOUR': 0x1000
        , 'HIGHHOUR': 0x2000
        , 'LOWHOUR': 0x4000
        , 'OPEN24HOUR': 0x8000
        , 'HIGH24HOUR': 0x10000
        , 'LOW24HOUR': 0x20000
        , 'LASTMARKET': 0x40000
        }
        fields = msg.split('~')
        mask = int(fields[-1], 16)
        fields = fields[:-1]
        curr = 0
        data = {}
        for prop in FIELDS:
            if FIELDS[prop] == 0:
                data[prop] = fields[curr]
                curr += 1
            elif mask & FIELDS[prop]:
                if prop == 'LASTMARKET':
                    data[prop] = fields[curr]
                else:
                    data[prop] = float(fields[curr])
                    curr += 1

        instr = data["FROMSYMBOL"] + "/" + data["TOSYMBOL"]
        if instr in self._cache:
            cached = self._cache[instr]
            cached.lastmarket = data.get("LASTMARKET", cached.lastmarket)
            cached.midprice = Decimal(data.get("PRICE", cached.lasttraded))
            cached.openhour = Decimal(data.get("OPENHOUR", cached.openhour))
            cached.highhour = Decimal(data.get("HIGHHOUR", cached.highhour))
            cached.lowhour = Decimal(data.get("LOWHOUR", cached.lowhour))
            cached.openday = Decimal(data.get("OPEN24HOUR", cached.openday))
            cached.highday = Decimal(data.get("HIGH24HOUR", cached.highday))
            cached.lowday = Decimal(data.get("LOW24HOUR", cached.lowday))
            cached.lasttradedvol = Decimal(data.get("LASTVOLUME", cached.lasttradedvol))
            cached.lasttradedvolccy = Decimal(data.get("LASTVOLUMETO", cached.lasttradedvolccy))
            cached.dayvol = Decimal(data.get("VOLUME24HOUR", cached.dayvol))
            cached.dayvolccy = Decimal(data.get("VOLUME24HOURTO", cached.dayvolccy))

        # fire main tick...
        self._events.OnTick.fire()


    """Worker process run or inline run"""
    def run(self):
        self._setup()
        self._listen()


    """Worker process run or inline run"""
    def _setup(self):

        # establish the connection...
        self._socketio = SocketIO(self.endpoint, 80)

        # subscribe for all instruments...
        subs = []
        for n in self._cache:
            instrument = self._cache[n].instrument
            if not isinstance(instrument, CosinePairInstrument): continue
            subs.append('5~CCCAGG~{0}~{1}'.format(instrument.asset.symbol, instrument.ccy.symbol))

        self._socketio.emit('SubAdd', {"subs": subs})
        self._socketio.on('m', self._on_sio_tick)


    """Worker process run or inline run"""
    def _listen(self):
        self._socketio.wait()


    """Worker process run or inline run"""
    def _on_sio_tick(self, message):
        if self._worker:
            self._worker.enqueue_event("OnRawTick", message)
        else:
            self._on_raw_tick(message)
