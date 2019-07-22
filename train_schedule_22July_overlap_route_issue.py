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



from itertools import combinations
from ortools.sat.python import cp_model
 

def test_overlap(t1_st, t1_end, t2_st, t2_end):
    
    def convert_to_minutes(t_str):
        hours, minutes = t_str.split(':')
        return 60*int(hours)+int(minutes)

    t1_st = convert_to_minutes(t1_st)
    t1_end = convert_to_minutes(t1_end)
    t2_st = convert_to_minutes(t2_st)
    t2_end = convert_to_minutes(t2_end)

# Check for wrapping time differences
    if t1_end < t1_st:
        if t2_end < t2_st:
        # Both wrap, therefore they overlap at midnight
            return True
        # t2 doesn't wrap. Therefore t1 has to start after t2 and end before
        return t1_st < t2_end or t2_st < t1_end

    if t2_end < t2_st:
        # only t2 wraps. Same as before, just reversed
        return t2_st < t1_end or t1_st < t2_end

    # They don't wrap and the start of one comes after the end of the other,
    # therefore they don't overlap
    if t1_st >= t2_end or t2_st >= t1_end:
        return False
    # In all other cases, they have to overlap
    return True



def main():
    model = cp_model.CpModel()
    solver = cp_model.CpSolver()
 
    # data
    route_km = {
        'R11': 700,
        'R32': 600,
        'R16': 600,
        'R41': 10,
        'R42': 10,
        'R43': 10,
        'R44': 10,
        'R45': 10}
    
    
    train_cum_km = {
        'T32': 24_300,
        'T11': 24_300,
        'T38': 24_200,
        'T28': 600,
        'T15': 200,
        'T24': 100}
    
    
    route_times = {
        'R11': ('05:00', '00:00'),
        'R32': ('06:00', '00:50'),
        'R16': ('05:20', '23:40'),
        'R41': ('11:15', '12:30'),
        'R42': ('11:45', '13:00'),
        'R43': ('12:15', '13:30'),
        'R44': ('12:45', '14:00'),
        'R45': ('13:20', '14:35')}
    
    
    
    trains = list(train_cum_km.keys())
    routes = list(route_km.keys())
    num_trains = len(trains)
    num_routes = len(routes)
    
    assignments = {(t, r): model.NewBoolVar('assignment_%s%s' % (t, r))
                   for t in trains for r in routes}
    
    
    # constraint 1: each train must be used
    for r in routes:
        model.Add(sum(assignments[(t, r)] for t in trains) == 1)
 
    # constraint 2: each train must do at least one (max two) routes
    for t in trains:
        model.Add(sum(assignments[(t, r)] for r in routes) >= 1)
        model.Add(sum(assignments[(t, r)] for r in routes) <= 2)
 
    
    # constraint 3: ensure the end of day cum km is less than 24_800
    # create a new variable which must be in the range (0,24_800)
    day_end_km = {
        t: model.NewIntVar(0, 24_800, 'train_%s_day_end_km' % t)
        for t in trains
    }
    
    for t in trains:
        # this will be constrained because day_end_km[t] is in domain [0, 24_800]
        tmp = sum(assignments[t, r]*route_km[r] for r in routes) + train_cum_km[t]   
        model.Add(day_end_km[t] == tmp)
 
    # constraint 4: where 2 routes are assigned to a train, these must not overlap
    for (r1, r2) in combinations(routes, 2):
        for (x1, x2) in combinations(route_times.values(),2):
            start1 = x1[0]
            end1   = x1[1]
            start2 = x2[0]
            end2   = x2[1]
            if test_overlap(start1, end1, start2, end2):
                 for train in trains:
                    model.AddBoolOr([assignments[train, r1].Not(), assignments[train, r2].Not()])
    

    status = solver.Solve(model)
    assert status in [cp_model.FEASIBLE, cp_model.OPTIMAL]
 
    for t in trains:
        t_routes = [r for r in routes if solver.Value(assignments[t, r])]
        print(f'Train {t} does route {t_routes} '
              f'with end of day cumulative kilometreage of '
              f'{solver.Value(day_end_km[t])}')
 
 
if __name__ == '__main__':
    main()

    
    
    
