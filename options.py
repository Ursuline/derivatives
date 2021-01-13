#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 12 13:44:57 2021

Computes the price of european and american call & put options
for shares or futures

@author: charles mégnin
"""
import math
import pandas as pd

#### PARAMETERS ####
LATTICE_FLAG = True # send lattice to stdout
FUTURES_FLAG = True # Compute options from futures

# Lattice parameters:
S0   = 100.0 # initial price
T    = 0.5 # maturity (years)
SIG  = 0.2 # volatility
N    = 10 # number of periods
R    = 0.02 # risk-free rate
D    = 0.01 # dividend yield
EXPO = 10 # expiration (to use with futures)

# Option parameters
K    = 100.0 # strike price
OPT  = 'put' # call or put option
TYPE = 'american' # option type: european or american

# Futures parameters
EXPF = 10 # expiration
#### END PARAMETERS ####


def back_prop(lattice, row, column, proba):
    ''' returns q*S^(i+1)_(t+1) + (1-q)*S^i_(t+1)
        q = proba / S = lattice'''
    p_1 = lattice[row+1][column+1] # S^(i+1)_(t+1)
    p_2 = lattice[row][column+1]   # S^i_(t+1)

    return p_1*proba + p_2*(1-proba)


def risk_free_proba(r_ud):
    '''Computes risk-free probability q from parameters u & d in r_ud'''
    num   = math.exp((R-D)*T/N)-r_ud[1]
    denom = r_ud[0] - r_ud[1]
    print(f'q = {num/denom:.4f} / 1-q = {1-num/denom:.4f}\n')

    return num/denom


def binomial_model_parameter():
    ''' Computes binomial model parameters u & d=1/u
        u=r_ud[0] d=r_ud[1]
        Convert Black-Scholes / calibrate a binomial model'''
    r_ud = [0., 0.]
    r_ud[0] = math.exp(SIG*math.sqrt(T/N))
    r_ud[1] = 1.0/r_ud[0]
    print(f'u = {r_ud[0]:.5f} / d = {r_ud[1]:.5f}')

    return r_ud


#### Lattice computations ####

def initialize_matrix():
    '''returns an N+1xN+1 list for each lattice'''
    return [[0 for x in range(N+1)] for y in range(N+1)]


def futures_lattice(lattice, proba):
    ''' Compute future lattice from shares lattice. proba->q'''
    futures = initialize_matrix()
    for period in range(N, -1, -1):
        for option in range(period, -1, -1):
            if period == N: # Ft = St at maturity
                futures[option][period] = lattice[option][period]
            else:
                futures[option][period] = back_prop(futures, option, period, proba)

    return futures


def option_lattice(lattice, proba, option_flags):
    ''' Compute options lattice from shares or futures lattice
        Computes american put option price'''
    payoff = initialize_matrix()
    flag   = option_flags[0]

    for period in range(N, -1, -1):
        for option in range(period, -1, -1):
            if period == N:
                payoff[option][period] = max(flag*(lattice[option][period]-K), 0.)
            else:
                num   = back_prop(payoff, option, period, proba)
                denom = math.exp(R*T/N)
                ratio = num/denom
                e_value = K - lattice[option][period] # exercise value
                if option_flags[1] == 'E':
                    payoff[option][period] = ratio
                else: # American option
                    payoff[option][period] = max(e_value, ratio)
                    if e_value > ratio:
                        print(f'Exercising option {option}/t={period} {e_value:.2f}>{ratio:.2f}')

    return payoff


def share_lattice(r_ud):
    ''' Computes lattice of share values with binomial model / r_ud: u=rup & d=rdown
        shares: 2x2 matrix
    '''
    shares = initialize_matrix()
    shares[0][0] = S0

    for period in range(1, N+1):
        for share in range(0, period+1):
            if share == 0:
                s_prev = shares[share][period-1]
                shares[share][period] = r_ud[1]*s_prev
            else:
                s_prev = shares[share-1][period-1]
                shares[share][period] = r_ud[0]*s_prev

    return shares


#### standard out routines ####
def summarize_run():
    '''Prints summary input data to std out'''
    print(f'Computing price for {TYPE} {OPT} option')
    print(f'Initial price: {S0}')
    print(f'Strike price: {K}')
    print(f'Maturity: {T} years / {N} periods')
    print(f'Risk-free rate: {100*R:.2f}% / dividend yield: {100*D:.2f}%')
    print(f'Volatility {100*SIG:.2f}%')
    print()


def lattice_to_stdout(lattice, title):
    '''Prints lattice to stdout'''
    print(f'{title} lattice:')
    print(pd.DataFrame(lattice).loc[::-1])
    print()
#### END standard out routines ####


def set_option_flags():
    '''Sets option flags for call/put & european/american'''
    flags = [1.0, 'E'] # initialize option flags to European call
    if str.lower(OPT) == 'put':
        flags[0] = -1.0
    elif str.lower(OPT) != 'call':
        raise Exception(f'OPT should be "call" or "put". Its value is: "{OPT}"')
    if str.lower(TYPE) == 'american':
        flags[1] = 'A'
    elif str.lower(TYPE) != 'european':
        raise Exception(f'TYPE should be "european" or "american". Its value is: "{TYPE}"')

    # American call options are priced as European
    if flags[0] == 1:
        flags[1]='E'

    return flags


if __name__ == '__main__':
    summarize_run()
    OPT_FLAGS = set_option_flags() # call/put & european/american

    params = binomial_model_parameter() # u, d
    rf_q   = risk_free_proba(params) # q

    # compute share values lattice
    S = share_lattice(params)

    # compute futures values lattice
    if FUTURES_FLAG:
        F = futures_lattice(S, rf_q)

    # compute option price lattice
    if FUTURES_FLAG: #compute option pricing from futures
        P = option_lattice(F, rf_q, OPT_FLAGS)
    else: # compute option pricing from shares
        P = option_lattice(S, rf_q, OPT_FLAGS)

    if LATTICE_FLAG:
        lattice_to_stdout(S, 'Share')
        if FUTURES_FLAG:
            lattice_to_stdout(F, 'Futures')
        lattice_to_stdout(P, 'Option')
    print(f'C0={P[0][0]:.2f}')
