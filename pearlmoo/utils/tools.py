# -*- coding: utf-8 -*-
#"""
#@author: Paul
# External functions for multi-objective optimization
# adapted from the DEAP package: https://deap.readthedocs.io/en/master/about.html
# Félix-Antoine Fortin, François-Michel De Rainville, Marc-André Gardner, Marc Parizeau and Christian Gagné, “DEAP: Evolutionary Algorithms Made Easy”, Journal of Machine Learning Research, pp. 2171-2175, no 13, jul 2012.
#"""

from operator import itemgetter
import bisect

import pandas as pd
import numpy as np
from collections import defaultdict


##############################################################
# Helper functions for sorting individuals in the population #
##############################################################

def isDominated(wvalues1, wvalues2):
    """
    
    Returns whether or not *wvalues2* dominates *wvalues1*.
    
    :param wvalues1: (list) The weighted fitness values that would be dominated.
    :param wvalues2: (list) The weighted fitness values of the dominant.
    :Returns obj: (bool) `True` if wvalues2 dominates wvalues1, `False` otherwise.
    
    """
    not_equal = False
    for self_wvalue, other_wvalue in zip(wvalues1, wvalues2):
        if self_wvalue > other_wvalue:
            return False
        elif self_wvalue < other_wvalue:
            not_equal = True
    return not_equal


def isDominated_constr(wvalues1, wvalues2):
    """
    
    Returns whether or not *wvalues2* dominates *wvalues1* with a modification to handle constraints. (see 
    "An Evolutionary Many-Objective Optimization Algorithm Using Reference-point Based Non-dominated Sortign Approach, 
    Part II: Handling Constraints and Extending to an Adaptive Approach" Jain et al. (2013))
    
    :param wvalues1: (list) The weighted fitness values that would be dominated.
    :param wvalues2: (list) The weighted fitness values of the dominant.
    :Returns obj: (bool) `True` if wvalues2 dominates wvalues1, `False` otherwise.
    
    """
    not_equal = False
    if np.sum(wvalues1["constraints"]) == 0 and np.sum(wvalues2["constraints"]) != 0:
        return False
    elif np.sum(wvalues1["constraints"]) != 0 and np.sum(wvalues2["constraints"]) == 0:
        not_equal = True
    elif np.sum(wvalues1["constraints"]) != 0 and np.sum(wvalues2["constraints"]) != 0:
        if np.sum(wvalues1["constraints"]) > np.sum(wvalues2["constraints"]):
            not_equal = True
        else:
            not_equal = False
    elif np.sum(wvalues1["constraints"]) == 0 and np.sum(wvalues2["constraints"]) == 0:
        not_equal = isDominated(wvalues1["objectives"][0], wvalues2["objectives"][0])
    return not_equal

