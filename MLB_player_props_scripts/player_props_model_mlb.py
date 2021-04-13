# -*- coding: utf-8 -*-
"""
Created on Tue Jun 25 08:55:15 2019

@author: Romain Boudet

This file will be used as part of the baseball player props predictions 
For this task, we will focus on a more machine learning based model
More precicesly we will start by using a Bayesian Network to make predictions
For each specific statistic, we will train a Bayesian Network. Where the vectors
Will be the different averages computed from previous games, and the target values
will be the value of that statistics in the following game. 

The work done in this file is to prepare the data so it can be used by a machine learning model
For each player playing in the seasons specified, we go through each of his games and create a vector
containing the information from his past performance. 
The vector will contain the current season average, the average playing home/away, the average playing 
against the same opponent, the average over the last 10 games and the average over the last 5 games. 
We then add the actual value of the stats that we are predicting to the vector in order to be able to train
the model. 
"""

import csv
import pandas as pd
import numpy as np
import math
import scipy.stats
import csv
import matplotlib.pyplot as plt
import os
from sportsreference.mlb.roster import Roster
from sportsreference.mlb.schedule import Schedule
from datetime import datetime
from operator import itemgetter
from fetch_data_mlb import update_games
import mlbgame


# for each stat to predict, we will have a value just from the last 10 games, form the location the game is
# from games indoor / outdoor, against this specific opponent and so on...

"""
these are the stats we will want to offer
- pitcher strikeouts
- player hits (gives the score of the game)
- home runs allowed (pitchers)
- bases on balls (per team)
- total hits (per team)
- total runs (per team/per player)
- struck out (per player)

"""
player_data = {"strikeouts":{}, "home_runs_thrown":{}, "hits":{}, "total_bases":{}, "home_runs":{}}





