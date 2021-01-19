#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 12 13:44:57 2021

Computes the price of european and american call & put options
for shares or futures

This follows the nomenclature of
Financial Engineering and Risk Management Part I chapter 4
on Coursera
https://www.coursera.org/learn/financial-engineering-1/home/welcome

@author: charles mégnin
"""
import math
import lattice as lt

#### PARAMETERS ####
PRINT_LATTICES = True # print lattices to stdout

# Lattice parameters:
S0    = 100.0 # initial price
T_YRS = 0.25 # maturity (years)
SIGMA = 0.3 # volat
NPER  = 15 # number of periods
R     = 0.02 # risk-free rate
DIV   = 0.01 # dividend yield

# Option parameters
K       = 110.0 # strike price
OPT     = 'put' # call or put option
TYPE    = 'european' # option type: european or american
OP_NPER = 15 # expiration - accomodates diff w/ #periods in lattice (EXPO<=N)

# Futures parameters
#EXPF = 10 # expiration
#### END PARAMETERS ####


#### UNDERLYING SECURITY ####
class SecurityParameters(lt.Parameters):
    '''Encapsulates parameters for the underlying security'''
    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self.init      = S0
        self.matur     = T_YRS
        self.volat     = SIGMA
        self.dividend  = DIV
        super().__init__(NPER, R)

        self._set_up_down_rates()
        self._set_risk_neutral_proba()


    def _set_up_down_rates(self):
        ''' Computes binomial model parameters u & d=1/u
            u=r_ud[0] d=r_ud[1]
            Convert Black-Scholes / calibrate a binomial model '''
        self.r_ud = [0., 0.]
        exponent  = self.volat * math.sqrt(self.matur / self.nperiods)
        self.r_ud[0] = math.exp(exponent)
        self.r_ud[1] = 1.0 / self.r_ud[0]


    def _set_risk_neutral_proba(self):
        ''' Computes risk-neutral probability rnp[0]=q rnp[1]=1-q
            from parameters u & d in r_ud '''
        self.rnp = [0., 0.]
        exponent = (self.rate - self.dividend) * self.matur / self.nperiods
        num      = math.exp(exponent)
        num      = num - self.r_ud[1]
        denom    = self.r_ud[0] - self.r_ud[1]
        self.rnp[0] = num / denom
        self.rnp[1] = 1.0 - self.rnp[0]


    def describe(self):
        ''' Prints summary parameters to stdout '''
        print('*** Security parameters ***')
        print(f'Initial price: {self.init}')
        print(f'Risk-free rate: {100*self.rate:.2f}%')
        print(f'Dividend yield: {100*self.dividend:.2f}%')
        print(f'Volatility: {100*self.volat:.2f}%')
        print(f'u = {self.r_ud[0]:.5f} / d = {self.r_ud[1]:.5f}')
        print(f'q = {self.rnp[0]:.5f} / 1-q = {self.rnp[1]:.5f}')
        super().describe()



class Shares(lt.Lattice):
    ''' Shares lattice / subclass of Lattice'''
    def __init__(self, sec_par):
        self.sec_parameters = sec_par
        super().__init__(self.sec_parameters.nperiods)


    def build(self):
        ''' Build the lattice '''
        self.lattice[0][0] = self.sec_parameters.init
        for period in range(1, self.size+1):
            for state in range(0, period+1):
                if state == 0:
                    s_prev = self.lattice[state][period-1]
                    self.lattice[state][period] = self.sec_parameters.r_ud[1] * s_prev
                else:
                    s_prev = self.lattice[state-1][period-1]
                    self.lattice[state][period] = self.sec_parameters.r_ud[0] * s_prev


#### OPTION ####
class OptionParameters(lt.Parameters):
    '''Encapsulates parameters for the option'''
    def __init__(self, opt, option_type, strike, nperiods):
        self.opt    = opt
        self.type   = option_type
        self.strike = strike
        super().__init__(nperiods)


    def describe(self):
        '''Prints summary options parameters to std out'''
        print(f'{str.capitalize(self.type)} {self.opt} option')
        print(f'Strike price={self.strike}')



class Options(lt.Lattice):
    ''' Options lattice / subclass of Lattice
        underlying is lattice of either security or futures '''
    def __init__(self, opt_par):
        self.option_parameters = opt_par
        self.flags             = [1.0, 'E']
        super().__init__(opt_par.nperiods)


    def build(self, underlying, sec_par):
        ''' build the lattice '''
        self._set_option_flags(self.option_parameters)

        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                comp = underlying.lattice[state][period] - self.option_parameters.strike
                if period == self.size:
                    self.lattice[state][period] = max(self.flags[0]*comp, 0.)
                else:
                    num    = self._back_prop(state, period, sec_par.rnp)
                    denom  = math.exp(sec_par.rate * sec_par.matur/self.size)
                    ratio  = num/denom
                    ex_val = -comp # exercise value

                    if self.flags[1] == 'E':
                        self.lattice[state][period] = ratio
                    else: # American option
                        self.lattice[state][period] = max(ex_val, ratio)
                        if ex_val > ratio:
                            print(f'Exercizing option {state}/t={period} {ex_val:.2f}>{ratio:.2f}')


    def _set_option_flags(self, opt_par):
        '''Sets option flags for call/put & european/american'''
        if str.lower(opt_par.opt) == 'put':
            self.flags[0] = -1.0
        elif str.lower(opt_par.opt) != 'call':
            raise Exception(f'OPT should be "call" or "put". Its value is: "{OPT}"')
        if str.lower(opt_par.type) == 'american':
            self.flags[1] = 'A'
        elif str.lower(opt_par.type) != 'european':
            raise Exception(f'TYPE should be "european" or "american". Value is: "{opt_par.type}"')


#### FUTURES ####
class Futures(lt.Lattice):
    ''' Shares lattice / subclass of Lattice'''
    def __init__(self, sec_par):
        self.sec_par = sec_par
        super().__init__(sec_par.nperiods)


    def build(self, underlying):
        ''' build the lattice '''
        rnp = self.sec_par.rnp
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size: # F_T = S_T at maturity
                    self.lattice[state][period] = underlying.lattice[state][period]
                else:
                    self.lattice[state][period] = self._back_prop(state, period, rnp)



if __name__ == '__main__':
    FUTURES_FLAG   = False # Optionally compute options from futures

    # Load underlying security-related parameters
    security_params = SecurityParameters()

    # Build lattice for underlying security
    shares = Shares(security_params)
    shares.build()

    # Optionally build lattice for futures
    if FUTURES_FLAG:
        futures = Futures(security_params)
        futures.build(shares)

    # Build lattice for options
    option_params = OptionParameters(OPT, TYPE, K, OP_NPER)
    options    = Options(option_params)
    if FUTURES_FLAG: # build options lattice from futures
        options.build(futures, security_params)
    else: # build options lattice from underlying security
        options.build(shares, security_params)

    if PRINT_LATTICES: # print lattices to screen if flag set
        shares.display_lattice('Shares')
        if FUTURES_FLAG:
            futures.display_lattice('Futures')
        options.display_lattice('Options')

    # Print final result to screen
    security_params.describe()
    if FUTURES_FLAG:
        options.describe('Option (from futures)', option_params, False)
    else:
        options.describe('Option (from security)', option_params, False)