def sortNondominated_constr(pop, k, first_front_only=False):
    """
    Sort the first *k* *pop* into different nondomination levels.
    
    :param pop: (dict) population in dictionary structure
    :param k: (int) top k individuals are selected
    :param first_front_only [DEPRECATED]: (bool) If :obj:`True` sort only the first front and exit. 
    :Returns pareto_front: (list) A list of Pareto fronts, the first list includes nondominated pop.
    .. 

    reference: [Deb2002] Deb, Pratab, Agarwal, and Meyarivan, "A fast elitist
    non-dominated sorting genetic algorithm for multi-objective
    optimization: NSGA-II", 2002.
    """
    if k == 0:
        return []

    pop=list(pop.items())

    map_fit_ind = defaultdict(list)
    unfeasible_fits = defaultdict(list)
    for ind in pop:
        if np.sum(tuple(ind[1][2].items())[1][1]) == 0:# add if feasible
            map_fit_ind[ind[0]].append(ind)
        else:
            unfeasible_fits[ind[0]].append(ind)
    fits = list(map_fit_ind.keys())
    if fits == []:
        return [[list(sorted(pop,key=lambda x: np.sum(tuple(x[1][2].items())[1][1])))[0]],list(sorted(pop,key=lambda x: np.sum(tuple(x[1][2].items())[1][1])))[1:]],True# tuple(x[1][2].items())[1][1][0]))[0]],list(sorted(pop,key=lambda x: tuple(x[1][2].items())[1][1][0]))[1:]],True
    else:
        map_fit_ind.update(unfeasible_fits)
        fits = list(map_fit_ind.keys())
    
    current_front = []
    next_front = []
    dominating_fits = defaultdict(int)
    dominated_fits = defaultdict(list)

    # Rank first Pareto front
    for i, fit_i in enumerate(fits):
        for fit_j in fits[i+1:]:
            A = map_fit_ind[fit_j][0][1][2]#{"objectives":map_fit_ind[fit_j][0][1][2],"constraints":map_fit_ind[fit_j][0][1][2]}
            B = map_fit_ind[fit_i][0][1][2]#{"objectives":map_fit_ind[fit_i][0][1][2],"constraints":map_fit_ind[fit_i][0][1][2]}
            if isDominated_constr(A,B):#isDominated_constr(map_fit_ind[fit_j][0][1][2], map_fit_ind[fit_i][0][1][2]):
                dominating_fits[fit_j] += 1
                dominated_fits[fit_i].append(fit_j)
            elif isDominated_constr(A,B):#isDominated_constr(map_fit_ind[fit_i][0][1][2], map_fit_ind[fit_j][0][1][2]):
                dominating_fits[fit_i] += 1
                dominated_fits[fit_j].append(fit_i)
        if dominating_fits[fit_i] == 0:
            current_front.append(fit_i)
    

    fronts = [[]]
    for fit in current_front:
        fronts[-1].extend(map_fit_ind[fit])

    pareto_sorted = len(fronts[-1])

    # Rank the next front until all pop are sorted or
    # the given number of individual are sorted.
    if not first_front_only:
        N = min(len(pop), k)
        while pareto_sorted < N:
            fronts.append([])
            for fit_p in current_front:
                for fit_d in dominated_fits[fit_p]:
                    dominating_fits[fit_d] -= 1
                    if dominating_fits[fit_d] == 0:
                        next_front.append(fit_d)
                        pareto_sorted += len(map_fit_ind[fit_d]) # add element to the next solution
                        fronts[-1].extend(map_fit_ind[fit_d])
            current_front = next_front
            next_front = []
    return fronts,False

def sortNDHelperA_constr(fitnesses, obj, front):
    """
    Create a non-dominated sorting of S on the first M objectives
    """
    if len(fitnesses) < 2:
        return
    elif len(fitnesses) == 2:
        # Only two individuals, compare them and adjust front number
        s1, s2 = fitnesses[0], fitnesses[1]
        if isDominated(s2[:obj+1], s1[:obj+1]):
            front[s2] = max(front[s2], front[s1] + 1)
    elif obj == 1:
        sweepA(fitnesses, front)
    elif len(frozenset(map(itemgetter(obj), fitnesses))) == 1:
        #All individuals for objective M are equal: go to objective M-1
        sortNDHelperA_constr(fitnesses, obj-1, front)
    else:
        # More than two individuals, split list and then apply recursion
        best, worst = splitA(fitnesses, obj)
        sortNDHelperA_constr(best, obj, front)
        sortNDHelperB_constr(best, worst, obj-1, front)
        sortNDHelperA_constr(worst, obj, front)


