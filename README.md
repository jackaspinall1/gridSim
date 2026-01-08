# UK Grid Simulation Tool

An interactive Python application for simulating and visualizing the UK electricity grid's security and performance under different scenarios from 2025 to 2035. The tool models generation, demand, storage, and grid stability using a component-based demand model based on National Grid FES 2024 projections.

## Overview

This simulation tool provides a comprehensive analysis of the UK electricity grid, allowing users to:

- **Simulate grid operations** over 96-hour (4-day) periods
- **Explore different years** (2025-2035) with interpolated capacity projections
- **Test weather scenarios** including Dunkelflaute (winter low-renewable) and Summer Windy conditions
- **Adjust generation capacities and load factors** interactively
- **Model storage systems** (Pumped Hydro and Batteries) with realistic efficiency constraints
- **Track renewable curtailment** and unmet demand
- **Visualize real-time results** with interactive charts

## Features

### Component-Based Demand Model

The tool uses a demand model that breaks down electricity consumption into four key components:

1. **Baseload**: Traditional non-electrified demand (slow growth: 40-44 GW peak)
2. **Heat Pumps**: Rapid electrification of heating (2-18 GW peak by 2035)
3. **EV Charging**: Electric vehicle charging demand (3-20 GW peak by 2035)
4. **Behind-the-Meter Solar**: Rooftop solar generation that reduces apparent demand (5-15 GW capacity)

Each component has seasonal profiles (winter, summer, shoulder) that reflect realistic usage patterns throughout the day. Changes in these align with government targets.

### Generation Sources

The simulation models 10 generation technologies:

- **Nuclear** (5.88-11.0 GW): Base load generation
- **Solar** (15.7-62.0 GW): Variable renewable with seasonal patterns
- **Hydro Run-of-River** (1.47-1.5 GW): Small hydro capacity
- **Wind Offshore** (15.5-75.0 GW): Major renewable expansion
- **Wind Onshore** (15.2-36.0 GW): Onshore wind capacity
- **Biomass** (4.8-3.5 GW): Declining capacity
- **Interconnectors** (10.8-22.0 GW): Cross-border electricity imports/exports
- **Gas CCGT** (30.5-9.0 GW): Major retirement by 2035
- **Gas OCGT** (2.4-2.5 GW): Peaking plants
- **Oil Peakers** (0.1-0.5 GW): Emergency backup

### Storage Systems

Two storage technologies are modeled with realistic characteristics:

- **Pumped Hydro**: 75% efficiency, asymmetric charge/discharge (30% of total power capacity, 70% of total energy capacity)
- **Batteries**: 85% efficiency, symmetric charge/discharge (70% of total power capacity, 30% of total energy capacity)

### Weather Scenarios

Two extreme weather scenarios are included:

1. **Dunkelflaute** (Winter):
   - Low wind (Load factors of 10% offshore, 5% onshore)
   - Low solar (Load factors of 10% peak, 8-hour daylight)
   - High demand (winter heating)
   - Limited interconnector imports (10%)

2. **Summer Windy** (Summer):
   - High wind (Load factors of 85% offshore, 75% onshore)
   - High solar (Load factors of 80% peak, 16-hour daylight)
   - Lower demand (summer cooling)
   - Export capability (0% imports, potential exports). Set to be neutral on excess capacity; likely Europe also has excess as energy policy and weather are similar.

## Installation

### Prerequisites

- Python 3.7 or higher
- pip package manager

### Setup

1. Clone or download this repository
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

The required packages are:
- `matplotlib>=3.5.0` - For plotting and interactive widgets
- `pandas>=1.3.0` - For data manipulation
- `numpy>=1.21.0` - For numerical operations

## Usage

### Running the Simulation

Simply run the Python script:

```bash
python ukGridSim.py
```

The application will launch in a maximized window with interactive controls.

### Interactive Controls

#### Year Slider (Bottom Left)
- Adjust the simulation year from 2025 to 2035
- Automatically updates all capacity and demand parameters based on roadmap projections
- Values are interpolated between milestone years (2025, 2030, 2035)

#### Weather Selector (Right Panel)
- Toggle between "Dunkelflaute" and "Summer Windy" scenarios
- Automatically updates load factors for renewable sources
- Maintains your custom capacity settings

#### Generation Table (Right Panel)
- **Capacity (GW)**: Adjust installed capacity for each generation source
- **Load Factor**: Set utilization rate (0.0-1.0) for each source
  - Load factors are automatically clamped between 0 and 1
  - Weather selector updates renewable load factors automatically

