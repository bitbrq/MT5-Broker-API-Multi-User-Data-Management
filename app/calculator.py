from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import MetaTrader5 as mt5App
from app.middleware import *
from app.utils import *
from app.models import *
import pandas as pd
import pytz

async def info_deposit(cursor):
    conditions = [
        "comment NOT LIKE '%swap%'",
        "comment NOT LIKE '%Swap%'",
        "comment NOT LIKE '%SWAP%'"
    ]
    query = f"SELECT SUM(profit) FROM history_deals WHERE symbol = '' AND profit > 0 AND {' AND '.join(conditions)}"
    deposit = cursor.execute(query).fetchone() 
    return deposit[0] if deposit and deposit[0] is not None else 0.0

async def info_withdrawal(cursor):
    query = f"SELECT SUM(profit) FROM history_deals WHERE symbol = '' AND profit < 0"
    withdrawal = cursor.execute(query).fetchone()
    return abs(withdrawal[0]) if withdrawal and withdrawal[0] is not None else 0.0

async def info_profit(cursor, balance, deposit, withdrawal):
    conditions = [
        "comment LIKE '%reversal%'",
        "comment LIKE '%Reversal%'",
        "comment LIKE '%REVERSAL%'"
    ]
    query = f"SELECT SUM(profit) FROM history_deals WHERE symbol = '' AND profit < 0 AND {' AND '.join(conditions)}"
    adjustment = cursor.execute(query).fetchone() 
    profit = balance + withdrawal - deposit + abs(adjustment[0])
    return profit

