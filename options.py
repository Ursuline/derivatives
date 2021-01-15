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
FUTURES_FLAG = False # Compute options from futures

# Lattice parameters:
S0   = 100.0 # initial price
T    = 0.25 # maturity (years)
SIG  = 0.3 # volat
N    = 15 # number of periods
R    = 0.02 # risk-free rate
D    = 0.01 # dividend yield

# Option parameters
K    = 110.0 # strike price
OPT  = 'put' # call or put option
TYPE = 'American' # option type: european or american
EXPO = 15 # expiration - accomodates diff w/ #periods in lattice (EXPO<=N)

# Futures parameters
#EXPF = 10 # expiration
#### END PARAMETERS ####

class SecurityParameters:
    '''Encapsulates parameters for the underlying security'''
    # pylint: disable=too-many-instance-attributes

    def __init__(self):
        self.init      = S0
        self.matur     = T
        self.volat     = SIG
        self.n_periods = N
        self.rate      = R
        self.dividend  = D

        self._set_binomial_model_parameter()
        self._set_risk_free_proba()


    def _set_binomial_model_parameter(self):
        ''' Computes binomial model parameters u & d=1/u
            u=r_ud[0] d=r_ud[1]
            Convert Black-Scholes / calibrate a binomial model'''
        self.r_ud = [0., 0.]
        exponent  = self.volat * math.sqrt(self.matur / self.n_periods)
        self.r_ud[0] = math.exp(exponent)
        self.r_ud[1] = 1.0 / self.r_ud[0]


    def _set_risk_free_proba(self):
        '''Computes risk-free probability rfp=q from parameters u & d in r_ud'''
        exponent = (self.rate - self.dividend) * self.matur / self.n_periods
        num      = math.exp(exponent)
        num      = num - self.r_ud[1]
        denom    = self.r_ud[0] - self.r_ud[1]
        self.rfp = num / denom


    def print_summary(self):
        '''Prints summary parameters to stdout'''
        print(f'Initial price: {self.init}')
        print(f'Maturity: {self.matur} years / {self.n_periods} periods')
        print(f'Risk-free rate: {100*self.rate:.2f}%')
        print(f'Dividend yield: {100*self.dividend:.2f}%')
        print(f'Volatility: {100*self.volat:.2f}%')


    def echo_model_parameters(self):
        '''Prints u & d to stdout'''
        print(f'u = {self.r_ud[0]:.5f} / d = {self.r_ud[1]:.5f}')


    def echo_risk_free_probability(self):
        '''prints risk-free probability q to stdout'''
        print(f'q = {self.rfp:.5f} / 1-q = {1-self.rfp:.5f}')



class Lattice:
    ''' Lattice superclass encapsulates parameters and functionality
        common to Shares, Options and Futures classes'''
    def __init__(self, size):
        # build a size x size list populated with 0
        self.lattice = [['' for x in range(size+1)] for y in range(size+1)]
        self.size = size


    def back_prop(self, row, column, proba):
        ''' returns q*S^(i+1)_(t+1) + (1-q)*S^i_(t+1)
            q = proba / S = lattice'''
        p_1 = self.lattice[row + 1][column + 1] # S^(i+1)_(t+1)
        p_2 = self.lattice[row][column + 1]     # S^i_(t+1)

        return p_1*proba + p_2*(1. - proba)


    def lattice_to_stdout(self, title, percent_flag=False):
        '''Prints lattice to stdout'''
        print(f'{title} lattice:')
        df = pd.DataFrame(self.lattice)
        # Format output
        if percent_flag:
            pd.options.display.float_format = '{:.2%}'.format
            print(df.loc[::-1])
        else:
            pd.options.display.float_format = '{:.2f}'.format
            print(df.loc[::-1])


    def price_to_stdout(self):
        '''Prints derivative price to stdout'''
        print(f'C0={self.lattice[0][0]:.2f}')



