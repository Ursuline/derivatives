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
# TERM STRUCTURE
TS_R00  = .06 # initial price
TS_RUD  = [1.25, .9]
TS_RNP  = [.5, .5] # risk-neutral probabilities
TS_NPER = 5

# ZCB PARAMETERS
ZCB_FACE = 100 # Bond face value normally 100
ZCB_NPER = 4

#SWAP PARAMETERS
FIXED_RATE   = .05
SWAP_NPER    = 6

# CAPLETS/FLOORLETS PARAMETERS
LIBOR      = .02
CF_NPER    = 6

# Option parameters
OP_K    = 84.0 # strike price
OPT     = 'call' # call or put option
OP_TYPE = 'european' # option type: european or american
OP_NPER = 2 # expiration - accomodates diff w/ #periods in lattice (EXPO<=N)
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
        self.term_structure_parameters = term_structure_parameters
        super().__init__(term_structure_parameters.nperiods)
        self._build() # auto-build


    def _build(self): # build the lattice
        parameters = self.term_structure_parameters
        self.lattice[0][0] = parameters.init
        for period in range(1, self.size+1):
            for share in range(0, period+1):
                if share == 0:
                    s_prev = self.lattice[share][period-1]
                    self.lattice[share][period] = parameters.r_ud[1] * s_prev
                else:
                    s_prev = self.lattice[share-1][period-1]
                    self.lattice[share][period] = parameters.r_ud[0] * s_prev


    def describe(self):
        '''Self-descriptor'''
        super().describe('Interest rate term structure', self.term_structure_parameters, True)


### ZERO-COUPON BONDS & ZCB OPTIONS ###
class ZCBParameters(lt.Parameters):
    '''Parameters for caplets/floorlets'''
    def __init__(self, zcb_face, zcb_nper):
        self.face = zcb_face
        super().__init__(zcb_nper)


    def describe(self):
        ''' Prints summary parameters to stdout '''
        print(f'Face value: {self.face}')
        super().describe()



class ZCB(lt.Lattice):
    ''' Zero-coupon bond lattice '''

    def __init__(self, zcb_parameters):
        self.zcb_parameters = zcb_parameters
        super().__init__(self.zcb_parameters.nperiods)


    def build(self, sh_rate, term_par):
        ''' build the zero-coupon bond lattice'''
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    self.lattice[state][period] = self.zcb_parameters.face
                else:
                    num = self._back_prop(state, period, term_par.rnp)
                    denom = 1 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom


    def describe(self):
        '''Self-descriptor'''
        super().describe('Zero-coupon bond', self.zcb_parameters, False)



class ZCBOptions(op.Options):
    ''' Options for Zero coupon bonds / Subclass of Options '''

    def __init__(self, opt_params):
        self.rnp               = term_params.rnp
        self.option_parameters = opt_params
        super().__init__(opt_params)


    def build(self, underlying, sh_rate):
        ''' Over rides Options build method '''
        self._set_option_flags(self.option_parameters)
        strike = self.option_parameters.strike

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
        super().describe('Zero-coupon bond options', self.option_parameters, False)



#### CAPLETS & FLOORLETS ####
class CFParameters(lt.Parameters):
    '''Parameters for caplets/floorlets'''
    def __init__(self, derivative, cf_nper, libor):
        self.type    = derivative
        super().__init__(cf_nper, libor)


    def describe(self):
        ''' Prints summary parameters to stdout '''
        print(f'Derivative: {self.type}')
        super().describe(True, 'LIBOR')