def get_player_vector(playerid,playername, current_season, seasons_to_use, game_location, game_opponent, current_team, weights):
    seasons_to_use = [int(x) for x in seasons_to_use]
    seasons_to_use.sort()
    current_season = int(current_season)
    played_data = {"total":0, "current_season":0, "current_team":0, "ab":0, "ip":0}
    strikeouts = {"home":{}, "away":{}, "l10":[], "l5":[], "current_season":[], "current_team":[]}
    home_runs_thrown = {"home":{}, "away":{}, "l10":[], "l5":[],  "current_season":[], "current_team":[] }
    hits =  {"home":{}, "away":{}, "l10":[], "l5":[], "current_season":[], "current_team":[]}
    total_bases =  {"home":{}, "away":{}, "l10":[], "l5":[],  "current_season":[], "current_team":[]}
    home_runs =  {"home":{}, "away":{}, "l10":[], "l5":[],  "current_season":[], "current_team":[]}
    for season in seasons_to_use:
        games = []
        if os.path.isfile(f"Data/{season}/Players/{playerid}.txt"):
            file = open(f"Data/{season}/Players/{playerid}.txt", "r")
            for line in file:
                games.append(line.strip())
            file.close()
        for gameid in games:
            gameid = gameid.split('/')[1]
            game_df = pd.read_csv(f"Data/{season}/Games/{gameid}_players.csv")
            game_df.set_index("Unnamed: 0", inplace=True)
            row = game_df.loc[playerid]
            opponent = row["opponent"]
            is_home = row["is_home"]
            is_pitcher = not math.isnan(row["pitches_thrown"])
            if is_home:
                location = "home"
            else:
                location = "away"
            if "teamname" in played_data.keys():
                if row["team"] != played_data["teamname"]:
                    #then the player has changed team.we reinitialize his stats for 'current team'
                    played_data["teamname"] = row["team"]
                    strikeouts["current_team"] = []
                    home_runs_thrown["current_team"] = []
                    total_bases["current_team"] = []
                    hits["current_team"] = []
                    home_runs["current_tean"] = []
                    played_data["current_team"] = 1
                else:
                    played_data["current_team"] += 1
            else:
                played_data["teamname"] = row["team"]
         
            played_data["total"] += 1
            if season == current_season:
                played_data["current_season"] += 1
                
            if is_pitcher:
                if (not math.isnan(row["innings_pitched"])) and season == current_season:
                    played_data["ip"] += row["innings_pitched"]
                if playerid in player_data["strikeouts"].keys():
                    player_data["strikeouts"][playerid].append(row["strikeouts"])
                    player_data["home_runs_thrown"][playerid].append(row["home_runs_thrown"])
                else:
                    player_data["strikeouts"][playerid]= [row["strikeouts"]]
                    player_data["home_runs_thrown"][playerid]=[row["home_runs_thrown"]]
                    
                update_stats(strikeouts, location, opponent, row["strikeouts"], season, current_season)
                update_stats(home_runs_thrown, location, opponent, row["home_runs_thrown"], season, current_season)
            else:
                if (not math.isnan(row["at_bats"])) and season == current_season:
                    played_data["ab"] += row["at_bats"]
                    
                tb = row["slugging_percentage"] * row["at_bats"]
                if playerid in player_data["hits"].keys():
                    player_data["hits"][playerid].append(row["hits"])
                else:
                    player_data["hits"][playerid]=[row["hits"]]
                
                if not math.isnan(tb):
                    if playerid in player_data["total_bases"].keys():
                        player_data["total_bases"][playerid].append(tb)
                    else:
                        player_data["total_bases"][playerid]=[tb]
                        
                num_home_runs = 0
                if not row["details"] is None:
                    plays = str(row["details"])
                    for play in plays.split(","):
                        if 'HR' in play:
                            #then the player has had a Home Run 
                            hr = play.replace("HR","")
                            # we now want to check if he has had more than one
                            if hr == "":
                                #there was only one home run
                                num_home_runs = 1
                            else:
                                num_home_run = 2
                                while not str(num_home_run) in hr:
                                    num_home_run += 1
                if not math.isnan(row["at_bats"]) and row["at_bats"] != 0:
                    if playerid in player_data["home_runs"].keys():
                        player_data["home_runs"][playerid].append(num_home_runs)
                    else:
                        player_data["home_runs"][playerid]=[num_home_runs]     
            
                update_stats(home_runs, location, opponent, num_home_runs, season, current_season)

                update_stats(hits, location, opponent, row["hits"], season, current_season)
                if not math.isnan(tb):
                    update_stats(total_bases, location, opponent, tb, season, current_season)
                    
                

    # now that we have all of the players data stored in the dictonaries, we want to create a vector containing averages
    # then we will use the optimal weights to find a prediction
    if played_data["total"] > 0:
        if is_pitcher:
            v1 = ["strikeouts", playerid, playername ] #[l5_average, l10_average, loc_average, opp_average, current_season_average, current_team_average]
            temp = get_vector(strikeouts, game_location, game_opponent)
            if len(temp)==0:
                return [],[]
            else:
                v1 = v1 + temp
            v2 = ["home_runs_thrown", playerid, playername ] 
            temp = get_vector(home_runs_thrown, game_location, game_opponent)
            
            if len(temp)==0:
                return [],[]
            else:
                v2 = v2 + temp
            return [v1, v2, played_data["ip"]], True
        else:
            v1 = ["hits", playerid, playername ]
            temp = get_vector(hits, game_location, game_opponent)
            if len(temp)==0:
                return [],[]
            else:
                v1 = v1 + temp
            v2 = ["total_bases", playerid, playername ] 
            temp = get_vector(total_bases, game_location, game_opponent)
            if len(temp)==0:
                return [],[]
            else:
                v2 = v2 + temp
            
            v3 = ["home_runs", playerid, playername ] 
            temp = get_vector(home_runs, game_location, game_opponent)
            if len(temp)==0:
                return [],[]
            else:
                v3 = v3 + temp
                
                
                
            return [v1,v2, v3, played_data["ab"]], False

    else:
        return [],[]

                                 
