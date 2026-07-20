import json
import pandas as pd
from functools import partial
from fastapi import APIRouter, Depends, HTTPException, status
from util.log_service import LogService
from util.rule_registry import ENTRY_RULES, EXIT_RULES


from trading_rules_backend.app import schemas, cache
from trading_rules import entries as e, exits as ex, engine

from util.rule_registry import _collect_rules

logsvc = LogService("")
router = APIRouter(prefix="/rules", tags=["rules"])

ENTRY_RULES: dict[str, callable] = _collect_rules(e)
EXIT_RULES: dict[str, callable] = _collect_rules(ex)

@router.get("/get-rules")
async def strategies():
    try:
        
        with open("./trading_rules.json", "r") as tr:
            tr_json = json.load(tr)
            return tr_json

    except json.JSONDecodeError:
        logsvc.error("Could not decode the `trading_rules.json` file")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The configuration file is malformed JSON."
        )
        
    except Exception as e:
        logsvc.error(f"Something went wrong while reading `trading_rules.json`: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while reading the rules."
        )
    

@router.post("/run-backtest")
async def run_backtest(req: schemas.BacktestRequest):
    try:

        price_data = cache.get(req.data_id)

        if not price_data:
            logsvc.error(f"Could not find with data id: {req.data_id}")
            raise HTTPException(status_code=404, detail="Could not find requested data.")

        entry_rules = req.entry_rules
        exit_rules = req.exit_rules

        entries_partials = []
        exit_rules = []

        for entry in entry_rules:
            if ENTRY_RULES.get(entry):
                rule = ENTRY_RULES.get(entry)
                entries_partials.append(partial(rule, data=price_data))
            else:
                logsvc.error(f"{entry} rule does not exist.")
                continue

        for exit in exit_rules:
            if EXIT_RULES.get(exit):
                rule = ENTRY_RULES.get(exit)
                exit_rules.append(partial(rule, max_bars=144))
            else:
                logsvc.error(f"{exit} rule does not exist.")
                continue

        entries_series = [entry(data=price_data) for entry in entries_partials]
        # AND all the entry rules
        entries_series = pd.concat(entries_series, axis=1).all(axis=1)

        fee_param = FeeParams(
            model = FeeModel.POLYMARKET,
            rate_bps=500,
            rebate_share=0.0,
            min_fee_dollars=0.0
        )
        
        slippage_params = SlippageParams(
           bps = 2.0,
           atr_multiplier = 0.1
        )

        backtest = engine.backtest(data=price_data, 
                                   entries_series=entries_series,
                                   exit_rules=exit_rules,
                                   initial_cash=req.initial_capital,
                                   slippage_params=slippage_params,
                                   fee_params=fee_param)
        
        return backtest

    except Exception as e:
        logsvc.error(f"Could not backtest data-id: {req.data_id}. {e}")
        raise HTTPException(status_code=500, detail="Internal error while performing backtest, please try again")
