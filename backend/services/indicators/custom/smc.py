from functools import wraps
import pandas as pd
import numpy as np
from pandas import DataFrame, Series
from datetime import datetime
from typing import Union, List, Optional

def inputvalidator(input_="ohlc"):
    def dfcheck(func):
        @wraps(func)
        def wrap(*args, **kwargs):
            args = list(args)
            # Find the dataframe in args
            df_idx = -1
            for idx, arg in enumerate(args):
                if isinstance(arg, pd.DataFrame):
                    df_idx = idx
                    break
            
            if df_idx == -1:
                return func(*args, **kwargs)

            # Standardize columns to lowercase
            args[df_idx] = args[df_idx].rename(columns={c: c.lower() for c in args[df_idx].columns})

            inputs = {
                "o": "open",
                "h": "high",
                "l": "low",
                "c": kwargs.get("column", "close").lower(),
                "v": "volume",
            }

            if inputs["c"] != "close":
                kwargs["column"] = inputs["c"]

            for l in input_:
                if inputs[l] not in args[df_idx].columns:
                    raise LookupError(
                        'Must have a dataframe column named "{0}"'.format(inputs[l])
                    )

            return func(*args, **kwargs)

        return wrap

    return dfcheck


def apply(decorator):
    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls
    return decorate