def sortNDHelperB_constr(best, worst, obj, front):
    """
    Assign front numbers to the solutions in H according to the solutions
    in L. The solutions in L are assumed to have correct front numbers and the
    solutions in H are not compared with each other, as this is supposed to
    happen after sortNDHelperB is called.
    """
    key = itemgetter(obj)
    if len(worst) == 0 or len(best) == 0:
        #One of the lists is empty: nothing to do
        return
    elif len(best) == 1 or len(worst) == 1:
        #One of the lists has one individual: compare directly
        for hi in worst:
            for li in best:
                if isDominated(hi[:obj+1], li[:obj+1]) or hi[:obj+1] == li[:obj+1]:
                    front[hi] = max(front[hi], front[li] + 1)
    elif obj == 1:
        sweepB(best, worst, front)
    elif key(min(best, key=key)) >= key(max(worst, key=key)):
        #All individuals from L dominate H for objective M:
        #Also supports the case where every individuals in L and H
        #has the same value for the current objective
        #Skip to objective M-1
        sortNDHelperB_constr(best, worst, obj-1, front)
    elif key(max(best, key=key)) >= key(min(worst, key=key)):
        best1, best2, worst1, worst2 = splitB(best, worst, obj)
        sortNDHelperB_constr(best1, worst1, obj, front)
        sortNDHelperB_constr(best1, worst2, obj-1, front)
        sortNDHelperB_constr(best2, worst2, obj, front)

def sortLogNondominated_constr(pop, k, first_front_only=False):
    """
    Sort the first *k* *pop* into different nondomination levels.
    
    :param pop: (dict) population in dictionary structure
    :param k: (int) top k individuals are selected
    :param first_front_only [DEPRECATED]: (bool) If :obj:`True` sort only the first front and exit. 
    :Returns pareto_front: (list) A list of Pareto fronts, the first list includes nondominated pop.
    .. 

    reference: [Fortin2013] Fortin, Grenier, Parizeau, "Generalizing the improved run-time complexity algorithm for non-dominated sorting",
    Proceedings of the 15th annual conference on Genetic and evolutionary computation, 2013. 
    """
    if k == 0:
        return []

    pop=list(pop.items())
    #Separate individuals according to unique fitnesses
    unique_fits = defaultdict(list)
    
    unfeasible_fits = [] # useful for NSGA that needs all elements even unfeasibles

    for i, ind in enumerate(pop):
        if np.sum(tuple(ind[1][2].items())[1][1]) == 0:# add if feasible
            unique_fits[tuple(list(tuple(ind[1][2].items())[0][1][0]))].append(ind)
        else:
            unfeasible_fits.append(ind)
    
    #Launch the sorting algorithm
    obj = len(pop[0][1][2]["objectives"][0])-1
    fitnesses = list(unique_fits.keys())
    front = dict.fromkeys(fitnesses, 0)
    if fitnesses == []:
        return [[list(sorted(pop,key=lambda x: np.sum(tuple(x[1][2].items())[1][1])))[0]],list(sorted(pop,key=lambda x: np.sum(tuple(x[1][2].items())[1][1])))[1:]],True#tuple(x[1][2].items())[1][1][0]))[0]],list(sorted(pop,key=lambda x: tuple(x[1][2].items())[1][1][0]))[1:]],True
    # Sort the fitnesses lexicographically.
    fitnesses.sort(reverse=True)
    sortNDHelperA_constr(fitnesses, obj, front)
    
    #Extract pop from front list here
    nbfronts = max(front.values())+1
    pareto_fronts = [[] for i in range(nbfronts)]
    for fit in fitnesses:
        index = front[fit]
        pareto_fronts[index].extend(unique_fits[fit])
    # added for NSGA-III 
    unfeasible_fits = list(sorted(unfeasible_fits,key=lambda x: np.sum(tuple(x[1][2].items())[1][1])))# tuple(x[1][2].items())[1][1][0]))# sort the unfeasible
    index = nbfronts - 1
    for fit in unfeasible_fits:
        pareto_fronts[index].extend([fit])
    # Keep only the fronts required to have k pop.
    if not first_front_only:
        count = 0
        for i, front in enumerate(pareto_fronts):
            count += len(front)
            if count >= k:

                return pareto_fronts[:i+1],False
        return pareto_fronts,False
    else:
        return pareto_fronts[0],False



