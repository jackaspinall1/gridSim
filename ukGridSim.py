import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib.widgets import Slider, RadioButtons, TextBox

# --- 1. DATA & ROADMAP ---
# Based on NESO FES 2024 and Clean Power 2030 Action Plan
roadmap_milestones = {
    'Year': [2025, 2030, 2035],
    'Nuclear': [5.88, 6.5, 11.0],           # 2030: Hinkley C operational, 2035: + Sizewell C
    'Solar': [15.7, 45.0, 62.0],            # NESO targets: 47 GW (2030), 62 GW (2035)
    'Hydro_RunOfRiver': [1.47, 1.5, 1.5],
    'Wind_Offshore': [15.5, 45.0, 75.0],    # NESO targets: 43-50 GW (2030), 68-86 GW (2035)
    'Wind_Onshore': [15.2, 27.0, 36.0],     # NESO targets: 27 GW (2030), 35-37 GW (2035)
    'Biomass': [4.8, 4.0, 3.5],
    'Interconnectors': [10.8, 18.0, 22.0],
    'Gas_CCGT': [30.5, 32.0, 9.0],          # Combined Cycle Gas Turbines - major retirement by 2035
    'Gas_OCGT': [2.4, 2.5, 2.5],            # Open Cycle Gas Turbines - peaking plants
    'Gas_Oil': [0.1, 0.5, 0.5],             # Oil peaker plants for backup
    'Storage_Power': [10.8, 25.0, 45.0],    # Battery + pumped hydro power capacity
    'Storage_Energy': [42.5, 120.0, 250.0]  # Battery + pumped hydro energy capacity (GWh)
}

df_milestones = pd.DataFrame(roadmap_milestones).set_index('Year')
years_range = np.arange(2025, 2036)
df_fleet = df_milestones.reindex(years_range).interpolate()

weather_scenarios = {
    'Dunkelflaute': {'Wind_Off': 0.10, 'Wind_On': 0.05, 'Solar_Peak': 0.10, 'Demand_Mult': 1.0, 'Solar_Start': 8, 'Solar_Hours': 8, 'Interconnectors': 0.1},  # Winter: 8am-4pm (8 hours), imports from EU
    'Summer Windy': {'Wind_Off': 0.85, 'Wind_On': 0.75, 'Solar_Peak': 0.80, 'Demand_Mult': 0.7, 'Solar_Start': 5, 'Solar_Hours': 16, 'Interconnectors': 0.0}  # Summer: 5am-9pm (16 hours), exporting to EU
}

