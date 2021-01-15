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
r_ud = [1.25, .9]
rnp  = [.5, .5] # risk-neutral probabilities
N    = 5

# ZCB PARAMETERS
ZCB_MAT = 4

# Option parameters
K    = 88.0 # strike price
OPT  = 'put' # call or put option
TYPE = 'American' # option type: european or american
EXPO = 3 # expiration - accomodates diff w/ #periods in lattice (EXPO<=N)


class TermStructureParameters:
    '''Encapsulates parameters for the underlying security'''
    # pylint: disable=too-few-public-methods

    def __init__(self):
        self.init      = R_00
        self.n_periods = N
        self.r_ud      = r_ud
        self.rnp       = rnp

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
                    self.lattice[share][period] = sec_par.r_ud[1]*s_prev
                else:
                    s_prev = self.lattice[share-1][period-1]
                    self.lattice[share][period] = sec_par.r_ud[0]*s_prev



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



if __name__ == '__main__':
    # Load underlying security-related parameters
    term_st    = TermStructureParameters()
    short_rate = ShortRate(term_st)
    short_rate.lattice_to_stdout('Short-rate', True)

    zcb = ZCB(short_rate, term_st)
    zcb.lattice_to_stdout('ZCB')

    option_params = op.OptionParameters(OPT, TYPE, K, EXPO)
    opt = op.Options(zcb, term_st, option_params)
    opt.lattice_to_stdout('Zero option value')