def sortNondominated(pop, k, first_front_only=False):
    """
    Sort the first *k* *pop* into different nondomination levels.
    
    :param pop: (dict) population in dictionary structure
    :param k: (int) top k individuals are selected
    :param first_front_only [DEPRECATED]: (bool) If :obj:`True` sort only the first front and exit. 
    :Returns pareto_front: (list) A list of Pareto fronts, the first list includes nondominated pop.
    .. 

    reference: [Deb2002] Deb, Pratab, Agarwal, and Meyarivan, "A fast elitist
    non-dominated sorting genetic algorithm for multi-objective
    optimization: NSGA-II", 2002.
    """
    if k == 0:
        return []

    pop=list(pop.items())

    map_fit_ind = defaultdict(list)
    for ind in pop:
        map_fit_ind[ind[0]].append(ind)
    fits = list(map_fit_ind.keys())

    current_front = []
    next_front = []
    dominating_fits = defaultdict(int)
    dominated_fits = defaultdict(list)

    # Rank first Pareto front
    for i, fit_i in enumerate(fits):
        for fit_j in fits[i+1:]:
            if isDominated(map_fit_ind[fit_j][0][1][2], map_fit_ind[fit_i][0][1][2]):
                dominating_fits[fit_j] += 1
                dominated_fits[fit_i].append(fit_j)
            elif isDominated(map_fit_ind[fit_i][0][1][2], map_fit_ind[fit_j][0][1][2]):
                dominating_fits[fit_i] += 1
                dominated_fits[fit_j].append(fit_i)
        if dominating_fits[fit_i] == 0:
            current_front.append(fit_i)

    fronts = [[]]
    for fit in current_front:
        fronts[-1].extend(map_fit_ind[fit])
    pareto_sorted = len(fronts[-1])

    # Rank the next front until all pop are sorted or
    # the given number of individual are sorted.
    if not first_front_only:
        N = min(len(pop), k)
        while pareto_sorted < N:
            fronts.append([])
            for fit_p in current_front:
                for fit_d in dominated_fits[fit_p]:
                    dominating_fits[fit_d] -= 1
                    if dominating_fits[fit_d] == 0:
                        next_front.append(fit_d)
                        pareto_sorted += len(map_fit_ind[fit_d]) # add element to the next solution
                        fronts[-1].extend(map_fit_ind[fit_d])
            current_front = next_front
            next_front = []

    return fronts

#######################################
# Generalized Reduced runtime ND sort #
#######################################

def identity(obj):
    """
    Returns directly the argument *obj*.
    :param obj: (type)
    :Returns obj: (type)
    """
    return obj


