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
import lattice as lt
import options as op

#### PARAMETERS ####

# Lattice parameters:
R_00 = .06 # initial price
R_UD = [1.25, .9]
RNP  = [.5, .5] # risk-neutral probabilities
NPER = 5

# ZCB PARAMETERS
ZCB_NPER = 4

#SWAP PARAMETERS
FIXED_RATE   = .05
SWAP_NPER    = 6
SWAP_ARREARS = True # should be left as True

# CAPLETS/FLOORLETS PARAMETERS
LIBOR      = .1
CF_NPER    = 6
CF_ARREARS = True # should be left as True

# Option parameters
K       = 88.0 # strike price
OPT     = 'put' # call or put option
TYPE    = 'american' # option type: european or american
OP_NPER = 3 # expiration - accomodates diff w/ #periods in lattice (EXPO<=N)


class SWAPParameters(lt.Parameters):
    '''Encapsulates parameters for swaps'''

    def __init__(self):
        self.arrears    = SWAP_ARREARS
        super().__init__(SWAP_NPER, FIXED_RATE)


    def describe(self):
        ''' Prints summary parameters to stdout '''
        print(f'Fixed rate: {self.rate}')
        super().describe('Fixed')



class TermStructureParameters(lt.Parameters):
    '''Encapsulates parameters for the underlying security'''
    # pylint: disable=too-few-public-methods

    def __init__(self):
        self.init  = R_00
        self.r_ud  = R_UD
        self.rnp   = RNP
        super().__init__(NPER)

    def describe(self):
        ''' Prints summary parameters to stdout '''
        print(f'Initial price: {self.init}')
        print(f'Up-down rate: {self.r_ud}')
        print(f'Risk-neutral probability: {self.rnp}')
        super().describe()



class CFParameters(lt.Parameters):
    '''Parameters for caplets/floorlets'''
    def __init__(self):
        #self.libor  = LIBOR
        self.type    = DERIVATIVE
        self.arrears = CF_ARREARS
        super().__init__(CF_NPER, LIBOR)


    def describe(self):
        ''' Prints summary parameters to stdout '''
        print(f'Derivative: {self.type}')
        print(f'LIBOR rate: {self.rate}')
        super().describe('LIBOR')



class ShortRate(lt.Lattice):
    ''' Short rate lattice '''
    def __init__(self, sec_par):
        super().__init__(sec_par.nperiods)
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



class ZCB(lt.Lattice):
    ''' Zero-coupon bond lattice '''
    def __init__(self, sh_rate, ts_par):
        self.nperiods = ZCB_NPER
        super().__init__(self.nperiods)
        self._build(sh_rate, ts_par)

    def _build(self, sh_rate, ts_par): # build the lattice
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    self.lattice[state][period] = 100.
                else:
                    num = self.back_prop(state, period, ts_par.rnp)
                    denom = 1 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom

    def describe(self):
        '''Self-descriptor'''
        print('\n*** Zero-coupon bond price ***\n')
        #self.swap_parameters.describe()
        self.print_price(True)



class ZCBOptions(op.Options):
    ''' Options for Zero coupon bonds / Subclass of Options '''

    def __init__(self, ts_par, opt_par):
        self.term_parameters   = ts_par
        self.option_parameters = opt_par
        super().__init__(opt_par.nperiods)

    def build(self, underlying, sh_rate):
        ''' Over rides Options build method '''
        self._set_option_flags(self.option_parameters)
        strike = self.option_parameters.strike
        flag   = self.flags[0]
        rnp    = self.term_parameters.rnp
        print(strike, flag, rnp, self.size)

        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    comp = max(0., flag*(underlying.lattice[state][period]-strike))
                    self.lattice[state][period] = comp
                else :
                    if self.flags[1] == 'E': # european options
                        num = self.back_prop(state, period, rnp)
                        denom = 1. + sh_rate.lattice[state][period]
                        self.lattice[state][period] = num / denom
                    else: # american options
                        # Exercise value:
                        e_val = flag*(underlying.lattice[state][period]-strike)
                        num = self.back_prop(state, period, rnp)
                        denom = 1.0 + sh_rate.lattice[state][period]
                        c_val = num / denom

                        self.lattice[state][period] = max(e_val, c_val)

    def describe(self):
        '''Self-descriptor'''
        print('\n*** Option price from security ***\n')
        self.term_parameters.describe()
        print()
        self.option_parameters.describe()
        self.print_price()



