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

class OptionParameters:
    '''Encapsulates parameters for the option'''
    def __init__(self, opt, option_type, strike, expiration):
        self.opt    = opt
        self.type   = option_type
        self.strike = strike
        self.expir  = expiration


    def print_parameters(self):
        ''' Print all parameters in class '''
        print(f'\nclass parameters:{self.__dict__}')


    def print_summary(self):
        '''Prints summary options parameters to std out'''
        print(f'{str.capitalize(self.type)} {self.opt} option')
        print(f'Strike price={self.strike}')
        print(f'Expiration: {self.expir} periods\n')



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
        self._set_risk_neutral_proba()


    def _set_binomial_model_parameter(self):
        ''' Computes binomial model parameters u & d=1/u
            u=r_ud[0] d=r_ud[1]
            Convert Black-Scholes / calibrate a binomial model '''
        self.r_ud = [0., 0.]
        exponent  = self.volat * math.sqrt(self.matur / self.n_periods)
        self.r_ud[0] = math.exp(exponent)
        self.r_ud[1] = 1.0 / self.r_ud[0]


    def _set_risk_neutral_proba(self):
        ''' Computes risk-neutral probability rnp[0]=q rnp[1]=1-q
            from parameters u & d in r_ud '''
        self.rnp = [0., 0.]
        exponent = (self.rate - self.dividend) * self.matur / self.n_periods
        num      = math.exp(exponent)
        num      = num - self.r_ud[1]
        denom    = self.r_ud[0] - self.r_ud[1]
        self.rnp[0] = num / denom
        self.rnp[1] = 1.0 - self.rnp[0]


    def print_parameters(self):
        ''' Print all parameters in class '''
        print(f'\nclass parameters:{self.__dict__}')


    def print_summary(self):
        ''' Prints summary parameters to stdout '''
        print(f'Initial price: {self.init}')
        print(f'Maturity: {self.matur} years / {self.n_periods} periods')
        print(f'Risk-free rate: {100*self.rate:.2f}%')
        print(f'Dividend yield: {100*self.dividend:.2f}%')
        print(f'Volatility: {100*self.volat:.2f}%')


    def print_model_parameters(self):
        ''' Prints u & d to stdout '''
        print(f'u = {self.r_ud[0]:.5f} / d = {self.r_ud[1]:.5f}')


    def print_risk_neutral_probability(self):
        ''' Prints risk-free probability q to stdout '''
        print(f'q = {self.rnp[0]:.5f} / 1-q = {self.rnp[1]:.5f}')



class Lattice:
    ''' Lattice superclass encapsulates parameters and functionality
        common to Shares, Options and Futures classes'''
    def __init__(self, size):
        # build a size x size list populated with 0
        self.lattice = [['' for x in range(size+1)] for y in range(size+1)]
        self.size = size


    def back_prop(self, row, column, rnp):
        ''' returns q*S^(i+1)_(t+1) + (1-q)*S^i_(t+1)
            q = proba / S = lattice'''
        p_1 = self.lattice[row + 1][column + 1] # S^(i+1)_(t+1)
        p_2 = self.lattice[row][column + 1]     # S^i_(t+1)

        return p_1 * rnp[0] + p_2 * rnp[1]


    def lattice_to_stdout(self, title, percent_flag=False):
        '''Prints lattice to stdout'''
        print(f'{title} lattice:')
        dfr = pd.DataFrame(self.lattice)
        # Format output
        if percent_flag:
            pd.options.display.float_format = '{:.2%}'.format
            print(dfr.loc[::-1])
        else:
            pd.options.display.float_format = '{:.2f}'.format
            print(dfr.loc[::-1])


    def print_price(self):
        '''Prints derivative price to stdout'''
        print(f'C0={self.lattice[0][0]:.2f}')


    def print_parameters(self):
        ''' Print all parameters in class '''
        print(f'\nclass parameters:{self.__dict__}')



