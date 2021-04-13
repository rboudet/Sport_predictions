#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 11 08:53:29 2021

@author: romainboudet
"""

from datetime import datetime
from nba_props_model import generate_all_game_predictions

#set to False if we should remove game time decision players from the predictions
take_into_account_gtd = False 

email_recipient = "romain.boudet@mail.mcgill.ca"
generate_all_game_predictions(datetime.today(), take_into_account_gtd,email_recipient, send_email=True)
