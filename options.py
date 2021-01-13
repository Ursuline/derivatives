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
TYPE = 'european' # option type: european or american
EXPO = 10 # expiration - accomodates diff w/ #periods in lattice (EXPO<=N)

# Futures parameters
#EXPF = 10 # expiration
#### END PARAMETERS ####

class SecurityParameters:
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
        print(f'q = {self.rfp:.5f} / 1-q = {1-self.rfp:.5f}\n')


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


    def price_to_stdout(self):
        '''Prints derivative price to stdout'''
        print(f'C0={self.lattice[0][0]:.2f}')



class Options(Lattice):
    ''' Options lattice / subclass of Lattice'''
    def __init__(self, underlying, sec_par):
        self.type  = TYPE
        self.opt   = OPT
        self.strike = K
        self.expir  = EXPO
        self.flags  = [1.0, 'E']
        Lattice.__init__(self, self.expir)
        self._set_option_flags()
        self._build(underlying, sec_par)


    def _build(self, underlying, sec_par):
        strike = self.strike
        flag   = self.flags[0]
        rfp    = sec_par.rfp
        for period in range(self.size, -1, -1):
            for option in range(period, -1, -1):
                if period == self.size:
                    comp = underlying.lattice[option][period]-strike
                    self.lattice[option][period] = max(flag*comp, 0.)
                else:
                    num   = self.back_prop(option, period, rfp)
                    denom = math.exp(sec_par.rate*sec_par.maturity/self.size)
                    ratio = num/denom

                    ex_val = strike - underlying.lattice[option][period] # exercise value
                    if self.flags[1] == 'E':
                        self.lattice[option][period] = ratio
                    else: # American option
                        self.lattice[option][period] = max(ex_val, ratio)
                        if ex_val > ratio:
                            print(f'Exercizing option {option}/t={period} {ex_val:.2f}>{ratio:.2f}')


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


    def print_summary(self):
        '''Prints summary parameters to std out'''
        print(f'{str.capitalize(self.type)} {self.opt} option')
        print(f'Expiration: {self.expir}')
        print(f'Strike price={self.strike}')
        print()


class Futures(Lattice):
    ''' Shares lattice / subclass of Lattice'''
    def __init__(self, underlying, sec_par):
        Lattice.__init__(self, sec_par.n_periods)
        self._build(underlying, sec_par)


    def _build(self, underlying, sec_par):
        for period in range(self.size, -1, -1):
            for option in range(period, -1, -1):
                if period == self.size: # F_T = S_T at maturity
                    self.lattice[option][period] = underlying.lattice[option][period]
                else:
                    rfp = sec_par.rfp
                    self.lattice[option][period] = self.back_prop(option, period, rfp)



class Shares(Lattice):
    ''' Shares lattice / subclass of Lattice'''
    def __init__(self, sec_par):
        Lattice.__init__(self, sec_par.n_periods)
        self._build(sec_par)


    def _build(self, sec_par):
        self.lattice[0][0] = sec_par.init
        for period in range(1, self.size+1):
            for share in range(0, period+1):
                if share == 0:
                    s_prev = self.lattice[share][period-1]
                    self.lattice[share][period] = sec_par.r_ud[1]*s_prev
                else:
                    s_prev = self.lattice[share-1][period-1]
                    self.lattice[share][period] = sec_par.r_ud[0]*s_prev



def results_to_stdout():
    '''Prints results to screen'''
    sec.print_summary()
    print()
    options.print_summary()
    options.price_to_stdout()


if __name__ == '__main__':
    # Load parameters
    sec = SecurityParameters()

    sec.echo_model_parameters()
    sec.echo_risk_free_probability()

    # Security lattice
    shares = Shares(sec)

    # Futures lattice
    if FUTURES_FLAG:
        futures = Futures(shares, sec)

    # Options lattice
    if FUTURES_FLAG:
        options = Options(futures, sec)
    else:
        options = Options(shares, sec)

    if LATTICE_FLAG:
        shares.lattice_to_stdout('Shares')
        if FUTURES_FLAG:
            futures.lattice_to_stdout('Futures')
        options.lattice_to_stdout('Options')

    results_to_stdout()