# --- COMPONENT-BASED DEMAND MODEL ---
# Seasonal demand profiles (normalized 0-1, scaled by component capacities)
# Based on National Grid FES 2023, UK government projections
seasonal_profiles = {
    'winter': {
        # Traditional demand pattern, higher evenings
        'baseload': np.array([
            0.69, 0.67, 0.66, 0.65, 0.68, 0.80, 0.99, 1.00, 0.98, 0.95,  # 0-9h: Night→Morning peak
            0.93, 0.90, 0.88, 0.87, 0.88, 0.92, 0.97, 1.00, 0.98, 0.94,  # 10-19h: Day→Evening peak
            0.88, 0.78, 0.73, 0.70                                        # 20-23h: Evening decline
        ]),
        # Strong evening peak (heating demand), morning peak, temperature-driven
        'heat_pump': np.array([
            0.60, 0.55, 0.52, 0.50, 0.55, 0.70, 0.85, 0.90, 0.80, 0.70,  # 0-9h: Morning ramp
            0.65, 0.60, 0.55, 0.55, 0.60, 0.75, 0.95, 1.00, 1.00, 0.95,  # 10-19h: Evening peak (17-19h)
            0.85, 0.75, 0.68, 0.63                                        # 20-23h: Late evening
        ]),
        # Evening peak when people get home from work
        'ev_charging': np.array([
            0.15, 0.12, 0.10, 0.08, 0.08, 0.10, 0.20, 0.35, 0.25, 0.15,  # 0-9h: Overnight taper
            0.12, 0.10, 0.10, 0.12, 0.15, 0.25, 0.50, 0.75, 1.00, 0.95,  # 10-19h: Evening ramp (18-19h)
            0.80, 0.60, 0.40, 0.25                                        # 20-23h: Late charging
        ]),
        # Near-zero in winter Dunkelflaute (8h daylight, cloudy)
        'solar_btm': np.array([
            0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.05, 0.15,  # 0-9h: Dawn
            0.25, 0.30, 0.30, 0.28, 0.22, 0.12, 0.03, 0.00, 0.00, 0.00,  # 10-19h: Weak midday
            0.00, 0.00, 0.00, 0.00                                        # 20-23h: Night
        ])
    },
    'summer': {
        # Lower overall, flatter profile
        'baseload': np.array([
            0.63, 0.61, 0.60, 0.59, 0.61, 0.68, 0.78, 0.85, 0.88, 0.90,  # 0-9h: Gentler morning
            0.91, 0.92, 0.90, 0.88, 0.87, 0.88, 0.92, 0.95, 0.93, 0.88,  # 10-19h: Lower evening peak
            0.82, 0.75, 0.70, 0.66                                        # 20-23h: Evening
        ]),
        # Much lower (cooling only, high COP)
        'heat_pump': np.array([
            0.10, 0.08, 0.08, 0.08, 0.08, 0.10, 0.12, 0.15, 0.18, 0.22,  # 0-9h: Minimal
            0.25, 0.28, 0.30, 0.32, 0.33, 0.33, 0.32, 0.30, 0.28, 0.25,  # 10-19h: Afternoon cooling
            0.20, 0.15, 0.12, 0.10                                        # 20-23h: Evening
        ]),
        # Similar pattern, slight reduction (better battery efficiency)
        'ev_charging': np.array([
            0.12, 0.10, 0.08, 0.07, 0.07, 0.08, 0.15, 0.28, 0.22, 0.13,  # 0-9h: Overnight
            0.10, 0.09, 0.09, 0.10, 0.12, 0.20, 0.45, 0.70, 0.95, 0.90,  # 10-19h: Evening peak
            0.75, 0.55, 0.35, 0.20                                        # 20-23h: Late charging
        ]),
        # Strong midday generation (16h daylight, 80% solar)
        'solar_btm': np.array([
            0.00, 0.00, 0.00, 0.00, 0.00, 0.05, 0.20, 0.40, 0.60, 0.75,  # 0-9h: Sunrise
            0.85, 0.92, 0.95, 0.92, 0.85, 0.75, 0.60, 0.40, 0.20, 0.08,  # 10-19h: Midday peak
            0.02, 0.00, 0.00, 0.00                                        # 20-23h: Sunset/night
        ])
    }
}

# Shoulder season (Spring/Autumn) - intermediate between winter and summer
seasonal_profiles['shoulder'] = {
    'baseload': (seasonal_profiles['winter']['baseload'] * 0.6 + seasonal_profiles['summer']['baseload'] * 0.4),
    'heat_pump': (seasonal_profiles['winter']['heat_pump'] * 0.5 + seasonal_profiles['summer']['heat_pump'] * 0.5),
    'ev_charging': (seasonal_profiles['winter']['ev_charging'] * 0.5 + seasonal_profiles['summer']['ev_charging'] * 0.5),
    'solar_btm': (seasonal_profiles['winter']['solar_btm'] * 0.3 + seasonal_profiles['summer']['solar_btm'] * 0.7)
}

# Component growth trajectories (GW peak capacity)
# Based on National Grid FES 2023 "Leading The Way" scenario
component_milestones = {
    'Year': [2025, 2030, 2035],
    'Baseload_Peak': [40.0, 42.0, 44.0],        # Slow growth: existing non-electrified demand
    'HeatPump_Peak': [2.0, 8.0, 18.0],          # Rapid growth: 1M→6M→13M units @ ~1.5kW avg
    'EV_Peak': [3.0, 10.0, 20.0],               # Fast growth: 2M→8M→15M EVs @ ~7kW charging
    'SolarBTM_Capacity': [5.0, 10.0, 15.0]      # Steady growth: rooftop solar capacity
}

df_demand_components = pd.DataFrame(component_milestones).set_index('Year')
df_demand_components = df_demand_components.reindex(years_range).interpolate()

# Weather-to-season mapping
weather_to_season = {
    'Dunkelflaute': 'winter',
    'Summer Windy': 'summer'
}

hours = np.arange(96)

