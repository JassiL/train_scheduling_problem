# Copyright 2010-2018 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



##################################################################################################
# Problem statement: Assign 6 trains to 8 routes during a one day period
#                    subject to the following constraints:
#                   1. each train must be used during the day
#                   2. a train must do at least one route during the day (max 2)
#                   3. for each train, the cumulative km from the previous day + route length 
#                      must not exceed 24,800 km
#                   4. where the train is assigned to two routes during the day, these routes 
#                      must not overlap
##################################################################################################

# this builds on Google OR-tools examples nurse rota schedule and 
# shift scheduling                   

from __future__ import print_function
from ortools.sat.python import cp_model
import datetime
from collections import namedtuple
from itertools import combinations


class RoutePartialSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, assignments, num_trains,  num_routes, sols):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._assignments = assignments
        self._num_trains = num_trains
        self._num_routes = num_routes
        self._solutions = set(sols)
        self._solution_count = 0

    def on_solution_callback(self):
        if self._solution_count in self._solutions:
            print('Solution %i' % self._solution_count)
            for t in range(self._num_trains):
                is_running = False
                for r in range(self._num_routes):
                    if self.Value(self._assignments[(t, r)]):
                            is_running = True
                            print('  Train %i does route %i' % (t, r))
                if not is_running:
                        print('  Train {} does not do a route'.format(t))
            print()
        self._solution_count += 1

    def solution_count(self):
        return self._solution_count





# define the number of trains and routes
num_trains = 6                     
num_routes = 8                     
all_trains = range(num_trains)
all_routes = range(num_routes)

#create the model
model = cp_model.CpModel()

# also create some dictionaries for the route kilometreage and cumulative kilometreage up to the previous day
route_km = { 0: 700,
             1: 600,
             2: 600,
             3: 10,
             4: 10,
             5: 10,
             6: 10,
             7: 10}

train_cum_km = { 0: 24_300,
                 1: 24_200,
                 2: 24_200,
                 3: 600,
                 4: 200,
                 5: 100 }


# create a list of the times of the routes to be used for constraint 4
route_times = [('05:00', '00:00'), 
               ('06:00', '00:50'), 
               ('05:20', '23:40'),
               ('11:15', '12:30'),
               ('11:45', '13:00'),
               ('12:15', '13:30'),
               ('12:45', '14:00'),
               ('13:20', '14:35')]

# this array defines assignments for routes to trains.
# assignments[(t,r)] equal 1 if route r is assigned to train t , else it's 0
# if you print assignments in the console, you will see all the possible combinations of 
# trains and routes

assignments = {}
for t in all_trains:
    for r in all_routes:
        assignments[(t,r)] = model.NewBoolVar('assignment_t%ir%i' % (t,r))
 
           
#################################################################################################################              
# constraint 1: each route is assigned to exactly one train
#################################################################################################################  
for r in all_routes:
    model.Add(sum(assignments[(t,r)] for t in all_trains) == 1)
    
    
#################################################################################################################        
# constraint 2: each train must do at least one route per day (and maximum two routes per day)
#################################################################################################################  
for t in all_trains:
    model.Add(sum(assignments[(t,r)] for r in all_routes) >= 1)
    model.Add(sum(assignments[(t,r)] for r in all_routes) <= 2)

#################################################################################################################  
# constraint 3: for each train, we must ensure cum km from previous day +  assigned route/s is less than 24_800
# note: the assignment needs to be multipied by the route length and the cumulative km to return a result
#################################################################################################################
for t in all_trains:
    day_end_km = sum(assignments[(t,r)]*route_km[r] + assignments[(t,r)]*train_cum_km[t] for r in all_routes) 
    model.Add(day_end_km <= 24_800)





# *******************************     START:      THIS IS NOT WORKING     ****************************************
#################################################################################################################  
# constraint 4: where the train is assigned to two routes during the day, these routes 
#               must not overlap    
#################################################################################################################  

# create a function which returns all possible pairs of routes and whether they overlap or not
def test_overlap(dt1_st, dt1_end, dt2_st, dt2_end):    
    Range = namedtuple('Range', ['start', 'end'])
    r1 = Range(start=dt1_st, end=dt1_end)
    r2 = Range(start=dt2_st, end=dt2_end)
    latest_start = max(r1.start, r2.start)
    earliest_end = min(r1.end, r2.end)
    overlap = (earliest_end - latest_start)
    return overlap.seconds

def find_overlaps(times):
    pairs = list(combinations(times, 2))
    print(pairs)
    for pair in pairs:
        start1 = datetime.datetime.strptime(pair[0][0], '%H:%M')
        end1   = datetime.datetime.strptime(pair[0][1], '%H:%M')
        start2 = datetime.datetime.strptime(pair[1][0], '%H:%M')
        end2   = datetime.datetime.strptime(pair[1][1], '%H:%M')
        yield test_overlap(start1, end1, start2, end2) > 0
        
list(find_overlaps(route_times))
# *******************************     END         ***************************************************************
# solve the model
solver = cp_model.CpSolver()
solver.parameters.linearization_level = 0

# Display the first five solutions.
a_few_solutions = range(5)

solution_printer = RoutePartialSolutionPrinter(assignments, num_trains, num_routes, a_few_solutions)
solver.SearchForAllSolutions(model, solution_printer)

# stats
print()
print('Statistics')
print(' - conflicts       : %i' % solver.NumConflicts())
print(' - branches        : %i' % solver.NumBranches())
print(' - wall time       : %f s' % solver.WallTime())
print(' - solutions found : %i' % solution_printer.solution_count())
