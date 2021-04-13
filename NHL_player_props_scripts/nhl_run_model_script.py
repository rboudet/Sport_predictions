#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 11 08:53:29 2021

@author: romainboudet
"""

from datetime import datetime,timedelta
from nhl_props_model import generate_all_game_predictions
import time
#
#counter = 0
#while True:
#    if counter <=   :
#        generate_all_game_predictions(datetime.today(), send_email=True)
#        time.sleep(7200)
#        counter = counter + 1
#    else:
#        break

email_recipient = "romain.boudet@mail.mcgill.ca"
predict_for_gtd = False
#generate_all_game_predictions(datetime.today(), email_recipient, predict_for_gtd, send_email=True)
generate_all_game_predictions(datetime.today() + timedelta(days=1), email_recipient, predict_for_gtd, send_email=True)
