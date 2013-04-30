from distutils.core import setup, Extension

module1 = Extension('fovgraph',
                    sources=['fovgraphmodule.c'],
                    extra_compile_args=['-ggdb'],
                    libraries=['glpk'])

setup (name = '',
       version = '1.0',
       description = 'A C extension for the Graph building part.',
       ext_modules = [module1])
