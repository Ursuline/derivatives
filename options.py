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
LATTICE_FLAG = True # print lattice to stdout
FUTURES_FLAG = True # Compute options from futures

# Lattice parameters:
S0   = 100.0 # initial price
T    = 0.5 # maturity (years)
SIG  = 0.2 # volatility
N    = 10 # number of periods
R    = 0.02 # risk-free rate
D    = 0.01 # dividend yield

# Option parameters
K    = 100.0 # strike price
OPT  = 'put' # call or put option
TYPE = 'american' # option type: european or american
EXPO = 10 # expiration - accomodates diff w/ #periods in lattice (EXPO<=N)

# Futures parameters
#EXPF = 10 # expiration
#### END PARAMETERS ####

class Security:
    '''Encapsulates parameters for the underlying security'''

    def __init__(self):
        self.init       = S0
        self.maturity   = T
        self.volatility = SIG
        self.n_periods  = N
        self.rate       = R
        self.dividend   = D

        self._binomial_model_parameter()
        self._risk_free_proba()


    def _binomial_model_parameter(self):
        ''' Computes binomial model parameters u & d=1/u
        u=r_ud[0] d=r_ud[1]
        Convert Black-Scholes / calibrate a binomial model'''
        self.r_ud    = [0., 0.]
        self.r_ud[0] = math.exp(self.volatility*math.sqrt(self.maturity/self.n_periods))
        self.r_ud[1] = 1.0/self.r_ud[0]


    def _risk_free_proba(self):
        '''Computes risk-free probability rfp=q from parameters u & d in r_ud'''
        self.rfp = 0.
        num    = math.exp((self.rate-self.dividend)*self.maturity/self.n_periods)
        num    = num - self.r_ud[1]
        denom  = self.r_ud[0] - self.r_ud[1]
        self.rfp = num / denom


    def print_summary(self):
        '''Prints summary parameters to std out'''
        print(f'Initial price: {self.init}')
        print(f'Maturity: {self.maturity} years / {self.n_periods} periods')
        print(f'Risk-free rate: {100*self.rate:.2f}%')
        print(f'Dividend yield: {100*self.dividend:.2f}%')
        print(f'Volatility: {100*self.volatility:.2f}%')


    def echo_model_parameters(self):
        '''Prints u & d to stdout'''
        print(f'u = {self.r_ud[0]:.5f} / d = {self.r_ud[1]:.5f}')


    def echo_risk_free_probability(self):
        '''prints risk-free probability q to stdout'''
        print(f'q = {self.rfp:.4f} / 1-q = {1-self.rfp:.4f}\n')


class Option:
    '''Encapsulates parameters for the option'''
    def __init__(self):
        self.type = TYPE
        self.opt  = OPT
        self.stike = K
        self.expir = EXPO
        self.flags = [1.0, 'E']
        self._set_option_flags()


    def print_summary(self):
        '''Prints summary parameters to std out'''
        print(f'{str.capitalize(self.type)} {self.opt} option')
        print(f'Expiration: {self.expir}')
        print(f'Flags={self.flags}')
        print()


    def _set_option_flags(self):
        '''Sets option flags for call/put & european/american'''
        if str.lower(self.opt) == 'put':
            self.flags[0] = -1.0
        elif str.lower(self.opt) != 'call':
            raise Exception(f'OPT should be "call" or "put". Its value is: "{OPT}"')
        if str.lower(self.type) == 'american':
            self.flags[1] = 'A'
        elif str.lower(self.type) != 'european':
            raise Exception(f'TYPE should be "european" or "american". Its value is: "{TYPE}"')

        # American call options are priced as European
        if self.flags[0] == 1:
            self.flags[1]='E'


class Lattice:
    ''' Lattice superclass encapsulates parameters and functionality
        for all lattices'''
    def __init__(self, size):
        self.lattice = [[0 for x in range(size+1)] for y in range(size+1)]
        self.size = size


    def back_prop(self, row, column, proba):
        ''' returns q*S^(i+1)_(t+1) + (1-q)*S^i_(t+1)
            q = proba / S = lattice'''
        p_1 = self.lattice[row+1][column+1] # S^(i+1)_(t+1)
        p_2 = self.lattice[row][column+1]   # S^i_(t+1)

        return p_1*proba + p_2*(1-proba)


    def lattice_to_stdout(self, title):
        '''Prints lattice to stdout'''
        print(f'{title} lattice:')
        print(pd.DataFrame(self.lattice).loc[::-1])
        # print()