class Options(Lattice):
    ''' Options lattice / subclass of Lattice
        underlying is lattice of either security or futures
    '''
    def __init__(self, underlying, sec_par, opt_par):
        super().__init__(opt_par.expir)
        self._set_option_flags(opt_par)
        self._build(underlying, sec_par, opt_par)


    def _build(self, underlying, sec_par, opt_par): # build the lattice
        strike = opt_par.strike
        flag   = self.flags[0]
        rnp    = sec_par.rnp

        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    comp = underlying.lattice[state][period]-strike
                    self.lattice[state][period] = max(flag*comp, 0.)
                else:
                    num   = self.back_prop(state, period, rnp)
                    denom = math.exp(sec_par.rate*sec_par.matur/self.size)
                    ratio = num/denom
                    # exercise value
                    ex_val = strike - underlying.lattice[state][period]

                    if self.flags[1] == 'E':
                        self.lattice[state][period] = ratio
                    else: # American option
                        self.lattice[state][period] = max(ex_val, ratio)
                        if ex_val > ratio:
                            print(f'Exercizing option {state}/t={period} {ex_val:.2f}>{ratio:.2f}')


    def _set_option_flags(self, opt_par):
        '''Sets option flags for call/put & european/american'''
        self.flags  = [1.0, 'E']
        if str.lower(opt_par.opt) == 'put':
            self.flags[0] = -1.0
        elif str.lower(opt_par.opt) != 'call':
            raise Exception(f'OPT should be "call" or "put". Its value is: "{OPT}"')
        if str.lower(opt_par.type) == 'american':
            self.flags[1] = 'A'
        elif str.lower(opt_par.type) != 'european':
            raise Exception(f'TYPE should be "european" or "american". Its value is: "{TYPE}"')



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
                    rnp = sec_par.rnp
                    self.lattice[state][period] = self.back_prop(state, period, rnp)



class Shares(Lattice):
    ''' Shares lattice / subclass of Lattice'''
    def __init__(self, sec_par):
        super().__init__(sec_par.n_periods)
        self._build(sec_par)


    def _build(self, sec_par): # build the lattice
        self.lattice[0][0] = sec_par.init
        for period in range(1, self.size+1):
            for state in range(0, period+1):
                if state == 0:
                    s_prev = self.lattice[state][period-1]
                    self.lattice[state][period] = sec_par.r_ud[1]*s_prev
                else:
                    s_prev = self.lattice[state-1][period-1]
                    self.lattice[state][period] = sec_par.r_ud[0]*s_prev



def print_results(sec_p, op_p, opt):
    '''Prints final results to screen'''
    if FUTURES_FLAG:
        print('\n*** Option price from futures ***\n')
    else:
        print('\n*** Option price from security ***\n')
    sec_params.print_summary()
    print()
    opt_params.print_summary()
    options.print_price()


if __name__ == '__main__':
    # Load underlying security-related parameters
    sec_params = SecurityParameters()

    # Display security-derived parameters (check)
    sec_params.print_model_parameters()
    sec_params.print_risk_neutral_probability()

    # Build lattice for underlying security
    shares = Shares(sec_params)

    # Optionally build lattice for futures
    if FUTURES_FLAG:
        futures = Futures(shares, sec_params)

    # Build lattice for options
    opt_params = OptionParameters(OPT, TYPE, K, EXPO)
    if FUTURES_FLAG: # build options lattice from futures
        options = Options(futures, sec_params, opt_params)
    else: # build options lattice from underlying security
        options = Options(shares, sec_params, opt_params)

    if LATTICE_FLAG: # print lattices to sceen if flag set
        shares.lattice_to_stdout('Shares')
        if FUTURES_FLAG:
            futures.lattice_to_stdout('Futures')
        options.lattice_to_stdout('Options')

    # Print final rresult to screen
    print_results(sec_params, opt_params, options)
