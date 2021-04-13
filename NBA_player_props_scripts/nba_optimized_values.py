#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 20 09:08:21 2021

@author: romainboudet
"""

import pandas as pd
import os

import csv
import math
    

from sklearn.ensemble import AdaBoostRegressor
## these are needed for to create the exe file
import sklearn.tree
import sklearn.utils._cython_blas
import sklearn.utils._weight_vector
import sklearn.neighbors._quad_tree
import sklearn.neighbors._typedefs


'''
This method will be used to compute the optimal weights for a given player
'''
  

def fetch_stats_for_player(season, gameid, playerid):
    # this method returns the stats of a given player for a given game
    # if the player did not play this game, it returns {}
    
    df = pd.read_csv(f"Data/{season}/Games/{gameid}_players.csv")
    teams = df.team.unique() #teams that were playing in the game. (in first position home team)
    for i, row in df.iterrows():
        if row["Unnamed: 0"] == playerid:  #Unamed : 0 is the column name for player ids
            if math.isnan(row["minutes_played"]):
                break
            
            # we also want to add information regarding if the player is playing at home
            # and against which team he is playing. 
            game_df = pd.read_csv(f"Data/{season}/Games/{gameid}.csv")
            minutes_1 = time_format(game_df.iloc[0]["away_minutes_played"])
            minutes_2 = time_format(game_df.iloc[0]["home_minutes_played"])
            total_minutes = max(minutes_1, minutes_2)
            home_abbrv = teams[0]
            if home_abbrv == row["team"]:
                row["isHome"] = True
                row["opponent"] = teams[1]
                row["current_team"] = teams[0]
            else:
                row["isHome"] = False
                row["opponent"] = teams[0]
                row["current_team"] = teams[1]
            row["total_minutes"] = total_minutes/5
            
            return row
    return pd.DataFrame()

def time_format(time):
    if ":" in str(time):
        minutes = time.split(":")[0]
        seconds = time.split(":")[1]
        time = float(minutes) + float(seconds)/60
    return time



def compute_missing_values_for_weight_calculations(playerid, seasons):
    # we make sure the folders are created 
    seasons = sorted([int(x) for x in seasons])
    current_season = seasons[-1]

    
    try:
        os.mkdir(f"Data/{current_season}/weights")
    except: 
        pass
    try:
        os.mkdir(f"Data/{current_season}/weights/regular")
    except: 
        pass
    try:
        os.mkdir(f"Data/{current_season}/weights/playoff")
    except: 
        pass
    
    games_computed = [] ## this will contain all the games that are taken into account for the weights files.   
    try:
        file = open(f'Data/{current_season}/weights/regular/{playerid}.txt', 'r')
        for line in file:
            games_computed.append(line.strip())
        file.close()
    except: 
        pass
    games_played = []
    for i in range(len(seasons)): 
        try:
            season = seasons[i]
            file = open(f'Data/{season}/Players/{playerid}.txt', 'r')
            for line in file: 
                games_played.append([line.strip(), season])
            file.close()
        except:
            pass
    
    if len(games_computed) == len(games_played):
        return False
    ## now we want to verify for which games we need to compute the lambda values, making sure we only take into account games that 
    ## have happened already. 
    data_stored = {"l10":{"points":[], "assists":[], "rebounds":[], "percent_played":[]},"l5":{"points":[], "assists":[], "rebounds":[], "percent_played":[]},
                  "home":{"points":[], "assists":[], "rebounds":[], "percent_played":[]}, "away":{"points":[], "assists":[], "rebounds":[], "percent_played":[]}, 
                  "overall":{"points":[], "assists":[], "rebounds":[], "percent_played":[]}}
    for season in seasons:
        data_stored[str(season)] = {"points":[], "assists":[], "rebounds":[], "percent_played":[]}
    
    rows_to_add = []
    games_added = []
    prev_season = ""
    
    for game_num in range(len(games_played)):
        [gameid, season] = games_played[game_num]
        if season != prev_season: 
            data_stored["l5"] = {"points":[], "assists":[], "rebounds":[], "percent_played":[]}
            data_stored["l10"] = {"points":[], "assists":[], "rebounds":[], "percent_played":[]}
        prev_season = season
        
        if gameid not in games_computed:    
            games_added.append(gameid)
            ## we want to make sure that the player has player has played enough games
            # and that his last game was not too long ago
       
        # then we want to compute the values. taking only into account games 0 ... game_num
        game_stats = fetch_stats_for_player(season,gameid, playerid)
        if(game_stats.empty or  game_stats["minutes_played"]==0):
            continue
        ishome =  game_stats["isHome"]            
        mp = game_stats["minutes_played"]
        pp = mp/game_stats["total_minutes"]
        pts = game_stats["points"]#/mp
        ast = game_stats["assists"]#/mp
        reb = game_stats["total_rebounds"]#/mp
        
        
        types = ["points", "assists", "rebounds", "percent_played"]
        values = [pts, ast, reb, pp]
        
        for i in range(len(types)):

            type = types[i]
            true_value = values[i]
            if len(data_stored[str(season)][type]) >= 3 :
                #we want to add a row to the file so we calculate the averages : 
           
                l10_avg =  sum(data_stored["l10"][type])/len(data_stored["l10"][type])
                l5_avg =  sum(data_stored["l5"][type])/len(data_stored["l5"][type])
                overall_avg =  sum(data_stored["overall"][type])/len(data_stored["overall"][type])
                if ishome:
                    if len(data_stored["home"][type]) <=5:
                        loc_avg = overall_avg
                    else:
                        loc_avg =  sum(data_stored["home"][type])/len(data_stored["home"][type])
                else:
                    if len(data_stored["away"][type]) <= 5:
                        loc_avg = overall_avg
                    else:
                        loc_avg =  sum(data_stored["away"][type])/len(data_stored["away"][type])
                if(len(data_stored[str(season)][type]) >= 1):
                    season_avg = sum(data_stored[str(season)][type])/len(data_stored[str(season)][type])
                    if len(data_stored[str(season)][type]) <= 5: 
                        ## if the player has not played a lot that season, we also want to take into account his overall 
                        ## average. And we do the same for the l5 and l10 averages
                        season_avg = 0.66*season_avg + 0.33*overall_avg
                        l5_avg = 0.66*l5_avg + 0.33*overall_avg
                        l10_avg = 0.66*l10_avg + 0.33*overall_avg
                else:
                    season_avg = overall_avg
                
                row = [gameid, type, l10_avg, l5_avg, season_avg, loc_avg,overall_avg, true_value]
                rows_to_add.append(row)
                
        if ishome:
            loc_value = "home"
        else:
            loc_value="away"
            
        for i in range(len(types)):
           
                    
            data_stored[loc_value][types[i]].append(values[i])
            data_stored["overall"][types[i]].append(values[i])
            data_stored[str(season)][types[i]].append(values[i])

            if len(data_stored["l10"][types[i]]) != 10:
                data_stored["l10"][types[i]].insert(0, values[i])
            else:
                k = len(data_stored["l10"][types[i]]) -1
                while k != 0:
                    data_stored["l10"][types[i]][k] = data_stored["l10"][types[i]][k-1]
                    k = k-1
                data_stored["l10"][types[i]][0] = values[i]
                
            if len(data_stored["l5"][types[i]]) != 5:
                data_stored["l5"][types[i]].insert(0, values[i])
            else:
                k = len(data_stored["l5"][types[i]]) -1
                while k != 0:
                    data_stored["l5"][types[i]][k] = data_stored["l5"][types[i]][k-1]
                    k = k-1
                data_stored["l5"][types[i]][0] = values[i]
                
                
    if os.path.isfile(f'Data/{current_season}/weights/regular/{playerid}.txt'):
        file = open(f'Data/{current_season}/weights/regular/{playerid}.txt', 'a')
        for gameid in games_added:
            file.write('\n' + gameid)
        file.close()
    else:
         file = open(f'Data/{current_season}/weights/regular/{playerid}.txt', 'w')
         counter = 0
         for gameid in games_added:
             if counter == 0:
                 file.write(gameid)
             else:
                 file.write('\n' + gameid)
             counter += 1
         file.close()
            
    #now we want to store these new values in the csv file
    if os.path.isfile(f'Data/{current_season}/weights/regular/{playerid}.csv'):
        file = open(f'Data/{current_season}/weights/regular/{playerid}.csv', 'a')
        writer = csv.writer(file)
        for row in rows_to_add:
            writer.writerow(row)
        file.close()
    else:
        file = open(f'Data/{current_season}/weights/regular/{playerid}.csv', 'a')
        writer = csv.writer(file)
        writer.writerow(["gameid", "type", "l10", "l5", "season", "location", "overall", "true_value"])
        for row in rows_to_add:
            writer.writerow(row)
        file.close()
    return True

def compute_opt_weights(playerid, seasons, default_weights): 
    
    
    
    ## we first want to check if any games need to be added to the data
    change = compute_missing_values_for_weight_calculations(playerid, seasons)
    
    ## now we know the csv files are complete
    
    ''' once we have all the data, for each stat of the individual player.  We will compute the optimal weights that the player assigns to 
        - games within the last 5
        - games within the last 10
        - games against the same opponent
#        - games at the same location (home/away)
#    
#    '''
            
    seasons = sorted([int(x) for x in seasons])
    current_season = seasons[-1]
    try:
        df = pd.read_csv(f'Data/{current_season}/weights/regular/{playerid}.csv')
    except:
        return default_weights

        
    # we want to remove the extreme values (our model should not be predicting such values so training it on it does not make sense)
    if len(df.index) < 50:
        return default_weights
    
    types =  ["points", "assists", "rebounds","turnovers","blocks", "three_pointers", "two_pointers", "free_throws","percent_played"]
    index = ["l10", "l5", "season", "overall"]
    data = {"l10":[[],[],[],[],[],[],[],[],[]], "l5":[[],[],[],[],[],[],[],[],[]], "season":[[],[],[],[],[],[],[],[],[]], "overall":[[],[],[],[],[],[],[],[],[]]}
    weights_df = pd.DataFrame(data, index=types)
    total_df = pd.DataFrame()
    time_df = pd.DataFrame()
    
    # we remove the extreme values for each stat
    for type in ["points", "assists", "rebounds", "percent_played"]:
        d = df[df['type'] == type]
        y = d["true_value"]
        remove =int( 0.1 *len(y))
        if(remove>0):
            d = d.sort_values(by=["true_value"])[remove:-remove] 
        if type !=  "percent_played":
            total_df = total_df.append(d)
        else:
            time_df = time_df.append(d)
        
        
    # we then fit the data to a linear regression model where we obtain the optimal
    # weights for each categorie of data
    y =  total_df["true_value"]
    X =  total_df.drop(["gameid", "true_value", "type",  "location"], axis=1)
    regr = AdaBoostRegressor(random_state=0,learning_rate = 0.001, n_estimators=500, loss = 'square')
    regr.fit(X,y)
    weights = regr.feature_importances_
    for type in types[:-1]:
        for i in range(len(weights)):
            weights_df.at[type, index[i]] = weights[i]
    
    ## and then we save the new weights:
    weights_df.at["percent_played","l10"]= 0.3
    weights_df.at["percent_played","l5"]=  0.5
    weights_df.at["percent_played","season"]= 0.2
    weights_df.at["percent_played","overall"]= 0

    weights_df.to_csv(f'Data/{current_season}/weights/regular/{playerid}_weights.csv') 
    return weights_df    