class Options(Lattice):
    ''' Options lattice'''
    def __init__(self, underlying, option):
        Lattice.__init__(self, option.expir)

    def _build(self, underlying, option):
        for period in range(EXPO, -1, -1):
            for option in range(period, -1, -1):
                if period == self.size:
                    payoff[option][period] = max(flag*(lattice[option][period]-K), 0.)
                else:
                    num   = back_prop(payoff, option, period, proba)
                    denom = math.exp(R*T/EXPO)
                    ratio = num/denom
                    e_value = K - lattice[option][period] # exercise value
                    if option_flags[1] == 'E':
                        payoff[option][period] = ratio
                    else: # American option
                        payoff[option][period] = max(e_value, ratio)
                        if e_value > ratio:
                            print(f'Exercising option {option}/t={period} {e_value:.2f}>{ratio:.2f}')



class Shares(Lattice):
    ''' Shares lattice'''
    def __init__(self, security):
        Lattice.__init__(self, security.n_periods)
        self._build(security)


    def _build(self, security):
        self.lattice[0][0] = security.init
        for period in range(1, self.size+1):
            for share in range(0, period+1):
                if share == 0:
                    s_prev = self.lattice[share][period-1]
                    self.lattice[share][period] = security.r_ud[1]*s_prev
                else:
                    s_prev = self.lattice[share-1][period-1]
                    self.lattice[share][period] = security.r_ud[0]*s_prev


class Futures(Lattice):
    ''' Shares lattice'''
    def __init__(self, underlying, security):
        Lattice.__init__(self, security.n_periods)
        self._build(underlying, security)

    def _build(self, underlying, security):
        for period in range(self.size, -1, -1):
            for option in range(period, -1, -1):
                if period == self.size: # F_T = S_T at maturity
                    self.lattice[option][period] = underlying.lattice[option][period]
                else:
                    rfp = security.rfp
                    self.lattice[option][period] = self.back_prop(option, period, rfp)




def option_lattice(lattice, proba, option_flags):
    ''' Compute options lattice from shares or futures lattice
        Computes american put option price'''
    payoff = initialize_matrix(EXPO)
    flag   = option_flags[0]

    for period in range(EXPO, -1, -1):
        for option in range(period, -1, -1):
            if period == EXPO:
                payoff[option][period] = max(flag*(lattice[option][period]-K), 0.)
            else:
                num   = back_prop(payoff, option, period, proba)
                denom = math.exp(R*T/EXPO)
                ratio = num/denom
                e_value = K - lattice[option][period] # exercise value
                if option_flags[1] == 'E':
                    payoff[option][period] = ratio
                else: # American option
                    payoff[option][period] = max(e_value, ratio)
                    if e_value > ratio:
                        print(f'Exercising option {option}/t={period} {e_value:.2f}>{ratio:.2f}')

    return payoff


#### standard out routines ####
# def summarize_run():
#     '''Prints summary input data to std out'''
#     print(f'Computing price for {TYPE} {OPT} option')
#     print(f'Initial price: {S0}')
#     print(f'Strike price: {K}')
#     print(f'Maturity: {T} years / {N} periods')
#     print(f'Risk-free rate: {100*R:.2f}% / dividend yield: {100*D:.2f}%')
#     print(f'Volatility {100*SIG:.2f}%')
#     print()


# def lattice_to_stdout(lattice, title):
#     '''Prints lattice to stdout'''
#     print(f'{title} lattice:')
#     print(pd.DataFrame(lattice).loc[::-1])
#     print()
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
    sec = Security()
    sec.echo_model_parameters()
    sec.echo_risk_free_probability()

    opt = Option()
    sec.print_summary()
    opt.print_summary()

    shares = Shares(sec)
    shares.lattice_to_stdout('Shares')

    futures = Futures(shares, sec)
    futures.lattice_to_stdout('Futures')



    #x=1/0
    #summarize_run()

    #OPT_FLAGS = set_option_flags() # call/put & european/american

    #params = binomial_model_parameter() # u, d
    #rf_q   = risk_free_proba(params) # q

    # compute share values lattice
    #S = share_lattice(params)

    # compute futures values lattice
    # if FUTURES_FLAG:
    #     F = futures_lattice(S, rf_q)

    # # compute option price lattice
    # if FUTURES_FLAG: #compute option pricing from futures
    #     P = option_lattice(F, rf_q, OPT_FLAGS)
    # else: # compute option pricing from shares
    #     P = option_lattice(S, rf_q, OPT_FLAGS)

    # if LATTICE_FLAG:
    #     lattice_to_stdout(S, 'Share')
    #     if FUTURES_FLAG:
    #         lattice_to_stdout(F, 'Futures')
    #     lattice_to_stdout(P, 'Option')
    # print(f'C0={P[0][0]:.2f}')