class CapFloorLet(lt.Lattice):
    ''' caplets & floorlets / Subclass of Lattice '''

    def __init__(self, cf_parameters):
        self.cf_parameters = cf_parameters
        self.nperiods      = self.cf_parameters.nperiods
        self.rate          = self.cf_parameters.rate
        self.type          = DERIVATIVE
        super().__init__(self.nperiods)
        self._set_option_flags()
        self.size -= 1 # arrears


    def _set_option_flags(self):
        '''Sets option flags for call/put & european/american'''
        if str.lower(self.type) == 'caplet':
            self.flag = 1.0
        elif str.lower(self.type) == 'floorlet':
            self.flag = -1.0
        else:
            raise Exception(f'DERIVATIVE should be "caplet" or "floorlet". Value is: "{self.type}"')


    def build(self, ts_par, sh_rate):
        ''' build the caplet/floorlet lattice '''
        flag = self.flag # caplet or floorlet
        rate = self.rate
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    num   = flag*(sh_rate.lattice[state][period] - rate)
                    denom = 1 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom
                else: # discount rate
                    num   = self._back_prop(state, period, ts_par.rnp)
                    denom = 1.0 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom


    def describe(self):
        '''Self-descriptor'''
        super().describe('Caplet/floorlet', self.cf_parameters, True)



#### SWAPS & SWAPTIONS ####
class SWAPParameters(lt.Parameters):
    '''Encapsulates parameters for swaps'''

    def __init__(self, swap_nper, fixed_rate):
        super().__init__(swap_nper, fixed_rate)


    def describe(self):
        ''' Prints summary parameters to stdout '''
        super().describe(True, 'Fixed')



class SWAP(lt.Lattice):
    '''Swap lattice '''
    def __init__(self, swap_par):
        self.swap_parameters = swap_par
        super().__init__(swap_par.nperiods)
        self.size -= 1 # arrears


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
                    num  = sh_rate.lattice[state][period] - rate # coupon
                    num += self._back_prop(state, period, ts_par.rnp)
                    denom = 1.0 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom


    def describe(self):
        '''Self-descriptor'''
        super().describe('Swap', self.swap_parameters, True)


#### Driver ####
if __name__ == '__main__':
    ## Derivative selection ##
    # Set either of zcb, zcbopt, caplet, floorlet, swap or swaption
    DERIVATIVE   = 'zcbopt'
    LATTICE_FLAG = True # print lattice to stdout
    DERIVATIVE   = str.lower(DERIVATIVE)

    # Load underlying security-related parameters
    term_params = TermStructureParameters()
    short_rates = ShortRate(term_params)
    short_rates.display_lattice('Short-rate', True)


    # Zero-coupon bonds and ZCB options
    if DERIVATIVE in ('zcb', 'zcbopt'):
        zcb = ZCB(ZCBParameters(ZCB_FACE, ZCB_NPER))
        zcb.build(short_rates, term_params) # compute lattice
        if LATTICE_FLAG:
            zcb.display_lattice('ZCB')

        if DERIVATIVE == 'zcb':
            short_rates.describe()
        zcb.describe()

        if DERIVATIVE == 'zcbopt': # ZCB options
            option_params = op.OptionParameters(OPT, OP_TYPE, OP_K, OP_NPER)
            zcb_opt       = ZCBOptions(option_params)
            zcb_opt.build(zcb, short_rates)  # compute lattice
            if LATTICE_FLAG:
                zcb_opt.display_lattice('Zero option value')
            short_rates.describe()
            zcb_opt.describe()

    # Caplets & floorlets
    elif DERIVATIVE in ('caplet', 'floorlet'):
        cflet     = CapFloorLet(CFParameters(DERIVATIVE, CF_NPER, LIBOR))
        cflet.build(term_params, short_rates)  # compute lattice

        if LATTICE_FLAG:
            cflet.display_lattice(str.capitalize(DERIVATIVE), True)
        cflet.describe()

    # Swaps & swaptions
    elif DERIVATIVE == 'swap':
        swap = SWAP(SWAPParameters(SWAP_NPER, FIXED_RATE))
        swap.build(term_params, short_rates)  # compute lattice
        if LATTICE_FLAG:
            swap.display_lattice(str.capitalize(DERIVATIVE), True)
        swap.describe()

    else:
        raise Exception(f'DERIVATIVE value is: "{DERIVATIVE}"')