#### Storage Table (Right Panel)
- **Power (GW)**: Set discharge/charge power capacity
- **Energy (GWh)**: Set energy storage capacity
- Default split: 30% Pumped Hydro / 70% Batteries for power, 70% / 30% for energy

### How to Modify Parameters

1. **Use the Year Slider**: Automatically populates all values from the roadmap
2. **Edit Textboxes**: Click any textbox, enter a new value, and press Enter
3. **Change Weather**: Click the weather radio button to update renewable load factors
4. **Custom Scenarios**: Manually adjust any parameter to test "what-if" scenarios

## Visualization

The tool displays three main charts:

### 1. Generation Stack Plot (Top)
- Shows hourly generation from all sources as a stacked area chart
- Black dashed line indicates total demand
- Title displays total renewable energy wasted (curtailed) in GWh
- Color-coded by generation source (see color key in right panel)

### 2. Storage State of Charge (Middle)
- Tracks energy stored in Pumped Hydro (blue) and Batteries (yellow)
- Shows how storage fills and depletes over the 96-hour period
- Y-axis shows GWh stored (0 to total energy capacity)

### 3. Residual Capacity (Bottom)
- **Green area**: Renewable energy curtailed (wasted)
- **Light grey background**: Total excess generation capacity (before storage)
- **Red area**: Unmet demand (after storage discharge)
- X-axis shows 4-day timeline with day markers (D1-D4) and hourly timestamps

## Simulation Logic

### Merit Order Dispatch

Generation is dispatched in priority order:
1. Nuclear (base load)
2. Solar (variable)
3. Hydro Run-of-River
4. Wind Offshore
5. Wind Onshore
6. Biomass
7. Interconnectors
8. Gas CCGT
9. Gas OCGT
10. Gas/Oil Peakers
11. Storage (Used as last resort to test energy security in the limit)

### Surplus Handling

When generation exceeds demand:
1. Meet all demand with available generation
2. Charge storage systems proportionally (based on charge capacity)
3. Curtail excess renewable energy if storage is full
4. Track renewable curtailment separately from total excess

### Deficit Handling

When demand exceeds generation:
1. Dispatch all available generation
2. Discharge storage systems proportionally (based on power capacity)
3. Calculate remaining unmet demand (may require load shedding or additional gas)
4. Track unmet demand in red on residual capacity chart

### Storage Efficiency

- **Pumped Hydro**: 75% round-trip efficiency (energy lost during charge/discharge)
- **Batteries**: 85% round-trip efficiency
- Storage cannot exceed energy capacity limits
- Charge/discharge rates are limited by power capacity

## Data Sources

The simulation is based on:

- **NESO FES 2024** (National Energy System Operator Future Energy Scenarios)
- **Clean Power 2030 Action Plan** (UK government targets)
- **National Grid FES 2023** "Leading The Way" scenario
- **UK Government projections** for electrification (heat pumps, EVs)

## Key Metrics

The simulation tracks:

- **Renewable Energy Wasted (GWh)**: Total renewable energy that must be curtailed
- **Renewable Curtailment**: Hourly renewable energy that cannot be used or stored
- **Unmet Demand**: Hourly demand that cannot be met after storage discharge
- **Storage Utilization**: State of charge for both storage systems
- **Generation Mix**: Hourly contribution from each generation source

## Limitations

- Simplified 96-hour simulation (4 days) - not a full year analysis
- Fixed seasonal profiles (winter/summer) - no daily weather variation
- Linear interpolation between milestone years (2025, 2030, 2035)
- Storage starts at full capacity (no initialization period)
- No transmission constraints or grid stability modeling
- Interconnectors modeled as simple import/export (no directional constraints)

## Future Enhancements

Potential improvements could include:
- Stochastic failure of power plants based on age
- Modified grid assets based on infrastructure buildout delays - update dynamically from data portal.
- Enhanced storage deployment algorithms. - Currently set to last resort as energy security test.
- Full year simulation with daily weather variation
- More granular demand components (industrial, commercial)
- Transmission network constraints
- Grid frequency and stability modeling
- Multiple interconnector directions and constraints
- Hydrogen storage and power-to-gas
- Demand response and smart charging

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The MIT License is a very permissive open-source license that allows all usage including commercial use, modification, distribution, and private use, with minimal restrictions.

## Contact

For questions or contributions, please refer to the repository: https://github.com/jackaspinall1/gridSim