# --- DEMAND CALCULATION FUNCTIONS ---
def get_component_demand_profiles(year, season):
    """
    Calculate hourly demand profiles for each component based on year and season.

    Args:
        year: Simulation year (2025-2035)
        season: 'winter', 'summer', or 'shoulder'

    Returns:
        dict: {component_name: np.array(24)} - 24-hour demand profiles in GW
    """
    # Get component peak capacities for this year (interpolated)
    components = df_demand_components.loc[year]

    # Get seasonal normalized profiles
    profiles = seasonal_profiles[season]

    # Scale normalized profiles by component peak capacities
    demand_profiles = {
        'baseload': profiles['baseload'] * components['Baseload_Peak'],
        'heat_pump': profiles['heat_pump'] * components['HeatPump_Peak'],
        'ev_charging': profiles['ev_charging'] * components['EV_Peak'],
        'solar_btm': profiles['solar_btm'] * components['SolarBTM_Capacity']
    }

    return demand_profiles

def aggregate_component_demands(component_profiles):
    """
    Aggregate component demands into total demand profile.

    Args:
        component_profiles: dict of {component: np.array(24)}

    Returns:
        np.array(24): Total hourly demand in GW
    """
    # Start with baseload
    total_demand = component_profiles['baseload'].copy()

    # Add heat pumps
    total_demand += component_profiles['heat_pump']

    # Add EV charging
    total_demand += component_profiles['ev_charging']

    # Subtract behind-meter solar (reduces apparent demand)
    total_demand -= component_profiles['solar_btm']

    # Ensure demand doesn't go negative
    total_demand = np.maximum(total_demand, 0)

    return total_demand

def compute_demand_array(year, weather_key):
    """
    Compute 96-hour demand array with component-based model.

    Args:
        year: Simulation year (2025-2035)
        weather_key: 'Dunkelflaute' or 'Summer Windy'

    Returns:
        np.array(96): Hourly demand in GW for 96-hour simulation
    """
    # Map weather to season
    season = weather_to_season[weather_key]

    # Get component profiles for this year and season
    component_profiles = get_component_demand_profiles(year, season)

    # Aggregate into 24-hour total demand profile
    daily_demand = aggregate_component_demands(component_profiles)

    # Tile to create 96-hour profile
    demand_96h = np.tile(daily_demand, 4)

    return demand_96h

