def diesel_fuel(power_kw,fuel_l_per_kwh): return power_kw*fuel_l_per_kwh
def diesel_emissions(power_kw,fuel_l_per_kwh,co2_kg_per_l): return diesel_fuel(power_kw,fuel_l_per_kwh)*co2_kg_per_l
