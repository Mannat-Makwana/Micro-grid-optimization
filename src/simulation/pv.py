def pv_power_from_irradiance(irradiance_w_m2,capacity_kw): return max(0,min(capacity_kw,capacity_kw*max(0,irradiance_w_m2)/1000))