def median(seq, key=identity):
    """
    Returns the median of *seq* - the numeric value separating the higher
    half of a sample from the lower half. If there is an even number of
    elements in *seq*, it returns the mean of the two middle values.
    """
    sseq = sorted(seq, key=key)
    length = len(seq)
    if length % 2 == 1:
        return key(sseq[(length - 1) // 2])
    else:
        return (key(sseq[(length - 1) // 2]) + key(sseq[length // 2])) / 2.0

def feasible(ind):
    """
    Check if individual created is feasible
    :param ind: (dict) individual in dictionary format {'objective':,'constraints':} 
    :return True or False
    """
    if np.sum(ind['constraints']) != 0:
        return False
    else:
        return True

def sortLogNondominated(pop, k, first_front_only=False):
    """
    Sort the first *k* *pop* into different nondomination levels.
    
    :param pop: (dict) population in dictionary structure
    :param k: (int) top k individuals are selected
    :param first_front_only [DEPRECATED]: (bool) If :obj:`True` sort only the first front and exit. 
    :Returns pareto_front: (list) A list of Pareto fronts, the first list includes nondominated pop.
    .. 

    reference: [Fortin2013] Fortin, Grenier, Parizeau, "Generalizing the improved run-time complexity algorithm for non-dominated sorting",
    Proceedings of the 15th annual conference on Genetic and evolutionary computation, 2013. 
    """
    if k == 0:
        return []

    pop=list(pop.items())
    #Separate individuals according to unique fitnesses
    unique_fits = defaultdict(list)
    for i, ind in enumerate(pop):
        unique_fits[tuple(ind[1][2])].append(ind)


    #Launch the sorting algorithm
    obj = len(pop[0][1][2])-1
    fitnesses = list(unique_fits.keys())
    front = dict.fromkeys(fitnesses, 0)

    # Sort the fitnesses lexicographically.
    fitnesses.sort(reverse=True)
    sortNDHelperA(fitnesses, obj, front)

    #Extract pop from front list here
    nbfronts = max(front.values())+1
    pareto_fronts = [[] for i in range(nbfronts)]
    for fit in fitnesses:
        index = front[fit]
        pareto_fronts[index].extend(unique_fits[fit])

    # Keep only the fronts required to have k pop.
    if not first_front_only:
        count = 0
        for i, front in enumerate(pareto_fronts):
            count += len(front)
            if count >= k:
                return pareto_fronts[:i+1]
        return pareto_fronts
    else:
        return pareto_fronts[0]

def sortNDHelperA(fitnesses, obj, front):
    """
    Create a non-dominated sorting of S on the first M objectives
    """
    if len(fitnesses) < 2:
        return
    elif len(fitnesses) == 2:
        # Only two individuals, compare them and adjust front number
        s1, s2 = fitnesses[0], fitnesses[1]
        if isDominated(s2[:obj+1], s1[:obj+1]):
            front[s2] = max(front[s2], front[s1] + 1)
    elif obj == 1:
        sweepA(fitnesses, front)
    elif len(frozenset(map(itemgetter(obj), fitnesses))) == 1:
        #All individuals for objective M are equal: go to objective M-1
        sortNDHelperA(fitnesses, obj-1, front)
    else:
        # More than two individuals, split list and then apply recursion
        best, worst = splitA(fitnesses, obj)
        sortNDHelperA(best, obj, front)
        sortNDHelperB(best, worst, obj-1, front)
        sortNDHelperA(worst, obj, front)

def splitA(fitnesses, obj):
    """
    Partition the set of fitnesses in two according to the median of
    the objective index *obj*. The values equal to the median are put in
    the set containing the least elements.
    """
    median_ = median(fitnesses, itemgetter(obj))
    best_a, worst_a = [], []
    best_b, worst_b = [], []

    for fit in fitnesses:
        if fit[obj] > median_:
            best_a.append(fit)
            best_b.append(fit)
        elif fit[obj] < median_:
            worst_a.append(fit)
            worst_b.append(fit)
        else:
            best_a.append(fit)
            worst_b.append(fit)

    balance_a = abs(len(best_a) - len(worst_a))
    balance_b = abs(len(best_b) - len(worst_b))

    if balance_a <= balance_b:
        return best_a, worst_a
    else:
        return best_b, worst_b

def sweepA(fitnesses, front):
    """
    Update rank number associated to the fitnesses according
    to the first two objectives using a geometric sweep procedure.
    """
    stairs = [-fitnesses[0][1]]
    fstairs = [fitnesses[0]]
    for fit in fitnesses[1:]:
        idx = bisect.bisect_right(stairs, -fit[1])
        if 0 < idx <= len(stairs):
            fstair = max(fstairs[:idx], key=front.__getitem__)
            front[fit] = max(front[fit], front[fstair]+1)
        for i, fstair in enumerate(fstairs[idx:], idx):
            if front[fstair] == front[fit]:
                del stairs[i]
                del fstairs[i]
                break
        stairs.insert(idx, -fit[1])
        fstairs.insert(idx, fit)

def sortNDHelperB(best, worst, obj, front):
    """
    Assign front numbers to the solutions in H according to the solutions
    in L. The solutions in L are assumed to have correct front numbers and the
    solutions in H are not compared with each other, as this is supposed to
    happen after sortNDHelperB is called.
    """
    key = itemgetter(obj)
    if len(worst) == 0 or len(best) == 0:
        #One of the lists is empty: nothing to do
        return
    elif len(best) == 1 or len(worst) == 1:
        #One of the lists has one individual: compare directly
        for hi in worst:
            for li in best:
                if isDominated(hi[:obj+1], li[:obj+1]) or hi[:obj+1] == li[:obj+1]:
                    front[hi] = max(front[hi], front[li] + 1)
    elif obj == 1:
        sweepB(best, worst, front)
    elif key(min(best, key=key)) >= key(max(worst, key=key)):
        #All individuals from L dominate H for objective M:
        #Also supports the case where every individuals in L and H
        #has the same value for the current objective
        #Skip to objective M-1
        sortNDHelperB(best, worst, obj-1, front)
    elif key(max(best, key=key)) >= key(min(worst, key=key)):
        best1, best2, worst1, worst2 = splitB(best, worst, obj)
        sortNDHelperB(best1, worst1, obj, front)
        sortNDHelperB(best1, worst2, obj-1, front)
        sortNDHelperB(best2, worst2, obj, front)

def splitB(best, worst, obj):
    """
    Split both best individual and worst sets of fitnesses according
    to the median of objective *obj* computed on the set containing the
    most elements. The values equal to the median are attributed so as
    to balance the four resulting sets as much as possible.
    """
    median_ = median(best if len(best) > len(worst) else worst, itemgetter(obj))
    best1_a, best2_a, best1_b, best2_b = [], [], [], []
    for fit in best:
        if fit[obj] > median_:
            best1_a.append(fit)
            best1_b.append(fit)
        elif fit[obj] < median_:
            best2_a.append(fit)
            best2_b.append(fit)
        else:
            best1_a.append(fit)
            best2_b.append(fit)

    worst1_a, worst2_a, worst1_b, worst2_b = [], [], [], []
    for fit in worst:
        if fit[obj] > median_:
            worst1_a.append(fit)
            worst1_b.append(fit)
        elif fit[obj] < median_:
            worst2_a.append(fit)
            worst2_b.append(fit)
        else:
            worst1_a.append(fit)
            worst2_b.append(fit)

    balance_a = abs(len(best1_a) - len(best2_a) + len(worst1_a) - len(worst2_a))
    balance_b = abs(len(best1_b) - len(best2_b) + len(worst1_b) - len(worst2_b))

    if balance_a <= balance_b:
        return best1_a, best2_a, worst1_a, worst2_a
    else:
        return best1_b, best2_b, worst1_b, worst2_b

def sweepB(best, worst, front):
    """
    Adjust the rank number of the worst fitnesses according to
    the best fitnesses on the first two objectives using a sweep
    procedure.
    """
    stairs, fstairs = [], []
    iter_best = iter(best)
    next_best = next(iter_best, False)
    for h in worst:
        while next_best and h[:2] <= next_best[:2]:
            insert = True
            for i, fstair in enumerate(fstairs):
                if front[fstair] == front[next_best]:
                    if fstair[1] > next_best[1]:
                        insert = False
                    else:
                        del stairs[i], fstairs[i]
                    break
            if insert:
                idx = bisect.bisect_right(stairs, -next_best[1])
                stairs.insert(idx, -next_best[1])
                fstairs.insert(idx, next_best)
            next_best = next(iter_best, False)

        idx = bisect.bisect_right(stairs, -h[1])
        if 0 < idx <= len(stairs):
            fstair = max(fstairs[:idx], key=front.__getitem__)
            front[h] = max(front[h], front[fstair]+1)

##########################################################################
# niching - based Selection functions 
# reference: [Deb2014] Deb, K., & Jain, H. (2014). 
# An Evolutionary Many-Objective Optimization
# Algorithm Using Reference-Point-Based Nondominated Sorting Approach,
# Part I: Solving Problems With Box Constraints. IEEE Transactions on
# Evolutionary Computation, 18(4), 577-601. doi:10.1109/TEVC.2013.2281535.
##########################################################################

def find_extreme_points(fitnesses, best_point, extreme_points=None):
    """
    Finds the individuals with extreme values for each objective function.
    :param fitnesses: (list) list of fitness for each individual
    :param best_point: (list) list of the best fitness found for each objective
    :param extreme_points: (list) Extreme points found at previous generation. If not provided
    find the extreme points only from current pop.  

    :Returns fitness with minimal asf (new extreme points)
    """
    # Keep track of last generation extreme points
    if extreme_points is not None:
        fitnesses = np.concatenate((fitnesses, extreme_points), axis=0)

    # Translate objectives
    ft = fitnesses - best_point

    # Find achievement scalarizing function (asf)
    asf = np.eye(best_point.shape[0])
    asf[asf == 0] = 1e6
    asf = np.max(ft * asf[:, np.newaxis, :], axis=2)

    # Extreme point are the fitnesses with minimal asf
    min_asf_idx = np.argmin(asf, axis=1)
    return fitnesses[min_asf_idx, :]


def find_intercepts(extreme_points, best_point, current_worst, front_worst):
    """
    Find intercepts between the hyperplane and each axis with
    the ideal point as origin.

    :param extreme_points: (list) list of extreme points for each objective
    :param best_point: (list) list of best points for each objective
    :param current_worst: (list) list of worst fitness for each objective (ever found if memory is implemented: TO DO!!)
    :Param front_worst: (list) current list of worst fitness for each objective (equal to current_worst for the current version)

    :Returns intercepts: (list) Obj-dimensional intercept.
    """
    # Construct hyperplane sum(f_i^n) = 1
    b = np.ones(extreme_points.shape[1])
    A = extreme_points - best_point
    try:
        x = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        intercepts = current_worst
    else:
        if np.count_nonzero(x) != len(x):
            intercepts = front_worst
        else:
            intercepts = 1 / x

            if (not np.allclose(np.dot(A, x), b) or
                    np.any(intercepts <= 1e-6) or
                    np.any((intercepts + best_point) > current_worst)):
                intercepts = front_worst

    return intercepts


def associate_to_niche(fitnesses, reference_points, best_point, intercepts):
    """
    Associates individuals to reference points and calculates niche number.
    Corresponds to Algorithm 3 of Deb & Jain (2014).
    
    :param fitnesses: (list) list of fitness for each individual
    :param reference_points: (list) list of Obj-dimensional reference points leveraged to obtain a well-spread pareto front
    :param best_point: (list) list of the best fitness found for each objective
    :param intercepts: (list) Obj-dimensional intercept.
    :Returns
    niches: (list) associated reference point for each individual
    distances: (list) distance of each individual to its associated niche
    """
    # Normalize by ideal point and intercepts
    fn = (fitnesses - best_point) / (intercepts - best_point)

    # Create distance matrix
    fn = np.repeat(np.expand_dims(fn, axis=1), len(reference_points), axis=1)
    norm = np.linalg.norm(reference_points, axis=1)
    
    distances = np.sum(fn * reference_points, axis=2) / norm.reshape(1, -1)
    distances = distances[:, :, np.newaxis] * reference_points[np.newaxis, :, :] / norm[np.newaxis, :, np.newaxis]
    distances = np.linalg.norm(distances - fn, axis=2)

    # Retrieve min distance niche index
    niches = np.argmin(distances, axis=1)
    distances = distances[range(niches.shape[0]), niches]
    return niches, distances


def niching(pop, k, niches, distances, niche_counts):
    """
    niche preserving operator. Choose elements which are associated to reference points
    with the lowest number of association from the already choosen batch of solution Pt
    
    :param pop: (dict) population in dictionary structure
    :param k: (int) top k individuals to select to complete the population
    :param niches: (list) associated reference point for each individual
    :param distances: (list) distance of each individual to its associated niche
    :param niching: (list) count per niche 

    :Returns selected: (list) remaining individual to complete the population
    """
    selected = []
    available = np.ones(len(pop), dtype=np.bool)
    while len(selected) < k:
        # Maximum number of individuals (niches) to select in that round
        n = k - len(selected)

        # Find the available niches and the minimum niche count in them
        available_niches = np.zeros(len(niche_counts), dtype=np.bool)
        available_niches[np.unique(niches[available])] = True
        min_count = np.min(niche_counts[available_niches])

        # Select at most n niches with the minimum count
        selected_niches = np.flatnonzero(np.logical_and(available_niches, niche_counts == min_count))
        np.random.shuffle(selected_niches)
        selected_niches = selected_niches[:n]

        for niche in selected_niches:
            # Select from available individuals in niche
            niche_individuals = np.flatnonzero(np.logical_and(niches == niche, available))
            np.random.shuffle(niche_individuals)

            # If no individual in that niche, select the closest to reference
            # Else select randomly
            if niche_counts[niche] == 0:
                sel_index = niche_individuals[np.argmin(distances[niche_individuals])]
            else:
                sel_index = niche_individuals[0]

            # Update availability, counts and selection
            available[sel_index] = False
            niche_counts[niche] += 1
            selected.append(pop[sel_index])

    return selected


def uniform_reference_points(nobj, p=4, scaling=None):
    """
    Generate reference points uniformly on the hyperplane intersecting
    each axis at 1. The scaling factor is used to combine multiple layers of
    reference points.

    :param nobj: (int) number of objective
    :param p: (int) number of division along each objective
    :param scaling [DEPRECATED]:
    :Returns ref_points: (list) list of Obj-dimensional reference points 
    """
    def gen_refs_recursive(ref, nobj, left, total, depth):
        points = []
        if depth == nobj - 1:
            ref[depth] = left / total
            points.append(ref)
        else:
            for i in range(left + 1):
                ref[depth] = i / total
                points.extend(gen_refs_recursive(ref.copy(), nobj, left - i, total, depth + 1))
        return points

    ref_points = np.array(gen_refs_recursive(np.zeros(nobj), nobj, p, p, 0))
    if scaling is not None:
        ref_points *= scaling
        ref_points += (1 - scaling) / nobj

    return ref_points


##########################################################################
# crowding distance - based Selection functions 
# reference: [Deb2002] Deb, Pratab, Agarwal, and Meyarivan, "A fast elitist
# non-dominated sorting genetic algorithm for multi-objective
# optimization: NSGA-II", 2002.
##########################################################################

def assignCrowdingDist(pop):
    """
    Assign a crowding distance to each individual's fitness. 

    :param pop: (list) list of individuals and assocated positions, strategy vector, and fitness
    :Returns:
    CrowDist: (dict) dictionnary of element of pop and associated crowding distance
    """
    if len(pop) == 0:
        return
    CrowdDist = {}
    distances = [0.0] * len(pop)
    crowd = [(ind[1][2], i) for i, ind in enumerate(pop)]

    nobj = len(pop[0][1][2])

    for i in range(nobj):
        crowd.sort(key=lambda element: element[0][i])
        distances[crowd[0][1]] = float("inf")
        distances[crowd[-1][1]] = float("inf")
        if crowd[-1][0][i] == crowd[0][0][i]:
            continue
        norm = nobj * float(crowd[-1][0][i] - crowd[0][0][i])
        for prev, cur, next in zip(crowd[:-2], crowd[1:-1], crowd[2:]):
            distances[cur[1]] += (next[0][i] - prev[0][i]) / norm

    for i, dist in enumerate(distances):
        CrowdDist[pop[i][0]] = dist
    return CrowdDist