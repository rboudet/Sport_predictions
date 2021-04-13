# -*- coding: utf-8 -*-
"""
Created on Wed Jul 17 10:24:09 2019

@author: Romain Boudet

This file will be used to use the mlb player props model
"""

from player_props_model_mlb import generate_all_game_day_predictions, make_prediction
from fetch_data_mlb import update_games
from datetime import datetime,timedelta


'''
game abbreviation: 
    
Arizona Diamondbacks:ARI
Atlanta Braves:ATL
Baltimore Orioles:BAL
Boston Red Sox:BOS
Chicago Cubs:CHN
Chicago White Sox:CHA
Cincinnati Reds:CIN
Cleveland Indians:CLE
Colorado Rockies:COL
Detroit Tigers:DET
Houston Astros:HOU
Kansas City Royals:KCA
Los Angeles Angels:ANA
Los Angeles Dodgers:LAN
Miami Marlins:MIA
Milwaukee Brewers:MIL
Minnesota Twins:MIN
New York Mets:NYN
New York Yankees:NYA
Oakland Athletics:OAK
Philadelphia Phillies:PHI
Pittsburgh Pirates:PIT
San Diego Padres:SDN
Seattle Mariners:SEA
San Francisco Giants:SFN
St. Louis Cardinals:SLN
Tampa Bay Rays:TBA
Texas Rangers:TEX
Toronto Blue Jays:TOR
Washington Nationals:WAS

'''


'''
for initial setup you can run this piece of code
It will fetch the data from the 2018,2017,2016 seasons as well as the data that has been played so far in the 2019 season
'''

#for season in ["2019", "2020"]:
#    update_games(season, False)
    
#update_games("2019", True)



'''
to fetch data from a specific season
'''
#season = "2017"
#update_games(season, False)


'''
to run predictions for the games happening today
'''
#current_season = "2019"
#seasons_to_use = ["2019","2018","2017"]
#date = datetime.today()
#generate_all_game_day_predictions(date ,seasons_to_use , current_season)




'''
to run predictions for the games happening on a given day
'''
#current_season = "2019"
#seasons_to_use = ["2019","2018","2017"]
#date = datetime(2019,10,16)
#generate_all_game_day_predictions(date ,seasons_to_use , current_season)
#


'''
run a prediction for a specific matchup
you will need to specify the hometeam and awayteam abbreviations (you can find them at the top of this file)
and you need to indicate the probable pitcher, if none are announced yet, set the propbable pitcher to : "."
'''
#current_season = "2019"
#seasons_to_use = ["2019"]
#home_probable_pitcher = "Madison Bumgarner"
#away_probable_pitcher = "Noah Syndergaard"
#hometeam ="SFN"
#awayteam = "NYN"
#make_prediction(hometeam, awayteam, seasons_to_use,current_season, home_probable_pitcher, away_probable_pitcher)

