
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 10 17:11:11 2021

@author: romainboudet


This is the script to run to initialize all the data
"""
from nhl_fetch_data import initial_setup
import os

## we need to install some packages: 
packages_to_install = ["pip", "pandas", "numpy", "sportsreference", "sklearn", "unidecode", "scipy", "pywin32"]


if __name__ == '__main__':
#    error = False
#    for package in packages_to_install:
#        try:
#            os.system(f"cmd \c 'pip install {package}'")
#        except:
#            try:
#                os.system(f"cmd \c 'pip install {package} --user'")
#            except:
#                print(f"error downloading package {package}, make sure it is installed before running the model")

    initial_setup()