def simple_wind_power(v,capacity_kw,cut_in=3,rated=12,cut_out=25):
    if v<cut_in or v>=cut_out:return 0
    if v>=rated:return capacity_kw
    return capacity_kw*((v**3-cut_in**3)/(rated**3-cut_in**3))
