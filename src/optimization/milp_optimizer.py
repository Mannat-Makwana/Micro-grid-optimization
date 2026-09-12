import yaml,pulp

def optimize_dispatch(load,solar_available,wind_available,soc_initial,config_path='config/microgrid_config.yaml'):
    c=yaml.safe_load(open(config_path)); b=c['battery']; d=c['diesel']; n=len(load); m=pulp.LpProblem('MicrogridDispatch',pulp.LpMinimize)
    S=[pulp.LpVariable(f'S{t}',0,solar_available[t]) for t in range(n)]; W=[pulp.LpVariable(f'W{t}',0,wind_available[t]) for t in range(n)]; C=[pulp.LpVariable(f'C{t}',0,b['max_charge_kw']) for t in range(n)]; D=[pulp.LpVariable(f'D{t}',0,b['max_discharge_kw']) for t in range(n)]; G=[pulp.LpVariable(f'G{t}',0,d['capacity_kw']) for t in range(n)]; U=[pulp.LpVariable(f'U{t}',cat='Binary') for t in range(n)]; soc=[pulp.LpVariable(f'soc{t}',b['min_soc'],b['max_soc']) for t in range(n+1)]
    m+=soc[0]==soc_initial
    for t in range(n):
        m+=S[t]+W[t]+D[t]+G[t]-C[t]==load[t];m+=G[t]>=d['minimum_output_kw']*U[t];m+=G[t]<=d['capacity_kw']*U[t];m+=soc[t+1]==soc[t]+(b['charge_efficiency']*C[t]-D[t]/b['discharge_efficiency'])/b['capacity_kwh']
    m+=pulp.lpSum(G[t]*d['fuel_l_per_kwh']*d['fuel_price_inr_per_l'] for t in range(n))+c['optimization']['emission_weight']*pulp.lpSum(G[t]*d['fuel_l_per_kwh']*d['co2_kg_per_l'] for t in range(n));status=m.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status]!='Optimal':raise RuntimeError(pulp.LpStatus[status])
    return {'solar_kW':[x.value() for x in S],'wind_kW':[x.value() for x in W],'battery_charge_kW':[x.value() for x in C],'battery_discharge_kW':[x.value() for x in D],'diesel_kW':[x.value() for x in G],'soc':[x.value() for x in soc]}
