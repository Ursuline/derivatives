#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 20 14:15:00 2021

This follows the nomenclature of
Financial Engineering and Risk Management Part I chapter 5
Binomial lattice models of the short-rate;
bond pricing

on Coursera
https://www.coursera.org/learn/financial-engineering-1/home/welcome

@author: charles mégnin
"""
import lattice as lt
import options as op

#### PARAMETERS ####
# Lattice parameters:
# TERM STRUCTURE
TS_R00  = .06 # initial price
TS_RUD  = [1.25, .9]
TS_RNP  = [.5, .5] # risk-neutral probabilities
TS_NPER = 5

# Option parameters
OP_K    = 84.0 # strike price
OPT     = 'call' # call or put option
OP_TYPE = 'european' # option type: european or american
OP_NPER = 4 # expiration - accomodates diff w/ #periods in lattice (EXPO<=N)

# BOND parameters
BOND_FACE = 100 # Bond face value normally 100
BOND_NPER = 6
BOND_COUPON = .1

# Forward/future parameters
FF_FACE = 100 # Bond face value normally 100
FF_NPER = 4
FF_TYPE = 'forward'

### Derivative selection to be set in main driver ###

### SHORT RATE LATTICE ###
class TermStructureParameters(lt.Parameters):
    ''' Encapsulates parameters for the underlying security
        Base parameters for all fixed income derivatives
    '''
    # pylint: disable=too-few-public-methods

    def __init__(self):
        self.init  = TS_R00
        self.r_ud  = TS_RUD
        self.rnp   = TS_RNP
        super().__init__(TS_NPER)


    def describe(self):
        ''' Prints summary parameters to stdout '''
        print(f'Initial price: {self.init:.2%}')
        print(f'Up-down rate: {self.r_ud}')
        print(f'Risk-neutral probability: {self.rnp}')
        super().describe()



class ShortRate(lt.Lattice):
    ''' Short rate lattice: base lattice for all fixed-income derivatives '''

    def __init__(self, term_structure_parameters):
        self.parameters = term_structure_parameters
        super().__init__(self.parameters.nperiods)
        self._build() # auto-build


    def _build(self): # build the lattice
        self.lattice[0][0] = self.parameters.init
        for period in range(1, self.size+1):
            for state in range(0, period+1):
                if state == 0:
                    s_prev = self.lattice[state][period-1]
                    self.lattice[state][period] = self.parameters.r_ud[1] * s_prev
                else:
                    s_prev = self.lattice[state-1][period-1]
                    self.lattice[state][period] = self.parameters.r_ud[0] * s_prev


    def describe(self):
        '''Self-descriptor'''
        super().describe('Interest rate term structure', self.parameters, True)



class ZCBOptions(op.Options):
    ''' Options for Zero coupon bonds / Subclass of Options '''

    def __init__(self, opt_params):
        self.rnp        = term_params.rnp
        self.parameters = opt_params
        super().__init__(self.parameters)


    def build(self, underlying, sh_rate):
        ''' Over rides Options build method '''
        self._set_option_flags(self.parameters)
        strike = self.parameters.strike

        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                e_val = self.flags[0]*(underlying.lattice[state][period]-strike)
                if period == self.size:
                    self.lattice[state][period] = max(0., e_val)
                else :
                    num   = self._back_prop(state, period, self.rnp)
                    denom = 1.0 + sh_rate.lattice[state][period]
                    c_val = num / denom
                    if self.flags[1] == 'E': # european options
                        self.lattice[state][period] = c_val
                    else: # american options
                        self.lattice[state][period] = max(e_val, c_val)


    def describe(self):
        '''Self-descriptor'''
        super().describe('Zero-coupon bond options', self.parameters, False)

### BONDS
class BondParameters(lt.Parameters):
    '''Parameters for caplets/floorlets'''
    def __init__(self, bond_face, bond_coupon, bond_nper):
        self.face   = bond_face
        self.coupon = bond_coupon
        super().__init__(bond_nper)


    def describe(self):
        ''' Prints summary parameters to stdout '''
        print(f'Face value: {self.face}')
        print(f'Coupon value: {self.coupon}')
        super().describe()



class Bond(lt.Lattice):
    def __init__(self, bond_parameters):
        self.parameters = bond_parameters
        super().__init__(self.parameters.nperiods)


    def build(self, term_par, sh_rate):
        ''' build the zero-coupon bond lattice'''
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    self.lattice[state][period]  = self.parameters.face
                    self.lattice[state][period] *= (1. + self.parameters.coupon)
                else:
                    num  = self._back_prop(state, period, term_par.rnp)
                    denom = 1 + sh_rate.lattice[state][period]
                    self.lattice[state][period]  = num / denom
                    self.lattice[state][period] += self.parameters.face*self.parameters.coupon


    def describe(self):
        '''Self-descriptor'''
        super().describe('Zero-coupon bond', self.parameters, False)



### BOND FORWARDS & FUTURES ###
class BondFFParameters(lt.Parameters):
    '''Parameters for Bond forwards & futures'''
    def __init__(self, ff_type, ff_coupon, ff_nperiods):
        if str.lower(ff_type) in ('forward', 'future'):
            self.type    = str.lower(ff_type)
        else:
            raise Exception(f'Invalid type: "{ff_type}"')
        self.coupon   = ff_coupon
        self.nperiods = ff_nperiods
        super().__init__(self.nperiods)


    def describe(self):
        '''Self-descriptor'''
        print(f'Bond type: {self.type}')
        print(f'Coupon: {self.coupon}')
        super().describe()



class BondFF(lt.Lattice):
    ''' Lattice for Forward & Futures on bonds '''
    def __init__(self, bond_params):
        self.parameters = bond_params
        super().__init__(self.parameters.nperiods)


    def build(self, ts_par, sh_rate, bond_l):
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    self.lattice[state][period]  = bond_l.lattice[state][period]
                    self.lattice[state][period] -= 100 * self.parameters.coupon
                else:
                    num   = self._back_prop(state, period, ts_par.rnp)
                    denom = 1.0
                    if self.parameters.type == 'forward':
                        denom += sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom

    def describe(self):
        '''Self-descriptor'''
        super().describe(self.parameters.type, self.parameters, False)


#### Driver ####
if __name__ == '__main__':
    ## Derivative selection ##
    # Set either of bondopt, bond, forward, future
    OPTION   = False
    LATTICE_FLAG = True # print lattice to stdout

    # Load underlying security-related parameters
    term_params = TermStructureParameters()
    short_rates = ShortRate(term_params)
    short_rates.display_lattice('Short-rate', True)

    bond = Bond(BondParameters(BOND_FACE, BOND_COUPON, BOND_NPER))
    bond.build(term_params, short_rates) # compute lattice
    bond.display_lattice('Bond')
    bond.describe()

    ffbond = BondFF(BondFFParameters(FF_TYPE, BOND_COUPON, FF_NPER))
    ffbond.build(term_params, short_rates, bond)
    ffbond.display_lattice(str.capitalize(FF_TYPE))
    ffbond.describe()