def update_stats(player_stats,location,opponent, new_value, season, current_season):
    if not math.isnan(new_value):
        if opponent not in player_stats[location].keys():
             player_stats[location][opponent] = [new_value]
        else:
            player_stats[location][opponent].append(new_value)
            
        player_stats["current_team"].append(new_value)
        
        if season == current_season:
            player_stats["current_season"].append(new_value)
            player_stats["l10"].append(new_value)
            player_stats["l5"].append(new_value)
             #if there are more than 10 values in the l10 list we remove the first one
            if len(player_stats["l10"]) > 10:
                player_stats["l10"] = player_stats["l10"][1:]
            #if there are more than 5 values in the l5 list we remove the first one
            if len(player_stats["l5"]) > 5:
                player_stats["l5"] = player_stats["l5"][1:]   
    
      
       
        
        
def get_vector(player_stats, location, opponent):
    if len(player_stats["l5"]) > 0:
        #l5 average
        l5_average = sum(player_stats["l5"])/len(player_stats["l5"])
        
        #l10 average
        l10_average = sum(player_stats["l10"])/len(player_stats["l10"])
        
            #current season average
        if len(player_stats["current_season"]) == 0 :
            return []
        current_season_average = sum(player_stats["current_season"])/len(player_stats["current_season"])
        
        #location average
        total_sum = 0
        num_values = 0
        for key in player_stats[location]:
            total_sum += sum(player_stats[location][key])
            num_values += len(player_stats[location][key])
        if num_values == 0:
            loc_average = current_season_average
        else:
            loc_average = total_sum/num_values
        
        #opponent average
        total_sum = 0
        num_values = 0
        if opponent in player_stats["home"]:
            total_sum += sum(player_stats["home"][opponent])
            num_values += len(player_stats["home"][opponent])
        if opponent in player_stats["away"]:
            total_sum += sum(player_stats["away"][opponent])
            num_values += len(player_stats["away"][opponent])
        if num_values == 0:
            opp_average = current_season_average
        else:
            opp_average = total_sum/num_values
            
        #current team average
        if len(player_stats["current_team"]) == 0 :
            current_team_average = current_season_average
        else:
            current_team_average = sum(player_stats["current_team"])/len(player_stats["current_team"])
        return [l5_average, l10_average, loc_average, opp_average, current_season_average, current_team_average]
    return []