class CapFloorLet(lt.Lattice):
    ''' caplets & floorlets / Subclass of Lattice '''

    def __init__(self, cf_parameters):
        self.cf_parameters = cf_parameters
        self.matur         = self.cf_parameters.matur
        self.libor         = self.cf_parameters.libor
        self.type          = DERIVATIVE
        super().__init__(self.matur)
        if self.cf_parameters.arrears:
            self.size -= 1
        self._set_option_flags()


    def _set_option_flags(self):
        '''Sets option flags for call/put & european/american'''
        if str.lower(self.type) == 'caplet':
            self.flag = 1.0
        elif str.lower(self.type) == 'floorlet':
            self.flag = -1.0
        else:
            raise Exception(f'DERIVATIVE should be "caplet" or "floorlet". Its value is: "{self.type}"')


    def build(self, ts_par, sh_rate):
        ''' build the caplet/floorlet lattice'''
        flag = self.flag # caplet or floorlet
        rate = self.libor
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    num = flag*(sh_rate.lattice[state][period] - rate)
                    denom = 1 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom
                else:
                    num = self.back_prop(state, period, ts_par.rnp)
                    denom = 1.0 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom


    def describe(self):
        '''Self-descriptor'''
        print('\n*** Caplet/floorlet price ***\n')
        self.cf_parameters.describe()
        self.print_price(True)


class SWAP(lt.Lattice):
    '''Swap lattice '''
    def __init__(self, swap_par):
        self.swap_parameters = swap_par
        super().__init__(swap_par.nperiods)
        if self.swap_parameters.arrears:
            self.size -= 1


    def build(self, ts_par, sh_rate): # build the lattice
        '''Build the swap lattice'''
        rate = self.swap_parameters.rate
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    num  = sh_rate.lattice[state][period] - rate
                    denom = 1.0 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom
                else:
                    num  = sh_rate.lattice[state][period] - rate
                    num += self.back_prop(state, period, ts_par.rnp)
                    denom = 1.0 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom


    def describe(self):
        '''Self-descriptor'''
        print('\n*** Swap price ***\n')
        self.swap_parameters.describe()
        self.print_price(True)



if __name__ == '__main__':
    DERIVATIVE   = 'swap' # either of zcb, caplet, floorlet, swap or swaption
    LATTICE_FLAG = True # print lattice to stdout

    DERIVATIVE = str.lower(DERIVATIVE)

    # Load underlying security-related parameters
    term_params = TermStructureParameters()
    short_rates = ShortRate(term_params)
    short_rates.print_lattice('Short-rate', True)

    if DERIVATIVE == 'zcb':
        zcb = ZCB(short_rates, term_params)
        zcb.print_lattice('ZCB')

        option_params = op.OptionParameters(OPT, TYPE, K, OP_NPER)
        opt = ZCBOptions(term_params, option_params)
        opt.build(zcb, short_rates)
        if LATTICE_FLAG:
            opt.print_lattice('Zero option value')
        zcb.describe()
    elif DERIVATIVE in ('caplet','floorlet'):
        cf_params = CFParameters()
        cf_let = CapFloorLet(cf_params)
        cf_let.build(term_params, short_rates)
        if LATTICE_FLAG:
            cf_let.print_lattice(str.capitalize(DERIVATIVE), True)
        cf_let.describe()
    elif DERIVATIVE == 'swap':
        swap_params = SWAPParameters()
        swap = SWAP(swap_params)
        swap.build(term_params, short_rates)
        if LATTICE_FLAG:
            swap.print_lattice(str.capitalize(DERIVATIVE), True)
        swap.describe()

    else:
        raise Exception(f'DERIVATIVE should be "zcb", "caplet" or "floorlet". Its value is: "{DERIVATIVE}"')
