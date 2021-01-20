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

#### PARAMETERS ####
# Lattice parameters:
# TERM STRUCTURE
TS_R00  = .05 # initial price
TS_RUD  = [1.1, .9]
TS_RNP  = [.5, .5] # risk-neutral probabilities
TS_NPER = 10


#SWAP PARAMETERS
FIXED_RATE   = .05
SWAP_NPER    = 6

#SWAPTION PARAMETERS
SWAPTION_K    = .00
SWAPTION_NPER = 3

# CAPLETS/FLOORLETS PARAMETERS
LIBOR      = .02
CF_NPER    = 6

# ELEMENTARY PRICE PARAMETERS
ELEM_NPER       = 6
ELEM_BASE_PRICE = 100

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
    ''' Caplets & Floorlets '''

    def __init__(self, cf_parameters):
        self.parameters = cf_parameters
        self.nperiods   = self.parameters.nperiods
        self.rate       = self.parameters.rate
        self.type       = DERIVATIVE
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
        super().describe('Caplet/floorlet', self.parameters, True)



#### SWAPS ####
class SwapParameters(lt.Parameters):
    '''Encapsulates parameters for swaps'''

    def __init__(self, swap_nper, fixed_rate):
        super().__init__(swap_nper, fixed_rate)


    def describe(self, percent=False, rate=None):
        ''' Prints summary parameters to stdout '''
        super().describe(True, 'Fixed')



class Swap(lt.Lattice):
    '''Swap lattice '''
    def __init__(self, swap_par):
        self.parameters = swap_par
        super().__init__(self.parameters.nperiods)
        self.size -= 1 # arrears


    def build(self, ts_par, sh_rate):
        '''Build the swap lattice'''
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    num  = sh_rate.lattice[state][period] - self.parameters.rate
                    denom = 1.0 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom
                else:
                    num  = sh_rate.lattice[state][period] - self.parameters.rate # coupon
                    num += self._back_prop(state, period, ts_par.rnp)
                    denom = 1.0 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom


    def describe(self):
        '''Self-descriptor'''
        super().describe('Swap', self.parameters, True)


#### SWAPTIONS ####
class SwaptionParameters(lt.Parameters):
    '''Encapsulates parameters for swaps'''

    def __init__(self, swaption_nper, strike):
        self.strike = strike
        super().__init__(swaption_nper)


    def describe(self, percent=False, rate=None):
        ''' Prints summary parameters to stdout '''
        print('Swaption parameters:')
        print(f'Swaption strike: {self.strike:.2%}')
        super().describe()



class Swaption(lt.Lattice):
    '''Swaption lattice '''

    def __init__(self, swaption_pars):
        self.parameters = swaption_pars
        super().__init__(self.parameters.nperiods)


    def build(self, ts_pars, sh_rate, swapl):
        '''Build the swaption lattice'''
        for period in range(self.size, -1, -1):
            for state in range(period, -1, -1):
                if period == self.size:
                    self.lattice[state][period] = max(0, swapl.lattice[state][period])
                else: # discount rate
                    num   = self._back_prop(state, period, ts_pars.rnp)
                    denom = 1.0 + sh_rate.lattice[state][period]
                    self.lattice[state][period] = num / denom


    def describe(self):
        '''Self-descriptor'''
        super().describe('Swaption', self.parameters, True)


### ELEMENTARY PRICES ###
class ElementaryPriceParameters(lt.Parameters):
    '''Encapsulates parameters for elementary prices'''

    def __init__(self, elem_nper, elem_base_price):
        self.base = elem_base_price
        super().__init__(elem_nper)


    def describe(self, percent=False, rate=None):
        ''' Prints summary parameters to stdout '''
        print('Elementary price parameters:')
        print(f'base price={self.base}')
        super().describe()



