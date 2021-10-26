# -*- coding: utf-8 -*-

"""
General description
-------------------
This example shows how to create an energysystem with oemof objects and
solve it with the solph module. Results are plotted with solph.

Dispatch modelling is a typical thing to do with solph. However cost does not
have to be monetary but can be emissions etc. In this example a least cost
dispatch of different generators that meet an inelastic demand is undertaken.
Some of the generators are renewable energies with marginal costs of zero.
Additionally, it shows how combined heat and power units may be easily modelled
as well.

Data
----
input_data.csv

Installation requirements
-------------------------
This example requires the version v0.4.x of oemof and matplotlib. Install by:

    pip install 'oemof.solph>=0.4,<0.5'

Optional to see the plots:

    pip install matplotlib
"""

__copyright__ = "oemof developer group"
__license__ = "GPLv3"

import os
import pandas as pd
from oemof.solph import (
    Sink,
    Source,
    Transformer,
    Bus,
    Flow,
    Model,
    EnergySystem,
    views,
)

import matplotlib.pyplot as plt


solver = "cbc"

# Create an energy system and optimize the dispatch at least costs.
# ####################### initialize and provide data #####################

datetimeindex = pd.date_range("1/1/2022", periods=24 * 365, freq="H")
energysystem = EnergySystem(timeindex=datetimeindex)
filename = os.path.join(os.getcwd(), "storage_investment_ambon1.csv")
data = pd.read_csv(filename, sep=",")

# ######################### create energysystem components ################

# resource buses
bcoal = Bus(label="coal", balanced=False)
bgas = Bus(label="gas", balanced=False)
boil = Bus(label="oil", balanced=False)

# electricity and heat
bel = Bus(label="bel")

energysystem.add(bcoal, bgas, boil, bel)

# an excess and a shortage variable can help to avoid infeasible problems
energysystem.add(Sink(label="excess_el", inputs={bel: Flow()}))
shortage_el = Source(label='shortage_el',
                     outputs={bel: Flow(variable_costs=20000)},conversion_factors={bel: 0.33})

energysystem.add(shortage_el)

# sources
energysystem.add(
    Source(label="pv", outputs={bel: Flow(fix=data["pv"], nominal_value=256e3)})
)

# demands (electricity/heat)
energysystem.add(
    Sink(
        label="demand_el",
        inputs={bel: Flow(nominal_value=1e3, fix=data["demand_el"])},
    )
)


# power plants
energysystem.add(
    Transformer(
        label="pp_coal",
        inputs={bcoal: Flow()},
        outputs={bel: Flow(nominal_value=14e6, variable_costs=40.7)},
        conversion_factors={bel: 0.35},
    )
)

energysystem.add(
    Transformer(
        label="pp_gas",
        inputs={bgas: Flow()},
        outputs={bel: Flow(nominal_value=30e6, variable_costs=23.2)},
        conversion_factors={bel: 0.38},
    )
)

energysystem.add(
    Transformer(
        label="pp_oil",
        inputs={boil: Flow()},
        outputs={bel: Flow(nominal_value=98e6, variable_costs=8)},
        conversion_factors={bel: 0.33},
    )
)

# ################################ optimization ###########################

# create optimization model based on energy_system
optimization_model = Model(energysystem=energysystem)

# solve problem
optimization_model.solve(
    solver=solver, solve_kwargs={"tee": True, "keepfiles": False}
)

# write back results from optimization object to energysystem
optimization_model.results()

# ################################ results ################################

# subset of results that includes all flows into and from electrical bus
# sequences are stored within a pandas.DataFrames and scalars e.g.
# investment values within a pandas.Series object.
# in this case the entry data['scalars'] does not exist since no investment
# variables are used
data = views.node(optimization_model.results(), "bel")
data["sequences"].info()
print("Optimization successful. Showing some results:")

# see: https://pandas.pydata.org/pandas-docs/stable/visualization.html
node_results_bel = views.node(optimization_model.results(), "bel")
node_results_flows = node_results_bel["sequences"]

node_results_flows.to_csv("results.csv")

demand_el = node_results_flows.iloc[:,0].sum()
print("electricity demand: {:.3f}".format(demand_el))
excess_el = node_results_flows.iloc[:,1].sum()
print("{:04.1f} % excess generation: {:.3f}".format(
            100 * excess_el / demand_el, excess_el))
coal_generation = node_results_flows.iloc[:,2].sum()
print("{:04.1f} % coal plant coverage: {:.3f}".format(
            100 * coal_generation / demand_el, coal_generation))
gas_generation = node_results_flows.iloc[:,3].sum()
print("{:04.1f} % gas plant coverage: {:.3f}".format(
            100 * gas_generation / demand_el, gas_generation))
oil_generation = node_results_flows.iloc[:,4].sum()
print("{:04.1f} % oil plant coverage: {:.3f}".format(
            100 * oil_generation / demand_el, oil_generation))
pv_generation = node_results_flows.iloc[:,5].sum()
print("{:04.1f} % pv plant coverage: {:.3f}".format(
            100 * pv_generation / demand_el, pv_generation))
shortage = node_results_flows.iloc[:,6].sum()
print("{:04.1f} % shortage : {:.3f}".format(
            100 * shortage / demand_el, shortage))


fig, ax = plt.subplots(figsize=(10, 5))
node_results_flows.plot(ax=ax, kind="bar", stacked=True, linewidth=0, width=1)
ax.set_title("Sums for optimization period")
ax.legend(loc="upper right", bbox_to_anchor=(1, 1))
ax.set_xlabel("Energy (MWh)")
ax.set_ylabel("Flow")
plt.legend(loc="center left", prop={"size": 8}, bbox_to_anchor=(1, 0.5))
fig.subplots_adjust(right=0.8)

dates = node_results_flows.index
tick_distance = int(len(dates) / 7) - 1
ax.set_xticks(range(0, len(dates), tick_distance), minor=False)
ax.set_xticklabels(
    [item.strftime("%d-%m-%Y") for item in dates.tolist()[0::tick_distance]],
    rotation=30,
    minor=False,
)

plt.show()

