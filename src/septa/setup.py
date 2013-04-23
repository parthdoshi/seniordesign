from distutils.core import setup, Extension

module1 = Extension('fovgraph',
                    sources = ['fovgraphmodule.c'],
                    libraries=['glpk'])

setup (name = '',
       version = '1.0',
       description = 'A C extension for the Graph building part.',
       ext_modules = [module1])
