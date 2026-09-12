def next_soc(soc,charge_kw,discharge_kw,capacity_kwh,charge_eff=.95,discharge_eff=.95): return soc+(charge_eff*charge_kw-discharge_kw/discharge_eff)/capacity_kwh
