# -*- coding: utf-8 -*-

"""
General description
-------------------
This example shows how to perform a capacity optimization for
an energy system with storage. The following energy system is modeled:

                input/output  bgas     bel
                     |          |        |       |
                     |          |        |       |
 wind(FixedSource)   |------------------>|       |
                     |          |        |       |
 pv(FixedSource)     |------------------>|       |
                     |          |        |       |
 gas_resource        |--------->|        |       |
 (Commodity)         |          |        |       |
                     |          |        |       |
 demand(Sink)        |<------------------|       |
                     |          |        |       |
                     |          |        |       |
 pp_gas(Transformer) |<---------|        |       |
                     |------------------>|       |
                     |          |        |       |
 storage(Storage)    |<------------------|       |
                     |------------------>|       |

The example exists in four variations. The following parameters describe
the main setting for the optimization variation 1:

    - optimize wind, pv, gas_resource and storage
    - set investment cost for wind, pv and storage
    - set gas price for kWh

    Results show an installation of wind and the use of the gas resource.
    A renewable energy share of 51% is achieved.

    Have a look at different parameter settings. There are four variations
    of this example in the same folder.

Data
----
storage_investment.csv

Installation requirements
-------------------------
This example requires the version v0.4.x of oemof. Install by:

    pip install 'oemof.solph>=0.4,<0.5'

The value of capacity is to be given in watts
"""

__copyright__ = "oemof developer group"
__license__ = "GPLv3"

###############################################################################
# Imports
###############################################################################

# Default logger of oemof
from oemof.tools import logger
from oemof.tools import economics
from oemof import solph

import logging
import os
import pandas as pd
import pprint as pp

number_timesteps = 8760

##########################################################################
# Initialize the energy system and read/calculate necessary parameters
##########################################################################

logger.define_logging()
logging.info("Initialize the energy system")
date_time_index = pd.date_range("1/1/2022", periods=number_timesteps, freq="H")

energysystem = solph.EnergySystem(timeindex=date_time_index)

# Read data file
full_filename = os.path.join(os.getcwd(), "storage_investment_ambon1.csv")
data = pd.read_csv(full_filename, sep=",")

price_gas = 6
price_coal = 75
price_oil = 0.8

# If the period is one year the equivalent periodical costs (epc) of an
# investment are equal to the annuity. Use oemof's economic tools.
epc_pv = economics.annuity(capex=1100, n=25, wacc=0.1)
epc_storage = economics.annuity(capex=1200, n=10, wacc=0.1)

##########################################################################
# Create oemof objects
##########################################################################

logging.info("Create oemof objects")
# create natural gas bus
bgas = solph.Bus(label="natural_gas")
bcoal = solph.Bus(label="coal")
boil = solph.Bus(label="oil")

# create electricity bus
bel = solph.Bus(label="electricity")

energysystem.add(bgas, bcoal, boil, bel)

# create excess component for the electricity bus to allow overproduction
excess = solph.Sink(label="excess_bel", inputs={bel: solph.Flow()})

# create source object representing the natural gas commodity (annual limit)
gas_resource = solph.Source(
    label="rgas", outputs={bgas: solph.Flow(variable_costs=price_gas)}
)

coal_resource = solph.Source(
    label="rcoal", outputs={bcoal: solph.Flow(variable_costs=price_coal)}
)

oil_resource = solph.Source(
    label="roil", outputs={boil: solph.Flow(variable_costs=price_oil)}
)


# create fixed source object representing pv power plants
pv = solph.Source(
    label="pv",
    outputs={
        bel: solph.Flow(
            fix=data["pv"], investment=solph.Investment(ep_costs=epc_pv)
        )
    },
)

# create simple sink object representing the electrical demand
demand = solph.Sink(
    label="demand",
    inputs={bel: solph.Flow(fix=data["demand_el"], nominal_value=1)},
)

# create simple transformer object representing a gas power plant
pp_gas = solph.Transformer(
    label="pp_gas",
    inputs={bgas: solph.Flow()},
    outputs={bel: solph.Flow(nominal_value=10e6, variable_costs=23)},
    conversion_factors={bel: 0.38},
)

# create simple transformer object representing a coal power plant
pp_coal = solph.Transformer(
    label="pp_coal",
    inputs={bcoal: solph.Flow()},
    outputs={bel: solph.Flow(nominal_value=14e6, variable_costs=40)},
    conversion_factors={bel: 0.35},
)

# create simple transformer object representing a oil power plant
pp_oil = solph.Transformer(
    label="pp_oil",
    inputs={boil: solph.Flow()},
    outputs={bel: solph.Flow(nominal_value=88e6, variable_costs=8)},
    conversion_factors={bel: 0.33},
)

# create storage object representing a battery
storage = solph.components.GenericStorage(
    label="storage",
    inputs={bel: solph.Flow(variable_costs=0.0001)},
    outputs={bel: solph.Flow()},
    loss_rate=0.00,
    initial_storage_level=0,
    invest_relation_input_capacity=1 / 6,
    invest_relation_output_capacity=1 / 6,
    inflow_conversion_factor=0.96,
    outflow_conversion_factor=0.96,
    investment=solph.Investment(ep_costs=epc_storage),
)

energysystem.add(excess, gas_resource, coal_resource, oil_resource, pv, demand, pp_gas, pp_oil, pp_coal, storage)

##########################################################################
# Optimise the energy system
##########################################################################

logging.info("Optimise the energy system")

# initialise the operational model
om = solph.Model(energysystem)

# if tee_switch is true solver messages will be displayed
logging.info("Solve the optimization problem")
om.solve(solver="cbc", solve_kwargs={"tee": True})

##########################################################################
# Check and plot the results
##########################################################################

# check if the new result object is working for custom components
results = solph.processing.results(om)

custom_storage = solph.views.node(results, "storage")
electricity_bus = solph.views.node(results, "electricity")

#my_energysystem.results['main'] = processing.results(om)
main_results = solph.processing.results(om)
meta_results = solph.processing.meta_results(om)
pp.pprint(meta_results)

my_results = electricity_bus["scalars"]

# installed capacity of storage in GWh
my_results["storage_invest_GWh"] = (
    results[(storage, None)]["scalars"]["invest"] / 1e6
)

# installed capacity of wind power plant in MW
#my_results["wind_invest_MW"] = results[(wind, bel)]["scalars"]["invest"] / 1e3
my_results["pv_invest_MW"] = results[(pv, bel)]["scalars"]["invest"] / 1e3
my_results["coal"] = results[(pp_coal,bel)]["sequences"]["flow"].sum()
my_results["gas"] = results[(pp_gas,bel)]["sequences"]["flow"].sum()
my_results["oil"] = results[(pp_oil,bel)]["sequences"]["flow"].sum()

# resulting renewable energy share
my_results["res_share"] = (
    1- (results[(pp_gas, bel)]["sequences"]["flow"].sum()+results[(pp_coal, bel)]["sequences"]["flow"].sum()
        +results[(pp_oil, bel)]["sequences"]["flow"].sum())/results[(bel, demand)]["sequences"]["flow"].sum()

)

pp.pprint(my_results)