def make_prediction(hometeam, awayteam, seasons_to_use, current_season, home_pp, away_pp, double_game=False):
    
    
    #first we update the rosters for both teams
    hometeam = format_team_abbreviation(hometeam)
    awayteam = format_team_abbreviation(awayteam)

    players = {hometeam:[], awayteam:[]}
    batter_vectors = {hometeam:[], awayteam:[]}
    pitcher_vectors = {hometeam:[], awayteam:[]}
    for abbrv in [hometeam, awayteam]:
        roster = Roster(abbrv, current_season, True)
        file = open(f"Data/{current_season}/Teams/{abbrv}.txt", "w")
        rosterplayers = roster.players
        playernum = 0
        for playerid in rosterplayers:
            playername = rosterplayers[playerid]
            players[abbrv].append([playerid,playername])
            if playernum == 0:
                file.write(f"{playername}:{playerid}")
            else:
                file.write(f"\n{playername}:{playerid}")
            playernum += 1
        file.close()
    lines_to_write = []
    
    for player_info in players[hometeam]:
        playerid = player_info[0]
        playername = player_info[1]
        #the object "data" that is return contains the 2 vectors from that player for both 
        # stats that we are predicting, and a value that will help us determine if we need to generate a prediction for this player
        
        data,isPitcher = get_player_vector(playerid, playername, current_season, seasons_to_use, "home", awayteam, hometeam, None) 
        #for both pitchers and batters we want to predict 2 values. v1 and v2 here are the vectors associated to the 2 statistics
        #we will then need to multiply those values by the optimal weights we have already stored
        if len(data)>0:
            if isPitcher:
                pitcher_vectors[hometeam].append(data)
            else:
                batter_vectors[hometeam].append(data)
            
    for player_info in players[awayteam]:
        playerid = player_info[0]
        playername = player_info[1]
        data, isPitcher = get_player_vector(playerid, playername, current_season, seasons_to_use, "away", hometeam, awayteam, None) 
        #for both pitchers and batters we want to predict 2 values. v1 and v2 here are the vectors associated to the 2 statistics
        #we will then need to multiply those values by the optimal weights we have already stored
        if len(data)>0:
            if isPitcher:
                pitcher_vectors[awayteam].append(data)
            else:
                batter_vectors[awayteam].append(data)
                
    #we select the batters and pitchers that we will generate statistics for. 
    # Only based on "at bats" for batters and "innings pitched" for pitchers
    home_batters_to_predict = select_players(batter_vectors[hometeam], False)
    away_batters_to_predict = select_players(batter_vectors[awayteam], False)
    #and now we make the predictions
    weights = [0.15, 0.3,0.1,0.1,0.2, 0.15]

    home_predicted_pitcher = False
    for player_stat in pitcher_vectors[hometeam]:
        v = player_stat[0]
        if v[2] == home_pp: #predicted pitcher
            home_predicted_pitcher = True
            value =  np.dot(weights , v[3:])
            sia_value = int(value) + 0.5
            sd = np.std(player_data[v[0]][v[1]])
            prob_under = scipy.stats.norm(float(value), float(sd)).cdf(sia_value)
            prob_over = 1 - prob_under
            lines_to_write.append([hometeam, v[2], v[0],value, sia_value, prob_over, get_line(prob_over), prob_under, get_line(prob_under)])
    
    if not home_predicted_pitcher:
        # if we do not have data on the predicted pitcher
        # this might be because the player was traded, and is still listed on another roster
        # so if there is an announced pitcher, from his name we still fetch information for him
        #we firs get the player_id from the player name
        home_pp_id = get_player_id(home_pp, current_season)
        if not home_pp_id is None:
            #and then we fetch the data
            data, isPitcher = get_player_vector(home_pp_id, home_pp, current_season, seasons_to_use, "home", awayteam, hometeam, None)
            if len(data) > 0:
                home_predicted_pitcher = True
                v = data[0]
                value =  np.dot(weights , v[3:])
                sia_value = int(value) + 0.5
                sd = np.std(player_data[v[0]][v[1]])
                prob_under = scipy.stats.norm(float(value), float(sd)).cdf(sia_value)
                prob_over = 1 - prob_under
                lines_to_write.append([hometeam, v[2], v[0],value, sia_value, prob_over, get_line(prob_over), prob_under, get_line(prob_under)])
            else:
                lines_to_write.append([hometeam, "Pitcher not announced or do not have enough data on the announced pitcher"])
        else:
            lines_to_write.append([hometeam, "Pitcher not announced or do not have enough data on the announced pitcher"])
        
        #we first get the mean by using the weights previously calculated 
        #and then get the standard deviation

    away_predicted_pitcher = False
    for player_stat in pitcher_vectors[awayteam]:
        v = player_stat[0]
        if v[2] == away_pp:
            away_predicted_pitcher = True
            value =  np.dot(weights , v[3:])
            sia_value = int(value) + 0.5
            sd = np.std(player_data[v[0]][v[1]])
            prob_under = scipy.stats.norm(float(value), float(sd)).cdf(sia_value)
            prob_over = 1 - prob_under
            lines_to_write.append([awayteam, v[2],v[0],value, sia_value, prob_over, get_line(prob_over), prob_under, get_line(prob_under)])
    
    if not away_predicted_pitcher:
        # if we do not have data on the predicted pitcher
        # this might be because the player was traded, and is still listed on another roster
        # so if there is an announced pitcher, from his name we still fetch information for him
        away_pp_id = get_player_id(away_pp, current_season)
        if not away_pp_id is None:
            data, isPitcher = get_player_vector(away_pp_id, away_pp, current_season, seasons_to_use, "home", awayteam, hometeam, None)
            home_predicted_pitcher = True
            v = data[0]
            home_predicted_pitcher = True
            value =  np.dot(weights , v[3:])
            sia_value = int(value) + 0.5
            sd = np.std(player_data[v[0]][v[1]])
            prob_under = scipy.stats.norm(float(value), float(sd)).cdf(sia_value)
            prob_over = 1 - prob_under
            lines_to_write.append([awayteam, v[2], v[0],value, sia_value, prob_over, get_line(prob_over), prob_under, get_line(prob_under)])
        else:
            lines_to_write.append([awayteam, "Pitcher not announced or do not have enough data on the announced pitcher"])
   
    for player_stat in home_batters_to_predict :
        v = player_stat[0]
        value =  np.dot(weights , v[3:])
        sia_value = int(value) + 0.5
        sd = np.std(player_data[v[0]][v[1]])
        prob_under = scipy.stats.norm(float(value), float(sd)).cdf(sia_value)
        prob_over = 1 - prob_under
        lines_to_write.append([hometeam, v[2], v[0],value, sia_value, prob_over, get_line(prob_over), prob_under, get_line(prob_under)])
    for player_stat in away_batters_to_predict :
        v = player_stat[0]
        value =  np.dot(weights , v[3:])
        sia_value = int(value) + 0.5
        sd = np.std(player_data[v[0]][v[1]])
        prob_under = scipy.stats.norm(float(value), float(sd)).cdf(sia_value)
        prob_over = 1 - prob_under
        lines_to_write.append([awayteam, v[2], v[0],value, sia_value, prob_over, get_line(prob_over), prob_under, get_line(prob_under)])
          
    
    
    for player_stat in home_batters_to_predict:
        v = player_stat[1]
        value =  np.dot(weights , v[3:])
        sia_value = int(value) + 0.5
        sd = np.std(player_data[v[0]][v[1]])
        prob_under = scipy.stats.norm(float(value), float(sd)).cdf(sia_value)
        prob_over = 1 - prob_under
        lines_to_write.append([hometeam,v[2], v[0],value, sia_value, prob_over, get_line(prob_over), prob_under, get_line(prob_under)])
      
    
    
    for player_stat in away_batters_to_predict:
        v = player_stat[1]
        value =  np.dot(weights , v[3:])
        sia_value = int(value) + 0.5
        sd = np.std(player_data[v[0]][v[1]])
        prob_under = scipy.stats.norm(float(value), float(sd)).cdf(sia_value)
        prob_over = 1 - prob_under
        lines_to_write.append([awayteam,v[2], v[0],value, sia_value, prob_over, get_line(prob_over), prob_under, get_line(prob_under)])
      
        
    for player_stat in home_batters_to_predict:
        v = player_stat[2]
        value =  np.dot(weights , v[3:])
        sd = np.std(player_data[v[0]][v[1]])
        mean = np.mean(player_data[v[0]][v[1]])
        prob_over = mean*1.1
        if prob_over > 0.1:
            lines_to_write.append([hometeam, v[2], "to_hit_a_home_run", 0.5,0.5, mean, get_line(mean), 1-mean, get_line(1-mean)])
    
    for player_stat in away_batters_to_predict:
        v = player_stat[2]
        value =  np.dot(weights , v[3:])
        sd = np.std(player_data[v[0]][v[1]])
        mean = np.mean(player_data[v[0]][v[1]])
        prob_over = mean*1.1
        if prob_over > 0.1:
            lines_to_write.append([awayteam, v[2], "to_hit_a_home_run", 0.5,0.5, mean, get_line(mean), 1-mean, get_line(1-mean)])
  
    date = datetime.today().strftime('%Y-%m-%d')
    dir_path = f"predictions/{date}"
    try:
        os.mkdir("predictions")
    except:
        pass    
    try:
        os.mkdir(dir_path)
    except:
        pass
    if double_game:
        file = open(f"{dir_path}/{hometeam}_{awayteam}_game2.csv", 'w', newline='')
    else:
        file = open(f"{dir_path}/{hometeam}_{awayteam}.csv", 'w', newline='')
        
    writer = csv.writer(file)
    writer.writerow(["team", "playername", "stat", "prediction", "sia_value", "prob_over", "line_over", "prob_under", "line_under"])
    for line in lines_to_write:
        writer.writerow(line)
    file.close()
    
