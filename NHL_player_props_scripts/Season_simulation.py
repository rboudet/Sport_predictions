#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  8 10:16:54 2021

@author: romainboudet
"""

'''
This file will be used for testing the NHL props model
and to change some hard coded values which leads to the best results
'''
import numpy as np
from sportsreference.nhl.schedule import Schedule
from sportsreference.nhl.teams import Teams
import pandas as pd
import math
import os
from datetime import datetime
from nhl_fetch_data import get_stats_from_game, fetch_playerstat_for_player
from scipy.stats import poisson
from operator import itemgetter
import csv
import os
import glob



reg_l5_weight = 0.2
reg_l10_weight = 0.2
reg_location_weight = 0.2
reg_opponent_weight = 0
reg_season_weight = 0.3
reg_overall_weight = 0.1
reg_playoff_weight = 0



def simulate_fetch_stats_for_player(season, gameid, playerid):
    # this method returns the stats of a given player for a given game
    # if the player did not play this game, it returns {}
    
    df = pd.read_csv(f"Data/{season}/Games/{gameid}_players.csv")
    teams = df.team.unique() #teams that were playing in the game. (in first position home team)
    total_minutes = 0
    to_return = pd.DataFrame()
    for i, row in df.iterrows():
        total_minutes += simulate_time_format(row["time_on_ice"])
        if row["Unnamed: 0"] == playerid:  #Unamed : 0 is the column name for player ids
            row["time_on_ice"] = simulate_time_format(row["time_on_ice"])
            if math.isnan( row["time_on_ice"]):
                break
            
            # we also want to add information regarding if the player is playing at home
            # and against which team he is playing. 
#            game_df = pd.read_csv(f"Data/{season}/Games/{gameid}.csv")
            home_abbrv = teams[0]
            if home_abbrv == row["team"]:
                row["isHome"] = True
                row["opponent"] = teams[1]
                row["current_team"] = teams[0]
            else:
                row["isHome"] = False
                row["opponent"] = teams[0]
                row["current_team"] = teams[1]
            
            to_return =  row
    if not to_return.empty :
        to_return["total_game_minutes"] = total_minutes/12
        
    return to_return


def simulate_time_format(time):
    try:
        if ":" in str(time):
            minutes = time.split(":")[0]
            seconds = time.split(":")[1]
            time = float(minutes) + float(seconds)/60
        return float(time)
    except:
        return None



def simulate_fetch_data_for_game(gameid, season):
    
    ## we want to add the data for that game if it is not already present in the files.
  
    game_df, player_df = get_stats_from_game(gameid, season)
    
    for index, row in player_df.iterrows():
        playerid = row["Unnamed: 0"]
        time_on_ice = simulate_time_format(row["time_on_ice"])
        if time_on_ice is None or time_on_ice == 0:
            continue
        else:
            if os.path.isfile(f"Data/{season}/Players/Simulate/{playerid}.txt"):
                file = open(f"Data/{season}/Players/Simulate/{playerid}.txt", "a")
                file.write(f"\n{gameid}")
            else:
                file = open(f"Data/{season}/Players/Simulate/{playerid}.txt", "w")
                file.write(f"{gameid}")
            file.close()
    
    home_goals = game_df["home_goals"].item()
    away_goals = game_df["away_goals"].item()
    winning_abbr = game_df["winning_abbr"].item()
    losing_abbr = game_df["losing_abbr"].item()
    home_sog =  game_df["home_shots_on_goal"].item()
    away_sog =  game_df["away_shots_on_goal"].item()

    if os.path.isfile(f"Data/{season}/simulate_defense_file.csv"):
        df =  pd.read_csv(f"Data/{season}/simulate_defense_file.csv")
        df = df.set_index('team_names')
        if home_goals > away_goals:
            home_abbr = winning_abbr
            away_abbr = losing_abbr
        else:
            home_abbr = losing_abbr
            away_abbr = winning_abbr
    
        if home_abbr in df.index.values:
            df["games_played"][home_abbr] =  df["games_played"][home_abbr] + 1
            df["goals_allowed"][home_abbr]=   df["goals_allowed"][home_abbr] + away_goals
            df["shots_on_goal_allowed"][home_abbr] =   df["shots_on_goal_allowed"][home_abbr]+ away_sog
        else:
            data = {"games_played":1, "goals_allowed":away_goals, "shots_on_goal_allowed":away_sog }
            new_row_df = pd.DataFrame(data, index=[home_abbr])
            new_row_df.index.name = "team_names"
            df = pd.concat([df, new_row_df])
                
        if away_abbr in df.index.values:
            df["games_played"][away_abbr] =  df["games_played"][away_abbr] + 1
            df["goals_allowed"][away_abbr]=   df["goals_allowed"][away_abbr] + home_goals
            df["shots_on_goal_allowed"][away_abbr] =   df["shots_on_goal_allowed"][away_abbr]+ home_sog
        else:
            data = {"games_played":1, "goals_allowed":home_goals, "shots_on_goal_allowed":home_sog }
            new_row_df = pd.DataFrame(data, index=[away_abbr])
            new_row_df.index.name = "team_names"
            df = pd.concat([df, new_row_df])
                
        df.to_csv(f"Data/{season}/simulate_defense_file.csv")

    else:
        if int(home_goals) > int(away_goals):
            data = {"games_played":[1,1], "goals_allowed":[away_goals, home_goals], "shots_on_goal_allowed":[away_sog, home_sog]}
        else:
            data = {"games_played":[1,1], "goals_allowed":[home_goals, away_goals], "shots_on_goal_allowed":[home_sog, away_sog]}
        df = pd.DataFrame(data, index=[winning_abbr, losing_abbr])
        df.index.name = "team_names"
        df.to_csv(f"Data/{season}/simulate_defense_file.csv", index=True)

 
    return player_df

def simulate_season():
    
    # we first want to fetch all the games that have already "happenend"
    # and the games that we want to predict

    
    games_played = []
    game_df = pd.DataFrame(columns=["gameid", "date", "hometeam", "awayteam"])
    
    ## games played last season ###
    teams = Teams("2020")
    for team in teams:
        df = pd.read_csv(f"Data/2020/Teams/{team.abbreviation}_schedule.csv")
        for index, row in df.iterrows(): 
            gameid = row["boxscore_index"]
            opponent = row["opponent_abbr"]
            datestring = str(row["datetime"])
            values = datestring.split(" ")[0].split("-")
            game_date=datetime(int(values[0]), int(values[1]), int(values[2]))
            if row["location"] == "Home":
                game_df = game_df.append({"gameid":gameid, "date":game_date.date(), "hometeam":team.abbreviation, "awayteam":opponent}, ignore_index=True)
            else:
                game_df = game_df.append({"gameid":gameid, "date":game_date.date(), "awayteam":team.abbreviation, "hometeam":opponent}, ignore_index=True)

    
    game_df= game_df.sort_values(by='date')
    for index, row in game_df.iterrows():
        gameid = row["gameid"]
        home = row["hometeam"]
        away = row["awayteam"]
        if (gameid, "2020", home, away) not in games_played:
            games_played.append((gameid, "2020", home, away))
    
    ### now the current season ### 
    game_df = pd.DataFrame(columns=["gameid", "date", "hometeam", "awayteam"])
    current_season_games = []
    teams = Teams("2021")
    for team in teams:
        df = pd.read_csv(f"Data/2021/Teams/{team.abbreviation}_schedule.csv")
        for index, row in df.iterrows(): 
            gameid = row["boxscore_index"]
            opponent = row["opponent_abbr"]
            if '<' in gameid :
                break
            datestring = str(row["datetime"])
            values = datestring.split(" ")[0].split("-")
            game_date=datetime(int(values[0]), int(values[1]), int(values[2]))
            
            if row["location"] == "Home":
                game_df = game_df.append({"gameid":gameid, "date":game_date.date(), "hometeam":team.abbreviation, "awayteam":opponent}, ignore_index=True)
            else:
                game_df = game_df.append({"gameid":gameid, "date":game_date.date(), "awayteam":team.abbreviation, "hometeam":opponent}, ignore_index=True)    
    
    game_df= game_df.sort_values(by='date')
    for index, row in game_df.iterrows():
        gameid = row["gameid"]
        home = row["hometeam"]
        away = row["awayteam"]
        if (gameid, "2021",home, away) not in current_season_games:
            current_season_games.append((gameid, "2021",home, away))
    

    
    counter = 1
    for (opponent, l5,l10,season_weight,overall,loc) in [[0.1, 0, 0.1, 0.2, 0.5,0.1],[0.1, 0, 0.1, 0.1, 0.6,0.1] ]:
        for def_impact in [0.1]:
            games = 0
            print(f"using parameters : {def_impact}, {l5}, {l10}, {season_weight}, {overall}, {loc}, {opponent}")
            files = glob.glob("Data/2021/Players/Simulate/*")
            for f in files:
                try:
                    os.remove(f)
                except:
                    pass
            try:
                os.remove("Data/2021/simulate_defense_file.csv")
            except:
                pass

            
            temp_games_played = games_played.copy() 
            temp_current_season_games = current_season_games.copy()
            for i in range(100):
                simulate_fetch_data_for_game(current_season_games[i][0], temp_current_season_games[i][1])
                temp_games_played.append(temp_current_season_games[i])
                
            temp_current_season_games = temp_current_season_games[100:]
    
            
            file = open(f"simulation_results_file{counter}.csv", "w")
            writer = csv.writer(file)
            writer.writerow(["def_impact", "l5", "l10", "season_weight", "overall", "location", "opponent"])
            writer.writerow([def_impact, l5, l10, season_weight, overall, loc, opponent])

            writer.writerow(["gameid", "points difference", "goals difference", "assist difference", "total"])
            file.close()
            for (gameid, season, home, away) in temp_current_season_games:    
                print(gameid)
                if"202103090" in gameid:
                    break
                # we want to predict the values for gameid, taking only into account the games in games_played list
                points_score, goals_score,assists_score = simulate_predict_stats_for_game(l5, l10, season_weight, overall, loc, opponent,def_impact, gameid, home, away, temp_games_played)
                file = open(f"simulation_results_file{counter}.csv", "a")
                writer = csv.writer(file)
                writer.writerow([gameid, points_score,goals_score, assists_score, points_score+goals_score+assists_score] )
                file.close()
                temp_games_played.append(gameid)
                    
            counter += 1

def simulate_predict_stats_for_game(l5, l10, season_weight, overall, loc, opponent,def_impact, gameid, hometeam, awayteam, games_played):
    
    points_score = 0
    goals_score = 0
    assists_score = 0
    
    current_season = "2021"
    player_names = {}
    l10_weight = float(l10)
    l5_weight = float(l5)
    season_weight = float(season_weight)
    location_weight = float(loc)
    overall_weight = float(overall)
    opponent_weight = float(opponent)
    
    types = ["goals", "assists", "shots", "shots_on_goal", "saves", "percent_played"]
    data = {"l10":[l10_weight,l10_weight,l10_weight,l10_weight,l10_weight, l10_weight], 
                   "l5":[l5_weight,l5_weight,l5_weight,l5_weight,l5_weight,l5_weight], 
                   "season":[season_weight,season_weight,season_weight,season_weight,season_weight,season_weight], 
                   "location":[location_weight,location_weight,location_weight,location_weight,location_weight,location_weight], 
                   "overall":[overall_weight,overall_weight,overall_weight,overall_weight,overall_weight,overall_weight], 
                    "opponent":[opponent_weight,opponent_weight,opponent_weight,opponent_weight,opponent_weight,opponent_weight]}
    default_weights_df = pd.DataFrame(data, index=types)
    

    #We keep track of player names and select which players are injures
    file = open(f"Data/{current_season}/Teams/{hometeam}.txt", "r", encoding="utf8")
    home_players = []
    for line in file:
        temp = (line.rstrip()).split(":")
        home_players.append(temp[1])
        player_names[temp[1]] = temp[0]         
    file.close()
    
    # do the same thing for the away players
    file = open(f"Data/{current_season}/Teams/{awayteam}.txt", "r", encoding="utf8")
    away_players = []
    for line in file:
        temp = (line.rstrip()).split(":")
        away_players.append( temp[1])
        player_names[temp[1]] = temp[0]
        
    file.close()

    home_avg_goals_allowed = 0
    home_avg_sog_allowed = 0
    away_avg_goals_allowed = 0
    away_avg_sog_allowed = 0
    
    league_avg_goals_allowed = 0
    league_avg_sog_allowed = 0
    defense_df = pd.read_csv(f"Data/{current_season}/simulate_defense_file.csv")
    defense_df = defense_df.set_index('team_names')
    
    
    home_avg_goals_allowed = defense_df["goals_allowed"][hometeam]/defense_df["games_played"][hometeam]
    home_avg_sog_allowed = defense_df["shots_on_goal_allowed"][hometeam]/defense_df["games_played"][hometeam]
    away_avg_goals_allowed = defense_df["goals_allowed"][awayteam]/defense_df["games_played"][awayteam]
    away_avg_sog_allowed = defense_df["shots_on_goal_allowed"][awayteam]/defense_df["games_played"][awayteam]
    
    league_avg_goals_allowed = sum(defense_df["goals_allowed"])/sum(defense_df["games_played"])
    league_avg_sog_allowed = sum(defense_df["shots_on_goal_allowed"])/sum(defense_df["games_played"])
    
    average_stats_per_player_home = {}
    average_stats_per_player_away = {}
    not_predicting = {hometeam:[], awayteam:[]}
    indices = ["l10", "l5", "season", "location", "overall", "opponent"]
    stat_types = ["goals", "assists", "shots", "shots_on_goal", "saves", "percent_played"]
    seasons = ["2020", "2021"]
    
    for player in home_players:        
        ## we fetch the optimal weights for the given player
        # if there are none, this method will return the default weights provided
#        weights_df = compute_opt_weights(player, seasons, default_weights_df)
        gameids = []
        try:
            gameid_file = open(f"Data/2020/Players/{player}.txt")
            for x in gameid_file.readlines():
                gameids.append([x.strip(),"2020",False])
            gameid_file.close()
        except:
            #the player has no games played in this season
                pass
        try:
            gameid_file = open(f"Data/2021/Players/Simulate/{player}.txt")
            for x in gameid_file.readlines():
                gameids.append([x.strip(),"2021",False])
            gameid_file.close()
        except:
            #the player has no games played in this season
                pass
        
        
        weights_df = default_weights_df

        df,def_rating,gp_season = get_values_for_player(player, current_season, gameids , True, awayteam)
        if gp_season >= 3:
                        
            for type in stat_types:
                overall = df.at[type, "overall"]
                season = df.at[type, "season"]
                l5 = df.at[type, "l5"]
                l10 = df.at[type, "l10"]
               
                if df.at[type, "opponent"] == 0:
                    df.at[type, "opponent"]  =  df.at[type, "season"]
              
            
        
            if df.empty:
                continue
            
            else:
                average_stats_per_player_home[player] = {}
                for stat in stat_types:
                    value = 0
                    for index in indices: 
                        value += df.at[stat, index] * weights_df.at[stat, index]
                    average_stats_per_player_home[player][stat] = value
        else:
            not_predicting[hometeam].append(player)
        
    for player in away_players:
        gameids = []
        try:
            gameid_file = open(f"Data/2020/Players/{player}.txt")
            for x in gameid_file.readlines():
                gameids.append([x.strip(),"2020",False])
            gameid_file.close()
        except:
            #the player has no games played in this season
                pass
        try:
            gameid_file = open(f"Data/2021/Players/{player}_simulate.txt")
            for x in gameid_file.readlines():
                gameids.append([x.strip(),"2021",False])
            gameid_file.close()
        except:
            #the player has no games played in this season
                pass
#        weights_df = compute_opt_weights(player, seasons, default_weights_df)
        weights_df = default_weights_df
        df, def_rating,gp_season = get_values_for_player(player, current_season, gameids , False, hometeam)
        if gp_season >= 3:
            for type in types:
                overall_avg = df.at[type, "overall"]
                season_avg = df.at[type, "season"]
                l5 = df.at[type, "l5"]
                l10 = df.at[type, "l10"]
        
                if df.at[type, "opponent"] == 0:
                    df.at[type, "opponent"]  =  df.at[type, "season"]
    
            if df.empty:
                continue
            else:
                average_stats_per_player_away[player] = {}
                for stat in stat_types:
                    value = 0
                    for index in indices: 
                        value += df.at[stat, index] * weights_df.at[stat, index]
                    
                    average_stats_per_player_away[player][stat] = value
        else:
            not_predicting[awayteam].append(player)
    
    
    home_def_goals_rating = away_avg_goals_allowed - league_avg_goals_allowed
    home_def_sog_rating = away_avg_sog_allowed - league_avg_sog_allowed
    away_def_goals_rating = home_avg_goals_allowed - league_avg_goals_allowed
    away_def_sog_rating =home_avg_sog_allowed - league_avg_sog_allowed
    
    if home_def_goals_rating > 1:
        home_goal_shift = 1
    elif home_def_goals_rating < -1:
        home_goal_shift = -1
    else:
        home_goal_shift = home_def_goals_rating
        
    if home_def_sog_rating > 3:
        home_sog_shift = 1
    elif home_def_sog_rating < -3:
        home_sog_shift = -1
    else:
        home_sog_shift = home_def_sog_rating/3
        
    if away_def_goals_rating > 1:
        away_goal_shift = 1
    elif away_def_goals_rating < -1:
        away_goal_shift = -1
    else:
        away_goal_shift = away_def_goals_rating
        
    if away_def_sog_rating > 3:
        away_sog_shift = 1
    elif away_def_sog_rating < -3:
        away_sog_shift = -1
    else:
        away_sog_shift = away_def_sog_rating/3

    
    for player in average_stats_per_player_home:
        average_stats_per_player_home[player]["goals"] = average_stats_per_player_home[player]["goals"] * (1+def_impact*home_goal_shift)
        average_stats_per_player_home[player]["assists"] = average_stats_per_player_home[player]["assists"] * (1+def_impact*home_goal_shift)
        average_stats_per_player_home[player]["shots_on_goal"] = average_stats_per_player_home[player]["shots_on_goal"] * (1+def_impact*home_sog_shift)
    for player in average_stats_per_player_away:
        average_stats_per_player_away[player]["goals"] = average_stats_per_player_away[player]["goals"] * (1+def_impact*away_goal_shift)
        average_stats_per_player_away[player]["assists"] = average_stats_per_player_away[player]["assists"] * (1+def_impact*away_goal_shift)
        average_stats_per_player_away[player]["shots_on_goal"] = average_stats_per_player_away[player]["shots_on_goal"] * (1+def_impact*away_sog_shift)
        




     ## we fetch the actual values, and make comparisons with the predictions
    player_df = simulate_fetch_data_for_game(gameid, "2021")






    row_count = 1  #we want to keep track of the row count to be able to start the second team at a specific row number
    rows_to_write = []
    for player in average_stats_per_player_home:
        player_predictions = {}
        for stat in average_stats_per_player_home[player]:
            if stat != "percent_played":
                player_predictions[stat]  = average_stats_per_player_home[player][stat]*average_stats_per_player_home[player]["percent_played"]*60 
        player_predictions["points"]  =    player_predictions["goals"] + player_predictions["assists"]
        row_to_write = [hometeam, player]
        stat_order = ["points", "goals", "assists", "shots_on_goal", "saves"]
        for stat in stat_order:
            row_to_write.append(player_predictions[stat]) # predicted value

        rows_to_write.append(row_to_write)
    
    ordered_rows = sorted(rows_to_write, key=itemgetter(6), reverse=True)
    # we first sort on saves to get the goalies 
    for row in ordered_rows:
        if row[6] == 0: #if the player is not a goalie anymore
            break
        row_count += 1
        
    ordered_rows = ordered_rows[row_count-1:]
    # and now we sort by goals
    ordered_rows = sorted(ordered_rows, key=itemgetter(2), reverse=True)
    player_num = 0
    for row in ordered_rows:
        # for the top 10 players, we want to check how different the prediction was 
        
        player_actual_values = player_df.loc[player_df['Unnamed: 0'] == row[1]]
        if player_actual_values.empty or player_actual_values is None :
            # player didnt play
            continue
        else:
            points_score += abs(player_actual_values["points"].item() - row[2])
            goals_score += abs(player_actual_values["goals"].item() - row[3])
            assists_score += abs(player_actual_values["assists"].item() - row[4])
        
        if player_num >= 10:
            break
        
        player_num += 1
    
    
    ## and now we do the same thing for the away team
    row_count = 49
    rows_to_write = []
    for player in average_stats_per_player_away:
        player_predictions = {}
        for stat in average_stats_per_player_away[player]:
              if stat != "percent_played":
                player_predictions[stat]  = average_stats_per_player_away[player][stat]*60*average_stats_per_player_away[player]["percent_played"]
        player_predictions["points"]  = player_predictions["goals"] + player_predictions["assists"]
        row_to_write = [awayteam, player]
        stat_order = ["points", "goals", "assists", "shots_on_goal", "saves"]
        for stat in stat_order:
            row_to_write.append(player_predictions[stat]) # predicted value

        rows_to_write.append(row_to_write)

         
    ordered_rows = sorted(rows_to_write, key=itemgetter(6), reverse=True)
    # we first sort on saves to get the goalies 
    for row in ordered_rows:
        if row[6] == 0: #if the player is not a goalie anymore
            break
        row_count += 1    
    
    ordered_rows = ordered_rows[row_count-49:]
    # and now we sort by goals
    player_num = 0
    ordered_rows = sorted(ordered_rows, key=itemgetter(2), reverse=True)
    for row in ordered_rows:
        player_actual_values = player_df.loc[player_df['Unnamed: 0'] == row[1]]
        if player_actual_values.empty or player_actual_values is None :
            # player didnt play
            continue
        else:
            points_score += abs(player_actual_values["points"].item() - row[2])
            goals_score += abs(player_actual_values["goals"].item() - row[3])
            assists_score += abs(player_actual_values["assists"].item() - row[4])
        if player_num >= 10:
            break
        player_num += 1
    

   
    
    
    return points_score, goals_score, assists_score
    
    
    
def get_values_for_player(playerid, current_season, games_played, isHome, opponent):
    data = {"l10":0.0, "l5":0.0, "season":0.0, "location":0.0, "overall":0.0}
    rows = ["goals", "assists", "shots", "shots_on_goal", "saves", "time_on_ice"]
    df = pd.DataFrame(data, index=rows)
    # we go through each game that the player has played so far
    # if it matches the criteria we add the stat from that game to the specific list
    # and then we compute the average of the games in each list and thats what we want to return
    total_defrating = 0
    counted  = 0

    data_stored = {"l10":{"goals":[], "assists":[], "saves":[],"shots_on_goal":[],"percent_played":[]},
                     "l5":{"goals":[], "assists":[], "saves":[], "shots_on_goal":[],"percent_played":[]},
                 "overall":{"goals":[], "assists":[], "saves":[], "shots_on_goal":[],"percent_played":[]},
                 "location":{"goals":[], "assists":[], "saves":[], "shots_on_goal":[],"percent_played":[]},
                 "opponent":{"goals":[], "assists":[], "saves":[], "shots_on_goal":[],"percent_played":[]} }
    data_stored[str(current_season)] = {"goals":[], "assists":[], "saves":[], "shots_on_goal":[],"percent_played":[]}
    
    prev_season = ""
    types = ["goals", "assists", "shots_on_goal", "saves", "percent_played"]

    for game_num in range(len(games_played)):
        [gameid, season, playoff] = games_played[game_num]
        if season != prev_season: 
            data_stored["l5"] = {"goals":[], "assists":[], "saves":[], "shots_on_goal":[],"percent_played":[]}
            data_stored["l10"] = {"goals":[], "assists":[], "saves":[], "shots_on_goal":[],"percent_played":[]}
        prev_season = season
        
            ## we want to reinitialize the l5 and l10 game stats. 
        if season not in data_stored.keys():
            data_stored[str(season)] = {"goals":[], "assists":[], "saves":[], "shots_on_goal":[],"percent_played":[]}
        # then we want to compute the values. taking only into account games 0 ... game_num
        game_stats = fetch_playerstat_for_player(season,gameid, playerid)
        if(game_stats.empty or  game_stats["time_on_ice"]==0):
            continue
        time_on_ice = game_stats["time_on_ice"]
        pp = time_on_ice/game_stats["total_game_minutes"]
        goals = game_stats["goals"]/time_on_ice
        ast = game_stats["assists"]/time_on_ice
        sog = game_stats["shots_on_goal"]/time_on_ice
      
        if math.isnan(game_stats["saves"]):
            saves = 0
        else:
            saves = game_stats["saves"]/time_on_ice
        
        counted += 1
        
        add_to_loc = False
        if(game_stats["isHome"] == "True" and isHome) or (game_stats["isHome"] == "False" and not isHome):
            add_to_loc = True
            
        same_opponent =  False
        if game_stats["opponent"] == opponent:
            same_opponent = True
            
        values = [goals, ast, sog, saves, pp]
        cutoff = [1,1, 3, 35, 0.5 ]
        ## we want to make sure that the player has player has played enough games
        # and that his last game was not too long ago
        for i in range(len(types)):
            if values[i] > cutoff[i]:
                values[i] = cutoff[i]
            
            data_stored["overall"][types[i]].append(values[i])  
            data_stored[str(season)][types[i]].append(values[i])
            if add_to_loc:
                data_stored["location"][types[i]].append(values[i])
            if same_opponent:
                data_stored["opponent"][types[i]].append(values[i])
                
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
     
    for i in range(len(types)):
        type = types[i]
        if len(data_stored["overall"][type]) <= 3:
            return pd.DataFrame(), 0,0
        
        overall_avg =  sum(data_stored["overall"][type])/len(data_stored["overall"][type])

        if(len(data_stored[str(current_season)][type]) >= 1):
            season_avg = sum(data_stored[str(current_season)][type])/len(data_stored[str(current_season)][type])
            l10_avg =  sum(data_stored["l10"][type])/len(data_stored["l10"][type])
            l5_avg =  sum(data_stored["l5"][type])/len(data_stored["l5"][type])
            if len(data_stored["location"][type]) >= 5:
                loc_avg =  sum(data_stored["location"][type])/len(data_stored["location"][type])
            else:
                loc_avg = season_avg
            if len(data_stored[str(current_season)][type]) <= 5: 
                ## if the player has not played a lot that season, we also want to take into account his overall 
                ## average. And we do the same for the l5 and l10 averages
                season_avg = 0.66*season_avg + 0.33*overall_avg
                loc_avg = season_avg
                l5_avg = 0.66*l5_avg + 0.33*overall_avg
                l10_avg = 0.66*l10_avg + 0.33*overall_avg

        else:
            season_avg = overall_avg
            l10_avg = overall_avg
            l5_avg = overall_avg
            loc_avg = overall_avg
        
        
        if  len(data_stored["opponent"][type]) >= 5:
            opponent_avg = sum(data_stored["opponent"][type])/len(data_stored["opponent"][type])
        else:
            opponent_avg = 0
            
        df.at[type,"opponent"] = opponent_avg
        df.at[type,"l10"] = l10_avg
        df.at[type,"l5"] = l5_avg
        df.at[type,"season"] = season_avg
        df.at[type,"location"] = loc_avg
        df.at[type,"overall"] = overall_avg
        
    return df, total_defrating/counted, len(data_stored[str(current_season)]["goals"])
    
    
    
    
simulate_season()  
    
    
    
    
    