class ElementaryPrices(lt.Lattice):
    '''Elementary price lattice '''

    def __init__(self, elem_params):
        self.parameters = elem_params
        self.built      = False
        super().__init__(elem_params.nperiods)
        self.price = [0. for x in range(self.size+1)]
        self.rates = [0. for x in range(self.size+1)]


    def build(self, ts_pars, sh_rate):
        '''Build the elementary price lattice'''
        self.lattice[0][0] = 1.0
        for period in range(1, self.size+1):
            for state in range(0, period+1):
                print(state, period)
                if state == 0:
                    num    = ts_pars.rnp[0] * self.lattice[state][period-1]
                    denom = 1. + sh_rate.lattice[state][period-1]
                    self.lattice[state][period] = num / denom
                elif state == period:
                    num   = ts_pars.rnp[0] * self.lattice[state-1][period-1]
                    denom = 1. + sh_rate.lattice[state-1][period-1]
                    self.lattice[state][period] = num / denom
                else:
                    num1   = ts_pars.rnp[0] * self.lattice[state-1][period-1]
                    denom1 = 1.0 + sh_rate.lattice[state-1][period-1]
                    num2   = ts_pars.rnp[1] * self.lattice[state][period-1]
                    denom2 = 1. + sh_rate.lattice[state][period-1]
                    self.lattice[state][period] = num1/denom1 + num2/denom2
        self.built = True


    def discount(self):
        '''Compute ZCB prices'''
        print('\n  | coupon| spot|')
        print('P | price | rate|')
        print('-----------------')
        if self.built:
            for period in range(1, self.size+1):
                for state in range(0, period+1):
                    self.price[period] += self.lattice[state][period]
                self.price[period] *= self.parameters.base
                base = self.parameters.base/self.price[period]
                exp  = 1.0/period
                self.rates[period] = pow(base, exp) - 1.0
                print(f'{period} | {self.price[period]:3.2f} | {self.rates[period]:5.2%}')
        else:
            raise Exception('build() should be called before discount()')


    def describe(self):
        '''Self-descriptor'''
        super().describe('Elementary', None, False)


#### Driver ####
if __name__ == '__main__':
    ## Derivative selection ##
    # Set either of caplet, floorlet, swap, swaption, elementary
    DERIVATIVE   = 'zcb'
    LATTICE_FLAG = True # print lattice to stdout
    DERIVATIVE   = str.lower(DERIVATIVE)

    # Load underlying security-related parameters
    term_params = TermStructureParameters()
    short_rates = ShortRate(term_params)
    short_rates.display_lattice('Short-rate', True)


    # Caplets & floorlets
    if DERIVATIVE in ('caplet', 'floorlet'):
        cflet     = CapFloorLet(CFParameters(DERIVATIVE, CF_NPER, LIBOR))
        cflet.build(term_params, short_rates)  # compute lattice

        if LATTICE_FLAG:
            cflet.display_lattice(str.capitalize(DERIVATIVE), True)
        cflet.describe()

    # Swaps & swaptions
    elif DERIVATIVE in ('swap', 'swaption'):
        swap = Swap(SwapParameters(SWAP_NPER, FIXED_RATE))
        swap.build(term_params, short_rates)  # compute lattice
        if LATTICE_FLAG:
            swap.display_lattice('Swap', True)
        swap.describe()
        if DERIVATIVE == 'swaption':
            swaption = Swaption(SwaptionParameters(SWAPTION_NPER, SWAPTION_K))
            swaption.build(term_params, short_rates, swap)  # compute lattice
            if LATTICE_FLAG:
                swaption.display_lattice('Swaption', True)
            swaption.describe()

    # Elementary prices
    elif DERIVATIVE == 'elementary':
        elementary = ElementaryPrices(ElementaryPriceParameters(ELEM_NPER, ELEM_BASE_PRICE))
        elementary.build(term_params, short_rates)
        if LATTICE_FLAG:
            elementary.display_lattice('Elementary ', True)
        elementary.describe()
        elementary.discount()


    else:
        raise Exception(f'Non-existent DERIVATIVE value: "{DERIVATIVE}"')
