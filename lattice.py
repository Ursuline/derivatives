#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 18 15:07:27 2021

# base class holder for options & term_structure

@author: charly
"""
import pandas as pd


class Parameters():
    '''Super class for parameters'''

    # pylint: disable=too-few-public-methods
    def __init__(self, nperiods, rate=None):
        self.nperiods = nperiods
        self.rate     = rate


    def describe(self, percent=False, rate=None):
        '''Self-descriptor'''

        print(f'Maturity: {self.nperiods} periods')
        if rate is not None:
            if percent:
                print(f'{rate} Rate: {self.rate:.2%}')
            else:
                print(f'{rate} Rate: {self.rate:.2f}')


    def print_parameters(self):
        ''' Print dictionary of all parameters in class '''
        print(f'\nclass parameters:{self.__dict__}')



class Lattice:
    ''' Lattice superclass encapsulates parameters and functionality
        common to Shares, Options, Futures & fixed income derivatives'''

    def __init__(self, size):
        # build a size x size list populated with 0
        self.lattice = [['' for x in range(size+1)] for y in range(size+1)]
        self.size    = size


    def _back_prop(self, row, column, rnp):
        ''' returns risk neutral q*S^(i+1)_(t+1) + (1-q)*S^i_(t+1)
            q = proba / S = lattice'''
        p_1 = self.lattice[row + 1][column + 1] # S^(i+1)_(t+1)
        p_2 = self.lattice[row][column + 1]     # S^(i)_(t+1)

        return p_1 * rnp[0] + p_2 * rnp[1]


    def display_lattice(self, title, percent_flag=False):
        '''Prints lattice to stdout'''
        print(f'\n{title} lattice:')
        dfr = pd.DataFrame(self.lattice)
        # Format output
        if percent_flag:
            pd.options.display.float_format = '{:.2%}'.format
            print(dfr.loc[::-1])
        else:
            pd.options.display.float_format = '{:.2f}'.format
            print(dfr.loc[::-1])


    def _display_price(self, percent_flag=False):
        '''Prints derivative price to stdout'''
        if percent_flag:
            print(f'C0={self.lattice[0][0]:.2%}')
        else:
            print(f'C0={self.lattice[0][0]:.2f}')


    def describe(self, title, parameters, percent):
        '''Self-descriptor'''
        print(f'\n*** {str.capitalize(title)} price ***')
        parameters.describe()
        self._display_price(percent)


    def display_parameters(self):
        ''' Print all parameters in class '''
        print(f'\nclass parameters:{self.__dict__}')