# --- 2. SIMULATION ENGINE ---
def run_sim(year, weather_key, cap_override=None, lf_override=None, storage_override=None):
    if cap_override is None:
        cap = df_fleet.loc[year].to_dict()
    else:
        cap = cap_override.copy()

    w = weather_scenarios[weather_key]

    # Component-based demand calculation
    demand = compute_demand_array(year, weather_key)

    if storage_override is None:
        # Use default split from roadmap values
        storage_assets = {
            'Pumped_Hydro': {'power_cap': cap['Storage_Power']*0.3, 'charge_cap': cap['Storage_Power']*0.25, 'energy_cap': cap['Storage_Energy']*0.7, 'eff': 0.75},
            'Batteries': {'power_cap': cap['Storage_Power']*0.7, 'charge_cap': cap['Storage_Power']*0.7, 'energy_cap': cap['Storage_Energy']*0.3, 'eff': 0.85}
        }
    else:
        # Use individual storage values from textboxes
        storage_assets = {
            'Pumped_Hydro': {
                'power_cap': storage_override.get('Pumped_Hydro', {}).get('power', 0),
                'charge_cap': storage_override.get('Pumped_Hydro', {}).get('power', 0) * 0.83,  # Charge ~83% of discharge
                'energy_cap': storage_override.get('Pumped_Hydro', {}).get('energy', 0),
                'eff': 0.75
            },
            'Batteries': {
                'power_cap': storage_override.get('Batteries', {}).get('power', 0),
                'charge_cap': storage_override.get('Batteries', {}).get('power', 0),  # Symmetric charge/discharge
                'energy_cap': storage_override.get('Batteries', {}).get('energy', 0),
                'eff': 0.85
            }
        }

    # Start with full storage for simulation
    soc = {name: asset['energy_cap'] for name, asset in storage_assets.items()}
    history = []
    soc_history = {name: [] for name in storage_assets}
    residual_excess_history = []
    generation_excess_history = []  # Generation-only excess (excludes storage)
    renewable_curtailment_history = []
    wasted_energy_gwh = 0

    # Define renewable sources for tracking curtailment
    renewable_sources = ['Solar', 'Wind_Offshore', 'Wind_Onshore', 'Hydro_RunOfRiver']

    if lf_override is None:
        lfs = {'Nuclear': 0.90, 'Solar_Peak': w['Solar_Peak'], 'Hydro_RunOfRiver': 0.80, 'Wind_Offshore': w['Wind_Off'], 'Wind_Onshore': w['Wind_On'], 'Biomass': 0.95, 'Interconnectors': w['Interconnectors'], 'Gas_CCGT': 1.0, 'Gas_OCGT': 1.0, 'Gas_Oil': 1.0}
    else:
        lfs = lf_override.copy()

    for h in hours:
        hr_of_day = h % 24
        # Solar follows sine wave during day - duration depends on weather (winter: 8h, summer: 16h)
        solar_start = w['Solar_Start']
        solar_hours = w['Solar_Hours']
        solar_output = cap['Solar'] * lfs['Solar_Peak'] * np.maximum(0, np.sin((hr_of_day - solar_start) * np.pi / solar_hours))

        gen_pot = {s: (solar_output if s=='Solar' else cap[s]*lfs[s]) for s in cap if s not in ['Storage_Power', 'Storage_Energy']}

        total_pot = sum(gen_pot.values())
        physical_delta = total_pot - demand[h]
        
        storage_dispatch = {'Pumped_Hydro': 0, 'Batteries': 0}
        actual_gen = {s: 0 for s in gen_pot}
        priority = ['Nuclear', 'Solar', 'Hydro_RunOfRiver', 'Wind_Offshore', 'Wind_Onshore', 'Biomass', 'Interconnectors', 'Gas_CCGT', 'Gas_OCGT', 'Gas_Oil']
        
        total_charged_this_hour = 0
        total_discharged_this_hour = 0

        if physical_delta >= 0: # SURPLUS
            rem_demand = demand[h]
            for s in priority:
                used = min(rem_demand, gen_pot[s])
                actual_gen[s] = used
                rem_demand -= used

            surplus = physical_delta
            total_charge_cap = sum(a['charge_cap'] for a in storage_assets.values())
            
            for name, asset in storage_assets.items():
                share = asset['charge_cap'] / total_charge_cap if total_charge_cap > 0 else 0
                # Calculate how much can be absorbed
                charge = min(surplus * share, asset['charge_cap'], (asset['energy_cap'] - soc[name])/asset['eff'])
                soc[name] += (charge * asset['eff'])
                total_charged_this_hour += charge
                
                # Update stackplot visuals to show generation used for charging
                c_add = charge
                for s in reversed(priority):
                    space = gen_pot[s] - actual_gen[s]
                    added = min(c_add, space)
                    actual_gen[s] += added
                    c_add -= added
            
            wasted_energy_gwh += max(0, surplus - total_charged_this_hour)
            # Residual Excess is what we HAD to throw away (curtail)
            residual_excess = physical_delta - total_charged_this_hour

            # Calculate renewable curtailment specifically
            # Curtailed energy comes proportionally from all unused generation
            total_unused = sum(gen_pot[s] - actual_gen[s] for s in gen_pot)
            if total_unused > 0:
                renewable_unused = sum(gen_pot[s] - actual_gen[s] for s in renewable_sources if s in gen_pot)
                renewable_curtailment = residual_excess * (renewable_unused / total_unused) if residual_excess > 0 else 0
            else:
                renewable_curtailment = 0

        else: # DEFICIT
            for s in priority: actual_gen[s] = gen_pot[s]
            deficit = abs(physical_delta)
            total_dis_cap = sum(a['power_cap'] for a in storage_assets.values())

            for name, asset in storage_assets.items():
                share = asset['power_cap'] / total_dis_cap if total_dis_cap > 0 else 0
                dis = min(deficit * share, asset['power_cap'], soc[name])
                soc[name] -= dis
                storage_dispatch[name] = dis
                total_discharged_this_hour += dis

            # Residual Excess is the remaining gap (needs gas or load shedding)
            residual_excess = physical_delta + total_discharged_this_hour
            renewable_curtailment = 0  # No curtailment in deficit

        residual_excess_history.append(residual_excess)
        generation_excess_history.append(physical_delta)  # Generation-only excess (no storage)
        renewable_curtailment_history.append(renewable_curtailment)
        for name in storage_assets: soc_history[name].append(soc[name])
        actual_gen.update(storage_dispatch)
        history.append(actual_gen)

    total_storage_energy = sum(asset['energy_cap'] for asset in storage_assets.values())
    renewable_wasted_gwh = sum(renewable_curtailment_history)  # Total renewable energy curtailed
    return pd.DataFrame(history), soc_history, demand, total_storage_energy, residual_excess_history, renewable_wasted_gwh, storage_assets, renewable_curtailment_history, generation_excess_history

