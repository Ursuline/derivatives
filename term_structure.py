#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 15 11:33:54 2021

@author: charles mégnin
"""

# import math
# import pandas as pd
import options as op

#### PARAMETERS ####
LATTICE_FLAG = True # print lattice to stdout

# Lattice parameters:
R_00 = .06 # initial price
R_UD = [1.25, .9]
RNP  = [.5, .5] # risk-neutral probabilities
N    = 5

# ZCB PARAMETERS
ZCB_MAT = 4

# Option parameters
K    = 84.0 # strike price
OPT  = 'put' # call or put option
TYPE = 'european' # option type: european or american
EXPO = 2 # expiration - accomodates diff w/ #periods in lattice (EXPO<=N)


class TermStructureParameters:
    '''Encapsulates parameters for the underlying security'''
    # pylint: disable=too-few-public-methods

    def __init__(self):
        self.init      = R_00
        self.n_periods = N
        self.r_ud      = R_UD
        self.rnp       = RNP

    def describe(self):
        ''' Prints summary parameters to stdout '''
        print(f'Initial price: {self.init}')
        print(f'{self.n_periods} periods')
        print(f'RUp-down rate: {self.r_ud}')
        print(f'Risk-neutral probability: {self.rnp}')



class ShortRate(op.Lattice):
    ''' Short rate lattice / subclass of Lattice'''
    def __init__(self, sec_par):
        super().__init__(sec_par.n_periods)
        self._build(sec_par)


    def _build(self, sec_par): # build the lattice
        self.lattice[0][0] = sec_par.init
        for period in range(1, self.size+1):
            for share in range(0, period+1):
                if share == 0:
                    s_prev = self.lattice[share][period-1]
                    self.lattice[share][period] = sec_par.r_ud[1] * s_prev
                else:
                    s_prev = self.lattice[share-1][period-1]
                    self.lattice[share][period] = sec_par.r_ud[0] * s_prev



class ZCB(op.Lattice):
    '''Zero-coupon bond lattice / subclass of Lattice'''
    def __init__(self, sh_rate, ts_par):
        self.bond_maturity = ZCB_MAT
        super().__init__(self.bond_maturity)
        self._build(sh_rate, ts_par)

    def _build(self, sh_rate, ts_par): # build the lattice
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    self.lattice[state][period] = 100.
                else:
                    p_1 = self.lattice[state+1][period+1]
                    p_2 = self.lattice[state][period+1]
                    num = ts_par.rnp[0] * p_1 + ts_par.rnp[1] * p_2
                    denom = 1 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom



class ZCBOptions(op.Options):
    ''' Options for Zero coupon bonds / Subclass of Options '''


    def build(self, underlying, ts_par, opt_par, sh_rate):
        ''' Over rides Options build method '''
        self._set_option_flags(opt_par)
        strike = opt_par.strike
        flag   = self.flags[0]
        rnp    = ts_par.rnp
        print(strike, flag, rnp, self.size)

        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    comp = max(0., flag*(underlying.lattice[state][period]-strike))
                    self.lattice[state][period] = comp
                else :
                    if self.flags[1] == 'E': # european options
                        p_1 = self.lattice[state+1][period+1]
                        p_2 = self.lattice[state][period+1]
                        num = rnp[0] * p_1 + rnp[1] * p_2
                        denom = 1. + sh_rate.lattice[state][period]
                        self.lattice[state][period] = num / denom
                    else: # american options
                        pass



def print_results(sec_p, opt_p, opt):
    '''Prints final results to screen'''

    print('\n*** Option price from security ***\n')
    sec_p.describe()
    print()
    opt_p.describe()
    opt.print_price()


if __name__ == '__main__':
    # Load underlying security-related parameters
    term_st    = TermStructureParameters()
    short_rate = ShortRate(term_st)
    short_rate.print_lattice('Short-rate', True)

    zcb = ZCB(short_rate, term_st)
    zcb.print_lattice('ZCB')

    option_params = op.OptionParameters(OPT, TYPE, K, EXPO)
    opt = ZCBOptions(option_params)
    opt.build(zcb, term_st, option_params, short_rate)
    opt.print_lattice('Zero option value')

    print_results(term_st, option_params, opt)