class Options(Lattice):
    ''' Options lattice / subclass of Lattice
        underlying is lattice of either security or futures
    '''
    def __init__(self, underlying, sec_par):
        self.type   = TYPE
        self.opt    = OPT
        self.strike = K
        self.expir  = EXPO
        super().__init__(self.expir)
        self._set_option_flags()
        self._build(underlying, sec_par)


    def _build(self, underlying, sec_par): # build the lattice
        strike = self.strike
        flag   = self.flags[0]
        rfp    = sec_par.rfp

        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if state == self.size:
                    comp = underlying.lattice[state][period]-strike
                    self.lattice[state][period] = max(flag*comp, 0.)
                else:
                    num   = self.back_prop(state, period, rfp)
                    denom = math.exp(sec_par.rate*sec_par.matur/self.size)
                    ratio = num/denom
                    # exercise value
                    ex_val = strike - underlying.lattice[state][period]

                    if self.flags[1] == 'E':
                        self.lattice[state][period] = ratio
                    else: # American option
                        self.lattice[state][period] = max(ex_val, ratio)
                        if ex_val > ratio:
                            print(f'Exercizing option {option}/t={period} {ex_val:.2f}>{ratio:.2f}')


    def _set_option_flags(self):
        '''Sets option flags for call/put & european/american'''
        self.flags  = [1.0, 'E']
        if str.lower(self.opt) == 'put':
            self.flags[0] = -1.0
        elif str.lower(self.opt) != 'call':
            raise Exception(f'OPT should be "call" or "put". Its value is: "{OPT}"')
        if str.lower(self.type) == 'american':
            self.flags[1] = 'A'
        elif str.lower(self.type) != 'european':
            raise Exception(f'TYPE should be "european" or "american". Its value is: "{TYPE}"')


    def print_summary(self):
        '''Prints summary options parameters to std out'''
        print(f'{str.capitalize(self.type)} {self.opt} option')
        print(f'Strike price={self.strike}')
        print(f'Expiration: {self.expir} periods\n')



class Futures(Lattice):
    ''' Shares lattice / subclass of Lattice'''
    def __init__(self, underlying, sec_par):
        super().__init__(sec_par.n_periods)
        self._build(underlying, sec_par)


    def _build(self, underlying, sec_par): # build the lattice
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size: # F_T = S_T at maturity
                    self.lattice[state][period] = underlying.lattice[state][period]
                else:
                    rfp = sec_par.rfp
                    self.lattice[state][period] = self.back_prop(state, period, rfp)



class Shares(Lattice):
    ''' Shares lattice / subclass of Lattice'''
    def __init__(self, sec_par):
        super().__init__(sec_par.n_periods)
        self._build(sec_par)


    def _build(self, sec_par): # build the lattice
        self.lattice[0][0] = sec_par.init
        for period in range(1, self.size+1):
            for state in range(0, period+1):
                if share == 0:
                    s_prev = self.lattice[state][period-1]
                    self.lattice[state][period] = sec_par.r_ud[1]*s_prev
                else:
                    s_prev = self.lattice[state-1][period-1]
                    self.lattice[state][period] = sec_par.r_ud[0]*s_prev



def results_to_stdout():
    '''Prints final results to screen'''
    if FUTURES_FLAG:
        print('\n*** Option price from futures ***\n')
    else:
        print('\n*** Option price from security ***\n')
    sec.print_summary()
    print()
    options.print_summary()
    options.price_to_stdout()


if __name__ == '__main__':
    # Load underlying security-related parameters
    sec = SecurityParameters()

    # Display security-derived parameters (check)
    sec.echo_model_parameters()
    sec.echo_risk_free_probability()

    # Build lattice for underlying security
    shares = Shares(sec)

    # Optionally build lattice for futures
    if FUTURES_FLAG:
        futures = Futures(shares, sec)

    # Build lattice for options
    if FUTURES_FLAG: # build options lattice from futures
        options = Options(futures, sec)
    else: # build options lattice from underlying security
        options = Options(shares, sec)

    if LATTICE_FLAG: # print lattices to sceen if flag set
        shares.lattice_to_stdout('Shares')
        if FUTURES_FLAG:
            futures.lattice_to_stdout('Futures')
        options.lattice_to_stdout('Options')

    # Print final rresult to screen
    results_to_stdout()