def get_line(prob):
    return (1/(1.07*prob))

def select_players(vector_list, is_pitchers):
    '''
    this method is to select a few out of the whole list of players we will actually want to
     make a prediction (as the teams are too big)
     for batters we will select the 7 players that have the most 'at bats' and for pithers
     we will select the 4 players that have the most 'innings pitched'
    we first need to sort the list depending on the 3rd value in each array
    '''
    sorted(vector_list, key=itemgetter(-1))
    if is_pitchers:
        return vector_list
    else:
        return vector_list[:9]



def generate_all_game_day_predictions(date, seasons_to_use, current_season, is_playoff=False):
    #we first fetch any games that have not yet been loaded
    games_to_predict = {}
    home_teams = []
    update_games(current_season, True)
    for game in mlbgame.day(date.year, date.month, date.day):
        gid = game.game_id
        hometeam = gid.split('_')[4].replace('mlb','').upper()
        awayteam = gid.split('_')[3].replace('mlb','').upper()
        try:
            games_to_predict[gid] = {"hometeam":hometeam, "awayteam":awayteam, "home_pp":game.p_pitcher_home, "away_pp":game.p_pitcher_away}
    
        except:
            #the game has probably already starter
            games_to_predict[gid] = {"hometeam":hometeam, "awayteam":awayteam, "home_pp": "", "away_pp":""}
            
    for gameid in games_to_predict:
        print(f"predicting stats for game {gameid}")
        home = games_to_predict[gameid]["hometeam"]
        away = games_to_predict[gameid]["awayteam"]
        double = False
        if home in home_teams:
            #ie there is 2 games in the same day for a team
            double = True
        else:
            home_teams.append(home)
        home_pp = games_to_predict[gameid]["home_pp"]
        away_pp = games_to_predict[gameid]["away_pp"]
        if home_pp != "":
            if double:
                 make_prediction(home, away, seasons_to_use, current_season, home_pp, away_pp, double_game = True)
            else:
                make_prediction(home, away, seasons_to_use, current_season, home_pp, away_pp)

def format_team_abbreviation(team):
    to_return_names = {}
    to_change_abbrv= {}
    file = open("Data/TeamAbbrv.txt", "r")
    for line in file:
        team_name = line.split(":")[0]
        abbreviation  = line.split(":")[1].strip()
        to_return_names[team_name] = abbreviation
    file.close()
    
    file = open("Data/TeamAbbrv_mlbgame.txt", "r")
    for line in file:
        team_name = line.split(":")[0]
        abbreviation  = line.split(":")[1].strip()
        to_change_abbrv[abbreviation] = team_name
    file.close()
    
    return to_return_names[to_change_abbrv[team]]



def get_player_id(player_name, current_season):
    #we first need to get the player id from the player name
    
    for filename in os.listdir(f"Data/{current_season}/Teams"):
        file = open(f"Data/{current_season}/Teams/{filename}", 'r')
        for line in file:
            if line.split(":")[0] == player_name:
                return line.split(":")[1].strip()
        file.close()
    return None