@apply(inputvalidator(input_="ohlc"))
class smc:
    __version__ = "0.0.27"

    @classmethod
    def fvg(cls, ohlc: DataFrame, join_consecutive=False) -> DataFrame:
        """
        FVG - Fair Value Gap
        """
        fvg = np.where(
            (
                (ohlc["high"].shift(1) < ohlc["low"].shift(-1))
                & (ohlc["close"] > ohlc["open"])
            )
            | (
                (ohlc["low"].shift(1) > ohlc["high"].shift(-1))
                & (ohlc["close"] < ohlc["open"])
            ),
            np.where(ohlc["close"] > ohlc["open"], 1, -1),
            np.nan,
        )

        top = np.where(
            ~np.isnan(fvg),
            np.where(
                ohlc["close"] > ohlc["open"],
                ohlc["low"].shift(-1),
                ohlc["low"].shift(1),
            ),
            np.nan,
        )

        bottom = np.where(
            ~np.isnan(fvg),
            np.where(
                ohlc["close"] > ohlc["open"],
                ohlc["high"].shift(1),
                ohlc["high"].shift(-1),
            ),
            np.nan,
        )

        if join_consecutive:
            for i in range(len(fvg) - 1):
                if fvg[i] == fvg[i + 1]:
                    top[i + 1] = max(top[i], top[i + 1])
                    bottom[i + 1] = min(bottom[i], bottom[i + 1])
                    fvg[i] = top[i] = bottom[i] = np.nan

        mitigated_index = np.zeros(len(ohlc), dtype=np.int32)
        for i in np.where(~np.isnan(fvg))[0]:
            mask = np.zeros(len(ohlc), dtype=np.bool_)
            if fvg[i] == 1:
                mask = ohlc["low"].iloc[i + 2 :] <= top[i]
            elif fvg[i] == -1:
                mask = ohlc["high"].iloc[i + 2 :] >= bottom[i]
            if np.any(mask):
                j = np.argmax(mask) + i + 2
                mitigated_index[i] = j

        mitigated_index = np.where(np.isnan(fvg), np.nan, mitigated_index)

        res = pd.concat(
            [
                pd.Series(fvg, index=ohlc.index, name="fvg"),
                pd.Series(top, index=ohlc.index, name="fvg_top"),
                pd.Series(bottom, index=ohlc.index, name="fvg_bottom"),
                pd.Series(mitigated_index, index=ohlc.index, name="fvg_mitigated_index"),
            ],
            axis=1,
        )
        return pd.concat([ohlc, res], axis=1)

    @classmethod
    def swing_highs_lows(cls, ohlc: DataFrame, swing_length: int = 50) -> DataFrame:
        """
        Swing Highs and Lows
        """
        swing_length_val = swing_length * 2
        swing_highs_lows = np.where(
            ohlc["high"]
            == ohlc["high"].shift(-(swing_length_val // 2)).rolling(swing_length_val).max(),
            1,
            np.where(
                ohlc["low"]
                == ohlc["low"].shift(-(swing_length_val // 2)).rolling(swing_length_val).min(),
                -1,
                np.nan,
            ),
        )

        while True:
            positions = np.where(~np.isnan(swing_highs_lows))[0]
            if len(positions) < 2:
                break

            current = swing_highs_lows[positions[:-1]]
            next_val = swing_highs_lows[positions[1:]]

            highs = ohlc["high"].iloc[positions[:-1]].values
            lows = ohlc["low"].iloc[positions[:-1]].values
            next_highs = ohlc["high"].iloc[positions[1:]].values
            next_lows = ohlc["low"].iloc[positions[1:]].values

            index_to_remove = np.zeros(len(positions), dtype=bool)
            consecutive_highs = (current == 1) & (next_val == 1)
            index_to_remove[:-1] |= consecutive_highs & (highs < next_highs)
            index_to_remove[1:] |= consecutive_highs & (highs >= next_highs)

            consecutive_lows = (current == -1) & (next_val == -1)
            index_to_remove[:-1] |= consecutive_lows & (lows > next_lows)
            index_to_remove[1:] |= consecutive_lows & (lows <= next_lows)

            if not index_to_remove.any():
                break
            swing_highs_lows[positions[index_to_remove]] = np.nan

        positions = np.where(~np.isnan(swing_highs_lows))[0]
        if len(positions) > 0:
            if swing_highs_lows[positions[0]] == 1:
                swing_highs_lows[0] = -1
            if swing_highs_lows[positions[0]] == -1:
                swing_highs_lows[0] = 1
            if swing_highs_lows[positions[-1]] == -1:
                swing_highs_lows[-1] = 1
            if swing_highs_lows[positions[-1]] == 1:
                swing_highs_lows[-1] = -1

        level = np.where(
            ~np.isnan(swing_highs_lows),
            np.where(swing_highs_lows == 1, ohlc["high"], ohlc["low"]),
            np.nan,
        )

        res = pd.concat(
            [
                pd.Series(swing_highs_lows, index=ohlc.index, name="shl"),
                pd.Series(level, index=ohlc.index, name="shl_level"),
            ],
            axis=1,
        )
        return pd.concat([ohlc, res], axis=1)

    @classmethod
    def bos_choch(
        cls, ohlc: DataFrame, swing_length: int = 50, close_break: bool = True
    ) -> DataFrame:
        """
        BOS - Break of Structure
        CHoCH - Change of Character
        """
        # First get swing highs lows
        shl_df = cls.swing_highs_lows(ohlc, swing_length=swing_length)
        shl_hl = shl_df["shl"].values
        shl_level = shl_df["shl_level"].values

        level_order = []
        highs_lows_order = []
        bos = np.zeros(len(ohlc), dtype=np.int32)
        choch = np.zeros(len(ohlc), dtype=np.int32)
        level_arr = np.zeros(len(ohlc), dtype=np.float32)
        last_positions = []

        for i in range(len(shl_hl)):
            if not np.isnan(shl_hl[i]):
                level_order.append(shl_level[i])
                highs_lows_order.append(shl_hl[i])
                if len(level_order) >= 4:
                    # bullish bos
                    bos[last_positions[-2]] = (
                        1
                        if (
                            np.all(highs_lows_order[-4:] == [-1, 1, -1, 1])
                            and np.all(
                                level_order[-4]
                                < level_order[-2]
                                < level_order[-3]
                                < level_order[-1]
                            )
                        )
                        else 0
                    )
                    level_arr[last_positions[-2]] = (
                        level_order[-3] if bos[last_positions[-2]] != 0 else 0
                    )

                    # bearish bos
                    bos[last_positions[-2]] = (
                        -1
                        if (
                            np.all(highs_lows_order[-4:] == [1, -1, 1, -1])
                            and np.all(
                                level_order[-4]
                                > level_order[-2]
                                > level_order[-3]
                                > level_order[-1]
                            )
                        )
                        else bos[last_positions[-2]]
                    )
                    level_arr[last_positions[-2]] = (
                        level_order[-3] if bos[last_positions[-2]] != 0 else 0
                    )

                    # bullish choch
                    choch[last_positions[-2]] = (
                        1
                        if (
                            np.all(highs_lows_order[-4:] == [-1, 1, -1, 1])
                            and np.all(
                                level_order[-1]
                                > level_order[-3]
                                > level_order[-4]
                                > level_order[-2]
                            )
                        )
                        else 0
                    )
                    level_arr[last_positions[-2]] = (
                        level_order[-3]
                        if choch[last_positions[-2]] != 0
                        else level_arr[last_positions[-2]]
                    )

                    # bearish choch
                    choch[last_positions[-2]] = (
                        -1
                        if (
                            np.all(highs_lows_order[-4:] == [1, -1, 1, -1])
                            and np.all(
                                level_order[-1]
                                < level_order[-3]
                                < level_order[-4]
                                < level_order[-2]
                            )
                        )
                        else choch[last_positions[-2]]
                    )
                    level_arr[last_positions[-2]] = (
                        level_order[-3]
                        if choch[last_positions[-2]] != 0
                        else level_arr[last_positions[-2]]
                    )
                last_positions.append(i)

        broken = np.zeros(len(ohlc), dtype=np.int32)
        for i in np.where(np.logical_or(bos != 0, choch != 0))[0]:
            mask = np.zeros(len(ohlc), dtype=np.bool_)
            if bos[i] == 1 or choch[i] == 1:
                mask = ohlc["close" if close_break else "high"].iloc[i + 2 :] > level_arr[i]
            elif bos[i] == -1 or choch[i] == -1:
                mask = ohlc["close" if close_break else "low"].iloc[i + 2 :] < level_arr[i]
            if np.any(mask):
                j = np.argmax(mask) + i + 2
                broken[i] = j
                for k in np.where(np.logical_or(bos != 0, choch != 0))[0]:
                    if k < i and broken[k] >= j:
                        bos[k] = 0
                        choch[k] = 0
                        level_arr[k] = 0

        for i in np.where(np.logical_and(np.logical_or(bos != 0, choch != 0), broken == 0))[0]:
            bos[i] = 0
            choch[i] = 0
            level_arr[i] = 0

        bos = np.where(bos != 0, bos, np.nan)
        choch = np.where(choch != 0, choch, np.nan)
        level_arr = np.where(level_arr != 0, level_arr, np.nan)
        broken = np.where(broken != 0, broken, np.nan)

        res = pd.concat([
            pd.Series(bos, index=ohlc.index, name="bos"),
            pd.Series(choch, index=ohlc.index, name="choch"),
            pd.Series(level_arr, index=ohlc.index, name="structure_level"),
            pd.Series(broken, index=ohlc.index, name="structure_broken_index"),
        ], axis=1)
        return pd.concat([ohlc, res], axis=1)

    @classmethod
    def ob(
        cls,
        ohlc: DataFrame,
        swing_length: int = 50,
        close_mitigation: bool = False,
    ) -> DataFrame:
        """
        OB - Order Blocks
        """
        shl_df = cls.swing_highs_lows(ohlc, swing_length=swing_length)
        ohlc_len = len(ohlc)
        _open = ohlc["open"].values
        _high = ohlc["high"].values
        _low = ohlc["low"].values
        _close = ohlc["close"].values
        _volume = ohlc["volume"].values
        swing_hl = shl_df["shl"].values

        crossed = np.full(ohlc_len, False, dtype=bool)
        ob_arr = np.zeros(ohlc_len, dtype=np.int32)
        top_arr = np.zeros(ohlc_len, dtype=np.float32)
        bottom_arr = np.zeros(ohlc_len, dtype=np.float32)
        ob_volume = np.zeros(ohlc_len, dtype=np.float32)
        percentage = np.zeros(ohlc_len, dtype=np.float32)
        mitigated_index = np.zeros(ohlc_len, dtype=np.int32)
        breaker = np.full(ohlc_len, False, dtype=bool)

        swing_high_indices = np.flatnonzero(swing_hl == 1)
        swing_low_indices = np.flatnonzero(swing_hl == -1)

        active_bullish = []
        for i in range(ohlc_len):
            for idx in active_bullish.copy():
                if breaker[idx]:
                    if _high[i] > top_arr[idx]:
                        ob_arr[idx] = 0; top_arr[idx] = 0.0; bottom_arr[idx] = 0.0
                        active_bullish.remove(idx)
                else:
                    if ((not close_mitigation and _low[i] < bottom_arr[idx])
                        or (close_mitigation and min(_open[i], _close[i]) < bottom_arr[idx])):
                        breaker[idx] = True; mitigated_index[idx] = i

            pos = np.searchsorted(swing_high_indices, i)
            last_top_index = swing_high_indices[pos - 1] if pos > 0 else None
            if last_top_index is not None and _close[i] > _high[last_top_index] and not crossed[last_top_index]:
                crossed[last_top_index] = True
                obIndex = i - 1
                obBtm = _low[obIndex]; obTop = _high[obIndex]
                if i - last_top_index > 1:
                    start = last_top_index + 1
                    segment = _low[start:i]
                    if segment.size:
                        min_idx = start + np.argmin(segment)
                        obBtm = _low[min_idx]; obTop = _high[min_idx]; obIndex = min_idx
                ob_arr[obIndex] = 1; top_arr[obIndex] = obTop; bottom_arr[obIndex] = obBtm
                vol_sum = _volume[i] + (_volume[i-1] if i>=1 else 0) + (_volume[i-2] if i>=2 else 0)
                ob_volume[obIndex] = vol_sum
                active_bullish.append(obIndex)

        active_bearish = []
        for i in range(ohlc_len):
            for idx in active_bearish.copy():
                if breaker[idx]:
                    if _low[i] < bottom_arr[idx]:
                        ob_arr[idx] = 0; active_bearish.remove(idx)
                else:
                    if ((not close_mitigation and _high[i] > top_arr[idx])
                        or (close_mitigation and max(_open[i], _close[i]) > top_arr[idx])):
                        breaker[idx] = True; mitigated_index[idx] = i

            pos = np.searchsorted(swing_low_indices, i)
            last_btm_index = swing_low_indices[pos - 1] if pos > 0 else None
            if last_btm_index is not None and _close[i] < _low[last_btm_index] and not crossed[last_btm_index]:
                crossed[last_btm_index] = True
                obIndex = i - 1
                obTop = _high[obIndex]; obBtm = _low[obIndex]
                if i - last_btm_index > 1:
                    start = last_btm_index + 1
                    segment = _high[start:i]
                    if segment.size:
                        max_idx = start + np.argmax(segment)
                        obTop = _high[max_idx]; obBtm = _low[max_idx]; obIndex = max_idx
                ob_arr[obIndex] = -1; top_arr[obIndex] = obTop; bottom_arr[obIndex] = obBtm
                active_bearish.append(obIndex)

        res = pd.concat([
            pd.Series(np.where(ob_arr != 0, ob_arr, np.nan), index=ohlc.index, name="ob"),
            pd.Series(np.where(ob_arr != 0, top_arr, np.nan), index=ohlc.index, name="ob_top"),
            pd.Series(np.where(ob_arr != 0, bottom_arr, np.nan), index=ohlc.index, name="ob_bottom"),
            pd.Series(np.where(ob_arr != 0, mitigated_index, np.nan), index=ohlc.index, name="ob_mitigated_index"),
        ], axis=1)
        return pd.concat([ohlc, res], axis=1)

    @classmethod
    def previous_high_low(cls, ohlc: DataFrame, timeframe: str = "1D") -> DataFrame:
        """
        Previous High Low
        """
        ohlc = ohlc.copy()
        ohlc.index = pd.to_datetime(ohlc.index)
        resampled = ohlc.resample(timeframe).agg({"high": "max", "low": "min"}).shift(1)
        
        # Reindex to match original ohlc
        phl = resampled.reindex(ohlc.index, method='ffill')
        phl.columns = ["previous_high", "previous_low"]
        
        # Broken high/low
        phl["broken_high"] = np.where(ohlc["high"] > phl["previous_high"], 1, 0)
        phl["broken_low"] = np.where(ohlc["low"] < phl["previous_low"], 1, 0)
        
        return pd.concat([ohlc, phl], axis=1)

def fvg(ohlc: DataFrame, join_consecutive=False) -> DataFrame:
    return smc.fvg(ohlc, join_consecutive=join_consecutive)

def swing_highs_lows(ohlc: DataFrame, swing_length: int = 50) -> DataFrame:
    return smc.swing_highs_lows(ohlc, swing_length=swing_length)

def bos_choch(ohlc: DataFrame, swing_length: int = 50, close_break: bool = True) -> DataFrame:
    return smc.bos_choch(ohlc, swing_length=swing_length, close_break=close_break)

def ob(ohlc: DataFrame, swing_length: int = 50, close_mitigation: bool = False) -> DataFrame:
    return smc.ob(ohlc, swing_length=swing_length, close_mitigation=close_mitigation)

def previous_high_low(ohlc: DataFrame, timeframe: str = "1D") -> DataFrame:
    return smc.previous_high_low(ohlc, timeframe=timeframe)
