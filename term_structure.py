#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 15 11:33:54 2021

This follows the nomenclature of
Financial Engineering and Risk Management Part I chapter 5
Binomial lattice models of the short-rate;
pricing fixed income derivatives, caplets, floorlets

on Coursera
https://www.coursera.org/learn/financial-engineering-1/home/welcome

@author: charles mégnin
"""

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

# CAPLETS/FLOORLETS PARAMETERS
LIBOR   = .02
CF_EXP  = 6
CF_TYPE = 'caplet' # either of caplet or floorlet
ARREARS = True # should probably be left as True

# Option parameters
K    = 88.0 # strike price
OPT  = 'put' # call or put option
TYPE = 'american' # option type: european or american
EXPO = 3 # expiration - accomodates diff w/ #periods in lattice (EXPO<=N)


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
                        # Exercise value:
                        e_val = flag*(underlying.lattice[state][period]-strike)

                        num   = rnp[0]*self.lattice[state+1][period+1]
                        num  += rnp[1]*self.lattice[state][period+1]
                        denom = 1. + sh_rate.lattice[state][period]
                        c_val = num / denom

                        self.lattice[state][period] = max(e_val, c_val)

        def describe():
            print('\n*** Option price from security ***\n')
            ts_par.describe()
            print()
            opt_par.describe()
            self.print_price()



class CFParameters():
    def __init__(self):
        self.libor = LIBOR
        self.matur = CF_EXP
        self.type  = DERIVATIVE
        self.arrears = ARREARS


    def describe(self):
        ''' Prints summary parameters to stdout '''
        print(f'Derivative: {self.type}')
        print(f'Maturity: {self.matur} periods')
        print(f'LIBOR rate: {self.libor}')



class CapFloorLet(op.Lattice):
    ''' Options for caplets & floorlets / Subclass of Lattice '''

    def __init__(self, cf_parameters):
        self.cf_parameters = cf_parameters
        self.matur         = self.cf_parameters.matur
        self.libor         = self.cf_parameters.libor
        self.type          = self.cf_parameters.type
        super().__init__(self.matur)
        if self.cf_parameters.arrears == True:
            self.size -= 1
        self._set_option_flags()


    def _set_option_flags(self):
        '''Sets option flags for call/put & european/american'''
        if str.lower(self.type) == 'caplet':
            self.flag = 1.0
        elif str.lower(self.type) != 'floorlet':
            self.flag = -1.0
        else:
            raise Exception(f'DERIVATIVE should be "caplet" or "floorlet". Its value is: "{self.type}"')


    def build(self, ts_par, sh_rate):
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    num = sh_rate.lattice[state][period] - self.libor
                    denom = 1 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom
                else:
                    num  = ts_par.rnp[0] * self.lattice[state + 1][period + 1]
                    num += ts_par.rnp[1] * self.lattice[state][period + 1]
                    denom = 1 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom


    def describe(self):
        print('\n*** Option price from security ***\n')
        self.cf_parameters.describe()
        self.print_price(True)



if __name__ == '__main__':
    # Load underlying security-related parameters
    DERIVATIVE = 'caplet' # either of zcb, caplet or floorlet

    term_params = TermStructureParameters()
    short_rates = ShortRate(term_params)
    short_rates.print_lattice('Short-rate', True)

    if DERIVATIVE == 'zcb':
        zcb = ZCB(short_rates, term_params)
        zcb.print_lattice('ZCB')

        option_params = op.OptionParameters(OPT, TYPE, K, EXPO)
        opt = ZCBOptions(option_params)
        opt.build(zcb, term_params, option_params, short_rates)
        opt.print_lattice('Zero option value')
        zcb.describe()
    elif DERIVATIVE == 'caplet' or DERIVATIVE == 'floorlet':
        cf_params = CFParameters()
        cf_let = CapFloorLet(cf_params)
        cf_let.build(term_params, short_rates)
        cf_let.print_lattice('Caplet', True)
        cf_let.describe()
    else:
        raise Exception(f'DERIVATIVE should be "zcb", "caplet" or "floorlet". Its value is: "{DERIVATIVE}"')