# --- 3. PLOTTING SETUP ---
fig = plt.figure(figsize=(20, 11))
gs = fig.add_gridspec(3, 2, width_ratios=[2.2, 1], height_ratios=[3, 1, 1],
                      left=0.05, right=0.65, bottom=0.10, top=0.95,
                      hspace=0.25, wspace=0.12)

# Left side: graphs (occupy left ~65% of figure)
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)
ax3 = fig.add_subplot(gs[2, 0], sharex=ax1)

# Right side: control panel (will use absolute positioning from x=0.68 onwards)
ax_right = fig.add_axes([0.68, 0.10, 0.30, 0.85])
ax_right.axis('off')

# Year slider at bottom left
ax_slider = plt.axes([0.10, 0.03, 0.35, 0.02])
slider = Slider(ax_slider, 'Year', 2025, 2035, valinit=2025, valstep=1)

# Weather radio buttons - positioned in right panel below color key
ax_radio = plt.axes([0.70, 0.54, 0.12, 0.08])
radio = RadioButtons(ax_radio, ('Dunkelflaute', 'Summer Windy'))

# Create Excel-like grid tables for parameters
textboxes = {}

# Define generation parameter rows: (label, cap_param, lf_param)
gen_rows = [
    ('Nuclear', 'Nuclear', 'Nuclear'),
    ('Solar', 'Solar', 'Solar_Peak'),
    ('Hydro RoR', 'Hydro_RunOfRiver', 'Hydro_RunOfRiver'),
    ('Wind Offshore', 'Wind_Offshore', 'Wind_Offshore'),
    ('Wind Onshore', 'Wind_Onshore', 'Wind_Onshore'),
    ('Biomass', 'Biomass', 'Biomass'),
    ('Interconnect', 'Interconnectors', 'Interconnectors'),
    ('Gas CCGT', 'Gas_CCGT', 'Gas_CCGT'),
    ('Gas OCGT', 'Gas_OCGT', 'Gas_OCGT'),
    ('Oil Peakers', 'Gas_Oil', 'Gas_Oil'),
]

# Define storage rows: (label, storage_type)
storage_rows = [
    ('Pumped Hydro', 'Pumped_Hydro'),
    ('Batteries', 'Batteries'),
]

# Grid table positions (in right panel, below weather selector)
# Right panel spans from x=0.68 to x=0.98
gen_table_top = 0.43
storage_table_top = 0.12  # Consistent spacing with generation table
table_left = 0.77  # Start of first data column
row_height = 0.024  # Row spacing
col_width = 0.09   # Column width
col_gap = 0.01     # Gap between columns
textbox_height = 0.018  # Height of textboxes

# Create GENERATION table textboxes
for idx, (label, cap_param, lf_param) in enumerate(gen_rows):
    y_pos = gen_table_top - idx * row_height

    # Capacity textbox
    ax_cap = plt.axes([table_left, y_pos, col_width, textbox_height], facecolor='white')
    tb_cap = TextBox(ax_cap, '', initial='0.0', textalignment='center')
    textboxes[(cap_param, 'cap')] = tb_cap

    # Load factor textbox
    ax_lf = plt.axes([table_left + col_width + col_gap, y_pos, col_width, textbox_height], facecolor='white')
    tb_lf = TextBox(ax_lf, '', initial='0.0', textalignment='center')
    textboxes[(lf_param, 'lf')] = tb_lf

# Create STORAGE table textboxes
for idx, (label, storage_type) in enumerate(storage_rows):
    y_pos = storage_table_top - idx * row_height

    # Power capacity textbox
    ax_pwr = plt.axes([table_left, y_pos, col_width, textbox_height], facecolor='white')
    tb_pwr = TextBox(ax_pwr, '', initial='0.0', textalignment='center')
    textboxes[(storage_type, 'power')] = tb_pwr

    # Energy capacity textbox
    ax_egy = plt.axes([table_left + col_width + col_gap, y_pos, col_width, textbox_height], facecolor='white')
    tb_egy = TextBox(ax_egy, '', initial='0.0', textalignment='center')
    textboxes[(storage_type, 'energy')] = tb_egy

def update_simulation_from_textboxes(event=None):
    """Update simulation using values from textboxes"""
    year = int(slider.val)
    weather = radio.value_selected

    cap = {}
    lfs = {}
    storage_override = {'Pumped_Hydro': {}, 'Batteries': {}}

    for (param, ptype), tb in textboxes.items():
        try:
            value = float(tb.text)
            if ptype == 'cap':
                cap[param] = value
            elif ptype == 'lf':
                # Clamp load factor between 0 and 1
                clamped_value = max(0.0, min(1.0, value))
                lfs[param] = clamped_value
                # Update textbox if value was clamped
                if clamped_value != value:
                    tb.set_val(f"{clamped_value:.2f}")
            elif ptype == 'power':
                storage_override[param]['power'] = value
            elif ptype == 'energy':
                storage_override[param]['energy'] = value
        except ValueError:
            pass

    df, soc_h, demand, total_energy_cap, residual_excess, wasted, storage_assets, renewable_curtailment, generation_excess = run_sim(year, weather, cap, lfs, storage_override)

    ax1.clear(); ax2.clear(); ax3.clear()

    sources = ['Nuclear', 'Solar', 'Hydro_RunOfRiver', 'Wind_Offshore', 'Wind_Onshore', 'Biomass', 'Interconnectors', 'Gas_CCGT', 'Gas_OCGT', 'Gas_Oil', 'Pumped_Hydro', 'Batteries']
    colors = ['#ff4444', '#ffcc5c', '#6b4226', '#2ab7ca', '#005b96', '#b3c100', '#a3a3a3', '#555555', '#888888', '#3d3d3d', '#4a90e2', '#f8e71c']

    # Graph 1: Generation stack (no legend on graph)
    ax1.stackplot(hours, [df[s] for s in sources], labels=sources, colors=colors, alpha=0.8)
    ax1.plot(hours, demand, color='black', lw=2, ls='--', label='Demand (+50% by 2035)')
    ax1.set_title(f"UK Grid Security: {year} ({weather}) | Renewable GWh Wasted: {int(wasted)}", fontsize=12, weight='bold')
    ax1.set_ylabel("Power (GW)", fontsize=10)
    ax1.grid(True, alpha=0.3)

    # Graph 2: Storage (no legend on graph)
    ax2.plot(hours, soc_h['Pumped_Hydro'], color='#4a90e2', lw=2, label='Hydro SoC')
    ax2.plot(hours, soc_h['Batteries'], color='#f8e71c', lw=2, label='Battery SoC')
    ax2.set_ylabel("GWh Stored", fontsize=10)
    ax2.set_ylim(0, total_energy_cap + 10)
    ax2.grid(True, alpha=0.3)

    # Graph 3: Residual capacity - separate renewable curtailment from total excess
    # Light grey background: Total generation excess capacity (excludes storage)
    ax3.fill_between(hours, [max(0, x) for x in generation_excess], 0, color='#bdc3c7', alpha=0.3, label='Total Excess Capacity')
    # Main green: Renewable energy curtailed (wasted renewables)
    ax3.fill_between(hours, renewable_curtailment, 0, color='#27ae60', alpha=0.7, label='Renewable Curtailment')
    # Red: Unmet demand (after storage discharge)
    ax3.fill_between(hours, residual_excess, 0, where=(np.array(residual_excess) < 0), color='#e74c3c', alpha=0.5, label='Unmet Demand')
    ax3.axhline(0, color='black', lw=1, ls='-')
    ax3.set_ylabel("Residual Cap. (GW)", fontsize=10)
    ax3.set_xlabel("Time (4-Day Scenario)", fontsize=10)

    # Set x-axis to show times of day with day markers
    tick_positions = list(range(0, 96, 12))  # Every 12 hours (midnight and noon)
    tick_labels = []
    for hour in tick_positions:
        day = (hour // 24) + 1
        hour_of_day = hour % 24
        tick_labels.append(f"D{day} {hour_of_day:02d}:00")

    ax3.set_xticks(tick_positions)
    ax3.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
    ax3.legend(loc='upper left', fontsize=8)
    ax3.grid(True, alpha=0.3)

    fig.canvas.draw_idle()

def update_textboxes_from_sliders(val):
    """Update textbox values when year slider changes"""
    year = int(slider.val)
    weather = radio.value_selected

    cap = df_fleet.loc[year].to_dict()
    w = weather_scenarios[weather]

    # Update generation capacity textboxes
    textboxes[('Nuclear', 'cap')].set_val(f"{cap['Nuclear']:.2f}")
    textboxes[('Solar', 'cap')].set_val(f"{cap['Solar']:.2f}")
    textboxes[('Hydro_RunOfRiver', 'cap')].set_val(f"{cap['Hydro_RunOfRiver']:.2f}")
    textboxes[('Wind_Offshore', 'cap')].set_val(f"{cap['Wind_Offshore']:.2f}")
    textboxes[('Wind_Onshore', 'cap')].set_val(f"{cap['Wind_Onshore']:.2f}")
    textboxes[('Biomass', 'cap')].set_val(f"{cap['Biomass']:.2f}")
    textboxes[('Interconnectors', 'cap')].set_val(f"{cap['Interconnectors']:.2f}")
    textboxes[('Gas_CCGT', 'cap')].set_val(f"{cap['Gas_CCGT']:.2f}")
    textboxes[('Gas_OCGT', 'cap')].set_val(f"{cap['Gas_OCGT']:.2f}")
    textboxes[('Gas_Oil', 'cap')].set_val(f"{cap['Gas_Oil']:.2f}")

    # Update storage textboxes (split from total Storage_Power and Storage_Energy)
    textboxes[('Pumped_Hydro', 'power')].set_val(f"{cap['Storage_Power'] * 0.3:.2f}")
    textboxes[('Batteries', 'power')].set_val(f"{cap['Storage_Power'] * 0.7:.2f}")
    textboxes[('Pumped_Hydro', 'energy')].set_val(f"{cap['Storage_Energy'] * 0.7:.2f}")
    textboxes[('Batteries', 'energy')].set_val(f"{cap['Storage_Energy'] * 0.3:.2f}")

    # Update load factor textboxes
    textboxes[('Nuclear', 'lf')].set_val("0.90")
    textboxes[('Solar_Peak', 'lf')].set_val(f"{w['Solar_Peak']:.2f}")
    textboxes[('Hydro_RunOfRiver', 'lf')].set_val("0.80")
    textboxes[('Wind_Offshore', 'lf')].set_val(f"{w['Wind_Off']:.2f}")
    textboxes[('Wind_Onshore', 'lf')].set_val(f"{w['Wind_On']:.2f}")
    textboxes[('Biomass', 'lf')].set_val("0.95")
    textboxes[('Interconnectors', 'lf')].set_val(f"{w['Interconnectors']:.2f}")
    textboxes[('Gas_CCGT', 'lf')].set_val("1.00")
    textboxes[('Gas_OCGT', 'lf')].set_val("1.00")
    textboxes[('Gas_Oil', 'lf')].set_val("1.00")

    # Don't auto-update simulation - wait for user to press Enter

def update_load_factors_from_weather(val):
    """Update only load factors when weather changes, keep capacities unchanged"""
    weather = radio.value_selected
    w = weather_scenarios[weather]

    # Update only load factor textboxes based on weather
    textboxes[('Nuclear', 'lf')].set_val("0.90")
    textboxes[('Solar_Peak', 'lf')].set_val(f"{w['Solar_Peak']:.2f}")
    textboxes[('Hydro_RunOfRiver', 'lf')].set_val("0.80")
    textboxes[('Wind_Offshore', 'lf')].set_val(f"{w['Wind_Off']:.2f}")
    textboxes[('Wind_Onshore', 'lf')].set_val(f"{w['Wind_On']:.2f}")
    textboxes[('Biomass', 'lf')].set_val("0.95")
    textboxes[('Interconnectors', 'lf')].set_val(f"{w['Interconnectors']:.2f}")
    textboxes[('Gas_CCGT', 'lf')].set_val("1.00")
    textboxes[('Gas_OCGT', 'lf')].set_val("1.00")
    textboxes[('Gas_Oil', 'lf')].set_val("1.00")

    # Re-run simulation with updated load factors
    update_simulation_from_textboxes()

# --- RIGHT PANEL LAYOUT ---
# Using figure coordinates (right panel is x: 0.68-0.98)

# Add color key / legend at top
fig.text(0.69, 0.93, 'COLOR KEY', fontsize=11, weight='bold')

sources = ['Nuclear', 'Solar', 'Hydro_RunOfRiver', 'Wind_Offshore', 'Wind_Onshore', 'Biomass', 'Interconnectors', 'Gas_CCGT', 'Gas_OCGT', 'Gas_Oil', 'Pumped_Hydro', 'Batteries']
colors = ['#ff4444', '#ffcc5c', '#6b4226', '#2ab7ca', '#005b96', '#b3c100', '#a3a3a3', '#555555', '#888888', '#3d3d3d', '#4a90e2', '#f8e71c']
source_labels = ['Nuclear', 'Solar', 'Hydro', 'Wind Off.', 'Wind On.', 'Biomass', 'Intercon.', 'CCGT', 'OCGT', 'Oil', 'Pmp Hydro', 'Batteries']

legend_y_start = 0.89
legend_spacing = 0.033
for idx, (label, color) in enumerate(zip(source_labels, colors)):
    y_pos = legend_y_start - (idx % 6) * legend_spacing
    x_pos = 0.69 if idx < 6 else 0.84
    # Color box
    rect = plt.Rectangle((x_pos, y_pos - 0.008), 0.015, 0.020, color=color, alpha=0.8, transform=fig.transFigure, clip_on=False)
    fig.patches.append(rect)
    # Label
    fig.text(x_pos + 0.018, y_pos, label, fontsize=8, va='center')

# Weather selector label
fig.text(0.69, 0.64, 'WEATHER', fontsize=10, weight='bold')

# Add GENERATION table header
fig.text(0.69, 0.48, 'GENERATION', fontsize=11, weight='bold')
fig.text(0.69, 0.45, 'Source', fontsize=9, weight='bold')
fig.text(0.775, 0.45, 'Cap (GW)', fontsize=9, weight='bold')
fig.text(0.875, 0.45, 'Load Factor', fontsize=9, weight='bold')

# Add row labels for generation table
for idx, (label, cap_param, lf_param) in enumerate(gen_rows):
    y_pos = gen_table_top - idx * row_height + 0.005
    fig.text(0.69, y_pos, label, fontsize=8, va='center')

# Add STORAGE table header (below generation table)
fig.text(0.69, 0.17, 'STORAGE', fontsize=11, weight='bold')
fig.text(0.69, 0.14, 'Asset', fontsize=9, weight='bold')
fig.text(0.77, 0.14, 'Power (GW)', fontsize=9, weight='bold')
fig.text(0.87, 0.14, 'Energy (GWh)', fontsize=9, weight='bold')

# Add row labels for storage table
for idx, (label, storage_type) in enumerate(storage_rows):
    y_pos = storage_table_top - idx * row_height + 0.005
    fig.text(0.69, y_pos, label, fontsize=8, va='center')

# Connect events
slider.on_changed(update_textboxes_from_sliders)
radio.on_clicked(update_load_factors_from_weather)  # Weather change updates load factors only

# Connect each textbox to trigger simulation update on Enter
for tb in textboxes.values():
    tb.on_submit(update_simulation_from_textboxes)

# Initial setup - populate textboxes and run first simulation
update_textboxes_from_sliders(None)
update_simulation_from_textboxes()

# Maximize window on startup
mng = plt.get_current_fig_manager()
try:
    # Try TkAgg backend method
    mng.window.state('zoomed')
except:
    try:
        # Try Qt backend method
        mng.window.showMaximized()
    except:
        try:
            # Try macOS backend method
            mng.full_screen_toggle()
        except:
            pass  # If all fail, just show normally

plt.show()
