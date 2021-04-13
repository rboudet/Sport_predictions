#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 26 13:46:55 2021

@author: romainboudet

Version 2 of the NBA props model for Sports Interaction

This model differs from previous ones by using individual player weights that are trained on past data to minimize the difference 
between the actual value and previous data.
"""

from sportsreference.nhl.roster import Roster
from sportsreference.nhl.teams import Teams
from nhl_fetch_data import fetch_playerstat_for_player,fetch_injured_player_list, fetch_data_for_all_games
from nhl_optimized_values  import compute_opt_weights
import pandas as pd
from scipy.stats import poisson
import os
import xlsxwriter
from operator import itemgetter
import unidecode
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from datetime import datetime
import math
    
# these weights are the ones that will be assigned to each game that meet a certain
# criterion. The base weight is 0. If the game is played at the same location (home/away)
# we add the location-weight. If the game is against the same opponent, we add the
# opponent_weight. If the game is being played in the current season, we add the season_weight
# and finally if this game is one of the last 10 games the player has played, we add
# the l10_weight - how long it has been since thats game (for the last game we add l10_weight
# for the one before l10_weight-1 and so on)


## for playoff ##
po_l10_weight = 0.2
po_l5_weight = 0.2
po_location_weight = 0.1
po_opponent_weight = 0
po_season_weight = 0.1
po_playoff_weight = 0.2
po_overall_weight = 0.2


## for regular season ##
reg_l5_weight = 0
reg_l10_weight = 0.1
reg_location_weight = 0.1
reg_opponent_weight = 0
reg_season_weight = 0.4
reg_overall_weight = 0.4
reg_playoff_weight = 0

'''
This method computes the number of days since a given player's last game
'''
def days_since_last_game(season, playerid, current_team): 
    try:
        file = open(f"Data/{season}/Players/{playerid}.txt", 'r')
        lines = file.readlines()
        last_game = lines[-1]
        file.close()
        date_of_game = datetime(int(last_game[:4]),int(last_game[4:6]), int(last_game[6:8]) )
        game_df = pd.read_csv(f"Data/{season}/Games/{last_game}_players.csv")
        team =  game_df.loc[game_df["Unnamed: 0"] == playerid].team.item()
        ## if the last game that the player 
        if team != current_team:
            return -1
        return (datetime.today() - date_of_game).days 
    except:
        return 50
  
    
## this function fetches the number of games that the player has played within the last 20 games of that team
def num_games_played_l20(season, playerid, current_team): 
    try:
        team_schedule = pd.read_csv(f"Data/{season}/Teams/{current_team}_schedule.csv")
    except:
        ## schedule has not been loaded 
        teams = Teams(season)
        for team in teams:
            team_schedule = Schedule(team.abbreviation, season)
            df = team_schedule.dataframe
            df.to_csv(f"Data/{season}/Teams/{team.abbreviation}_schedule.csv")
        team_schedule = pd.read_csv(f"Data/{season}/Teams/{current_team}_schedule.csv")

    
    try:
        games = []
        for index,row in team_schedule.iterrows():
            datestring = str(row["datetime"])
            values = datestring.split(" ")[0].split("-")
            game_date=datetime(int(values[0]), int(values[1]), int(values[2]))
            if game_date < datetime.today():
                games.append(row["boxscore_index"])
            else:
                break
        games = games[:-1]
        if len(games) >= 20:
            games = games[len(games)-20:]        
        file = open(f"Data/{season}/Players/{playerid}.txt", 'r')
        lines = file.readlines()
        counter = 0
        for gameid in lines:
            if gameid.strip() in games:
                counter += 1
        file.close()
        
        return counter
       
    except:
        return 0
    
    
'''
In this method, we are given a player, the current season, a list of all the games we want to take into account 
and some information about the game. 
And we through all those games and compute the average stats for the given player and create different averages :
    - last 10 games
    - last 5 games
    - against the given opponent
    - at the location (home/away)
    - of the current season
    - overall for the player

'''    
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
    for game_num in range(len(games_played)):
        [gameid, season, isPlayoff] = games_played[game_num]
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
            
        types = ["goals", "assists", "shots_on_goal", "saves", "percent_played"]
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
    
    
'''
This will be the main function for the predictions
It takes as input all the information necessary to compute the predictions (the variable names are self explanatory)

for each player on the home/away team it generates the averages over the games we are taking into account
it goes to fetch the optimal weights for that player, and this creates the value per minute the player is expected to obtain. 

We then take into account injured players and opposing teams defense to shift up or down those values accordingly

Then using a poisson distribution, we generate the expected number of points/assists/rebounds etc that the player will obtain
with the probability that the outcome will be above or below that number. 

The output will be in a csv file, in the 'predictions' folder. 
'''

def generate_expected_statistics(date, hometeam, awayteam, seasons_to_use, current_season, is_playoff_game, predict_for_gtd,  injuries, gtd):
    
    # we fetch the injured player lists for both teams
#    injuries = fetch_injured_player_list()
    home_injured_players = []
    away_injured_players = []
    home_gtd_players = []
    away_gtd_players = []
    try:
        home_injured_players = injuries[hometeam]
    except:
        #ie there are no injured players on the hometeam
        pass
    try:
        away_injured_players = injuries[awayteam]
                
    except:
        #ie there are no injured players on the awayteam
        pass
    
    try:
        home_gtd_players = gtd[hometeam]
    except:
        pass
   
    try:
        away_gtd_players = gtd[awayteam]
    except:
        pass
    
    
    #we then want to fetch and store the latest updated roster for each team. 
    print("updating roster files")
    for abbrv in [hometeam, awayteam]:
        roster = Roster(abbrv, current_season, True)
        file = open(f"Data/{current_season}/Teams/{abbrv}.txt", "w", encoding='utf-8')
        count = 0
        for playerid in roster.players:
            playername = roster.players[playerid]
            if count == 0:
                file.write(playername + ":" + playerid)
            else:
                 file.write(f"\n{str(playername)}:{playerid}")
            count += 1
        file.close()    
        
    #we set the correct default weights we want to use 
    if is_playoff_game:
        l10_weight = po_l10_weight
        opponent_weight = po_opponent_weight
        season_weight = po_season_weight
        location_weight = po_location_weight
        playoff_weight = po_playoff_weight
        l5_weight = po_l5_weight
        overall_weight = po_overall_weight
    else:
        l10_weight = reg_l10_weight
        l5_weight = reg_l5_weight
        opponent_weight = reg_opponent_weight
        season_weight = reg_season_weight
        location_weight = reg_location_weight
        playoff_weight = reg_playoff_weight
        overall_weight = reg_overall_weight
    
    # we create the default dataframe for the weights 
    types = ["goals", "assists", "shots", "shots_on_goal", "saves", "percent_played"]
    data = {"l10":[l10_weight,l10_weight,l10_weight,l10_weight,l10_weight, l10_weight], 
                   "l5":[l5_weight,l5_weight,l5_weight,l5_weight,l5_weight,l5_weight], 
                   "season":[season_weight,season_weight,season_weight,season_weight,season_weight,season_weight], 
                   "location":[location_weight,location_weight,location_weight,location_weight,location_weight,location_weight], 
                   "overall":[overall_weight,overall_weight,overall_weight,overall_weight,overall_weight,overall_weight]}
    default_weights_df = pd.DataFrame(data, index=types)
    
    date = date.strftime('%m-%d-%Y')  # format the date 
    player_names = {}
    home_injured = []
    away_injured = []
    
    
    #We keep track of player names and select which players are injures
    file = open(f"Data/{current_season}/Teams/{hometeam}.txt", "r", encoding="utf8")
    home_players = []
    for line in file:
        temp = (line.rstrip()).split(":")
        playerid = temp[1]
        playername = temp[0]
        ## now we want to create the format firstLetter. Lastname
        first_name = playername.split(' ')[0]
        last_name = playername.split(' ')[1]
        format_name = f"{first_name[0]}. {last_name}"
        format_name = unidecode.unidecode(format_name)
        for name in home_injured_players:
            if (format_name == name) or (format_name in name) or (name in format_name):
                home_injured.append(playerid)
        if not predict_for_gtd:
            for name in home_gtd_players:
                if (format_name == name) or (format_name in name) or (name in format_name):
                    home_injured.append(playerid)    
        home_players.append(playerid)
        player_names[playerid] = temp[0]         
    file.close()
    
    # do the same thing for the away players
    file = open(f"Data/{current_season}/Teams/{awayteam}.txt", "r", encoding="utf8")
    away_players = []
    for line in file:
        temp = (line.rstrip()).split(":")
        playerid = temp[1]
        playername = temp[0]
        ## now we want to create the format firstLetter. Lastname
        first_name = playername.split(' ')[0]
        last_name = playername.split(' ')[1]
        format_name = f"{first_name[0]}. {last_name}"
        format_name = unidecode.unidecode(format_name)

        for name in away_injured_players:
            if (format_name == name) or (format_name in name) or (name in format_name):
                away_injured.append(playerid)
        if not predict_for_gtd:
            for name in away_gtd_players:
                if (format_name == name) or (format_name in name) or (name in format_name):
                    away_injured.append(playerid)

        away_players.append(playerid)
        player_names[playerid] = temp[0]
        
    file.close()
    
    home_avg_goals_allowed = 0
    home_avg_sog_allowed = 0
    away_avg_goals_allowed = 0
    away_avg_sog_allowed = 0
    
    league_avg_goals_allowed = 0
    league_avg_sog_allowed = 0
    if os.path.isfile(f"Data/{current_season}/defense_file.csv"):
        defense_df = pd.read_csv(f"Data/{current_season}/defense_file.csv")
        defense_df = defense_df.set_index('team_names')

    else:
        defense_df = pd.read_csv(f"Data/{int(current_season)-1}/defense_file.csv")
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
    home_injury_shift = 0
    away_injury_shift = 0
    home_injury_total = 0
    away_injury_total = 0
    home_injury_return = 0
    away_injury_return =  0
    indices = ["l10", "l5", "season", "location", "overall", "opponent"]
    stat_types = ["goals", "assists", "shots", "shots_on_goal", "saves", "percent_played"]
    # we order the seasons in increasing order
    seasons = sorted([int(x) for x in seasons_to_use])
    for player in home_injured:
        home_players.remove(player)
    ordered_home_players = home_injured + home_players ## we want to put the injured players first (so that the injury shift is already computed)
    
    
    for player in away_injured:
        away_players.remove(player)
    ordered_away_players = away_injured + away_players
#    
    for player in ordered_home_players:        
        ## we fetch the optimal weights for the given player
        # if there are none, this method will return the default weights provided
#        weights_df = compute_opt_weights(player, seasons, default_weights_df)
        weights_df = default_weights_df
        gameids = []
        playoff_games = []
        for season in seasons:
            season = str(season)
            try:
                gameid_file = open(f"Data/{season}/Players/{player}.txt")
                for x in gameid_file.readlines():
                    gameids.append([x.strip(),season,False])
                gameid_file.close()
            except:
                #the player has no games played in this season
                pass
            
            ## if this is a playoff game then we also want to take into account playoff games for the given player
            if is_playoff_game:
                try:
                    gameid_file = open(f"Data/{season}/Players/{player}_playoff.txt")
                    for x in gameid_file.readlines():
                        gameids.append([x.strip(),season,True])                
                    gameid_file.close()
                except:
                    # player has no playoff data for this season
                    pass
        
        
        if len(gameids) >= 10 :
            df,def_rating,gp_season = get_values_for_player(player, current_season, gameids , True, awayteam)
            num_l20_games_played = num_games_played_l20(current_season, player, hometeam)
            
            
            #if the player hasnt played in the recent games and is a significant player
            points = (df.at["goals", "season"]+df.at["assists", "season"])*df.at["percent_played", "season"]*60
            if (player not in home_injured) and gp_season >= 5 and num_l20_games_played <= 5 and  points>= 0.7:
                print(f"player {player} is returning for {hometeam}")
                #ie the player is coming back but hasnt played a lot of games in the last 20
                if  points >= 1:
                    percent = 1
                else:
                    percent = points
                home_injury_return +=  percent *(7-num_l20_games_played)/7

                if home_injury_return >=  1:
                    home_injury_return = 1
            
            
            
            for type in stat_types:
                overall = df.at[type, "overall"]
                season = df.at[type, "season"]
                l5 = df.at[type, "l5"]
                l10 = df.at[type, "l10"]
                
                if df.at[type, "opponent"] == 0:
                    df.at[type, "opponent"] = df.at[type, "season"]
                    
                   
                if home_injury_total >= 0.25  and  weights_df.at[type, "l5"] <= 0.4: 
                    if type == "percent_played":
                        weights_df.at[type, "l5"] += 0.33* weights_df.at[type, "season"]
                        weights_df.at[type, "season"] = 2*weights_df.at[type, "season"]/3
                    else:
                        weights_df.at[type, "l5"] += 0.25* weights_df.at[type, "overall"]
                        weights_df.at[type, "l10"] += 0.25* weights_df.at[type, "overall"]
                        weights_df.at[type, "overall"] = weights_df.at[type, "overall"]/2
                
                # if a significant player is returning from injury, then we shift the weight back to 
#                # the season average 
                if home_injury_return >= 0.25:
                    if type == "percent_played" :
                        weights_df.at[type, "season"] += 0.25* weights_df.at[type, "l5"]
                        weights_df.at[type, "l5"] = 3*weights_df.at[type, "l5"]/4
                        if home_injury_return >= 0.6:
                            weights_df.at[type, "season"] += 0.25* weights_df.at[type, "l5"]
                            weights_df.at[type, "l5"] = 3*weights_df.at[type, "l5"]/4
                    else:
                        if home_injury_return >= 0.6:
                            weights_df.at[type, "season"] += 0.25* weights_df.at[type, "l5"]
                            weights_df.at[type, "season"] += 0.25* weights_df.at[type, "l10"]
                            weights_df.at[type, "l10"] = 3*weights_df.at[type, "l10"]/4
                            weights_df.at[type, "l5"] = 3*weights_df.at[type, "l5"]/4
                        weights_df.at[type, "season"] += 0.25* weights_df.at[type, "l5"]
                        weights_df.at[type, "season"] += 0.25* weights_df.at[type, "l10"]
                        weights_df.at[type, "l10"] = 3*weights_df.at[type, "l10"]/4
                        weights_df.at[type, "l5"] = 3*weights_df.at[type, "l5"]/4  
            if df.empty:
                continue
        
            elif player in home_injured:
                time_played = df.at["percent_played", "season"]
                points =  (df.at["goals", "season"] + df.at["assists", "season"])*time_played*60
                days_since_game = days_since_last_game(current_season, player, hometeam)
                if days_since_game != -1:
                    if points >= 0.5:
                        shift = points
                        if shift >=  1:
                            shift = 1
                        if days_since_game <= 30:
                            ## we want to do this only if the player has been injured for a long time
                            home_injury_shift += shift * (40-days_since_game)/50
                            home_injury_total += shift   
                            if home_injury_shift >= 1:
                                home_injury_shift = 1
                        elif days_since_game <= 60:
                            home_injury_total += shift    
                            
            else:
                average_stats_per_player_home[player] = {}
                for stat in stat_types:
                    value = 0
                    for index in indices: 
                        value += df.at[stat, index] * weights_df.at[stat, index]
                    average_stats_per_player_home[player][stat] = value
        else:
            not_predicting[hometeam].append(player)
        
    for player in ordered_away_players:
#        weights_df = compute_opt_weights(player, seasons, default_weights_df)
        weights_df = default_weights_df

        gameids = []
        playoff_games = []
        for season in seasons:
            season = str(season)
            try:
                gameid_file = open(f"Data/{season}/Players/{player}.txt")
                for x in gameid_file.readlines():
                    gameids.append([x.strip(),season,False])
                gameid_file.close()
            except:
                #the player has no games played in this season
                pass
            
            if is_playoff_game:
                try:
                    gameid_file = open(f"Data/{season}/Players/{player}_playoff.txt")
                    for x in gameid_file.readlines():
                        gameids.append([x.strip(),season, True])   
                    gameid_file.close()
                except:
                    # player has no playoff data for this season
                    pass
        
        if len(gameids) >= 10:
            df, def_rating,gp_season = get_values_for_player(player, current_season, gameids , False, hometeam)
            
            num_l20_games_played = num_games_played_l20(current_season, player, awayteam)

            points = (df.at["goals", "season"]+df.at["assists", "season"])*df.at["percent_played", "season"]*60
            if (player not in away_injured) and gp_season >= 5 and num_l20_games_played <= 5 and points >= 0.7:
                print(f"player {player} is returning for {awayteam}")
                #ie the player is coming back but hasnt played a lot of games in the last 20
                if  points >= 1:
                    percent = 1
                else:
                    percent = points
                away_injury_return +=  percent * (7-num_l20_games_played)/7

                if away_injury_return >=  1:
                    away_injury_return = 1
            
            
            for type in types:
                overall_avg = df.at[type, "overall"]
                season_avg = df.at[type, "season"]
                l5 = df.at[type, "l5"]
                l10 = df.at[type, "l10"]
                
                
                if df.at[type, "opponent"] == 0:
                    df.at[type, "opponent"] =df.at[type, "season"]
            
                if away_injury_total >= 0.25  and  weights_df.at[type, "l5"] <= 0.4: 
                    if type == "percent_played":
                        weights_df.at[type, "l5"] += 0.33* weights_df.at[type, "season"]
                        weights_df.at[type, "season"] = 2*weights_df.at[type, "season"]/3
                    else:
                        weights_df.at[type, "l5"] += 0.25* weights_df.at[type, "overall"]
                        weights_df.at[type, "l10"] += 0.25* weights_df.at[type, "overall"]
                        weights_df.at[type, "overall"] = weights_df.at[type, "overall"]/2
                
                # if a significant player is returning from injury, then we shift the weight back to 
#                # the season average 
                if away_injury_return >= 0.25:
                    if type == "percent_played" :
                        weights_df.at[type, "season"] += 0.25* weights_df.at[type, "l5"]
                        weights_df.at[type, "l5"] = 3*weights_df.at[type, "l5"]/4
                        if home_injury_return >= 0.6:
                            weights_df.at[type, "season"] += 0.25* weights_df.at[type, "l5"]
                            weights_df.at[type, "l5"] = 3*weights_df.at[type, "l5"]/4
                    else:
                        if away_injury_return >= 0.6:
                            weights_df.at[type, "season"] += 0.25* weights_df.at[type, "l5"]
                            weights_df.at[type, "season"] += 0.25* weights_df.at[type, "l10"]
                            weights_df.at[type, "l10"] = 3*weights_df.at[type, "l10"]/4
                            weights_df.at[type, "l5"] = 3*weights_df.at[type, "l5"]/4
                        weights_df.at[type, "season"] += 0.25* weights_df.at[type, "l5"]
                        weights_df.at[type, "season"] += 0.25* weights_df.at[type, "l10"]
                        weights_df.at[type, "l10"] = 3*weights_df.at[type, "l10"]/4
                        weights_df.at[type, "l5"] = 3*weights_df.at[type, "l5"]/4  
            if df.empty:
                continue
        
            elif player in away_injured:
                time_played = df.at["percent_played", "season"]
                points = (df.at["goals", "season"] + df.at["assists", "season"])*time_played*60
                days_since_game = days_since_last_game(current_season, player, awayteam)
#                print(f"player {player} is injured, days since game : {days_since_game}, points : {points}")

                if days_since_game != -1:
                    if points >= 0.5:
                        shift = points
                        if shift >=  1:
                            shift = 1
                        if days_since_game <= 30:
                            ## we want to do this only if the player has been injured for a long time
                            away_injury_shift += shift * (40-days_since_game)/50
                            away_injury_total += shift    
                            if away_injury_shift >= 1:
                                away_injury_shift = 1
                        elif days_since_game <= 60:
                            away_injury_total += shift    
            else:
                average_stats_per_player_away[player] = {}
                for stat in stat_types:
                    value = 0
                    for index in indices: 
                        value += df.at[stat, index] * weights_df.at[stat, index]
                    
                    average_stats_per_player_away[player][stat] = value
        else:
            not_predicting[awayteam].append(player)
            
    for player in average_stats_per_player_away:
        for stat in ["assists", "goals", "shots_on_goal"]:
            average_stats_per_player_away[player][stat] =   average_stats_per_player_away[player][stat]*(1+0.05*away_injury_shift)
    for player in average_stats_per_player_home:
        for stat in ["assists", "goals", "shots_on_goal"]:
            average_stats_per_player_home[player][stat] =   average_stats_per_player_home[player][stat]*(1+0.05*home_injury_shift)
    for player in average_stats_per_player_away:
        for stat in ["assists", "goals", "shots_on_goal"]:
            average_stats_per_player_away[player][stat] =   average_stats_per_player_away[player][stat]*(1-0.05*away_injury_return) 
    for player in average_stats_per_player_home:
        for stat in ["assists", "goals", "shots_on_goal"]:
            average_stats_per_player_home[player][stat] =   average_stats_per_player_home[player][stat]*(1-0.05*home_injury_return) 

    ## we calculate the average defense rating of the teams playing
    ## depending on that value we will either increase or decrease the per minute value by a small factor. 
    
    
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
        average_stats_per_player_home[player]["goals"] = average_stats_per_player_home[player]["goals"] * (1+0.1*home_goal_shift)
        average_stats_per_player_home[player]["assists"] = average_stats_per_player_home[player]["assists"] * (1+0.1*home_goal_shift)
        average_stats_per_player_home[player]["shots_on_goal"] = average_stats_per_player_home[player]["shots_on_goal"] * (1+0.1*home_sog_shift)
    for player in average_stats_per_player_away:
        average_stats_per_player_away[player]["goals"] = average_stats_per_player_away[player]["goals"] * (1+0.1*away_goal_shift)
        average_stats_per_player_away[player]["assists"] = average_stats_per_player_away[player]["assists"] * (1+0.1*away_goal_shift)
        average_stats_per_player_away[player]["shots_on_goal"] = average_stats_per_player_away[player]["shots_on_goal"] * (1+0.1*away_sog_shift)
        
    
#    print(f"home goal rating : {home_def_goals_rating}")
#    print(f"home sog rating : {home_def_sog_rating}")
#    
#    print(f"away goal rating : {away_def_goals_rating}")
#    print(f"away sog rating : {away_def_sog_rating}")
    
    print(f"home injury shift : {home_injury_shift}")
    print(f"home injury total : {home_injury_total}")
    
    print(f"away injury shift : {away_injury_shift}")
    print(f"away injury total : {away_injury_total}")
    
    print(f"home injury return : {home_injury_return}")
    print(f"away injury return : {away_injury_return}")



    ### now we start writing to the excel file
    dir_path = f"predictions/{date}"
    try:
        os.mkdir("predictions")
    except:
        pass    
    try:
        os.mkdir(dir_path)
    except:
        pass
    
    workbook = xlsxwriter.Workbook(f"{dir_path}/{hometeam}_{awayteam}.xlsx")
    worksheet = workbook.add_worksheet()
    worksheet.write_row(0, 0, ["Team", "Player", "Points", "Points SIA", "Points prob over", "Points prob under ","Points line over", "Points line under ",
                               "Goals", "Goals SIA", "Goals prob over" ,"Goals prob under","Goals line over" ,"Goals line under", "Assists", "Assists SIA", 
                               "Assists prob over", "Assists prob under",  "Assists line over", "Assists line under", "Shots_on_goal", "Shots_on_goal SIA", 
                               "Shots_on_goal prob over", "Shots_on_goal prob under", "Shots_on_goal line over", "Shots_on_goal line under","saves", "saves SIA",
                               "saves prob over", "saves prob under", "saves line over", "saves line under"])

    row_count = 1  #we want to keep track of the row count to be able to start the second team at a specific row number
    rows_to_write = []
    for player in average_stats_per_player_home:
        player_predictions = {}
        for stat in average_stats_per_player_home[player]:
            if stat != "percent_played":
                player_predictions[stat]  = average_stats_per_player_home[player][stat]*average_stats_per_player_home[player]["percent_played"]*60 
        player_predictions["points"]  =    player_predictions["goals"] + player_predictions["assists"]
        row_to_write = [hometeam, player_names[player]]
        stat_order = ["points", "goals", "assists", "shots_on_goal", "saves"]
        for stat in stat_order:
            row_to_write.append(player_predictions[stat]) # predicted value
            if stat == "points" or stat=="goals":
                sia_value = 0.5
            else:
                sia_value = int(player_predictions[stat]) + 0.5
            row_to_write.append(sia_value) #value that we should put in SIA
            prob_under =  poisson.cdf(sia_value-0.5, player_predictions[stat]) #*48*average_stats_per_player_home[player]["percent_played"])  # prob of being under the SIA value
            prob_over = 1-prob_under # prob of being over the SIA value
            row_to_write.append(prob_over*100)
            row_to_write.append(prob_under*100)
            if prob_over == 0:
                prob_over = 0.00001
            if prob_under == 0:
                prob_under = 0.00001
            line_over = 1/(prob_over*1.08)
            if math.isnan(line_over) or math.isinf(line_over) or line_over > 100:
                line_over = 100
            row_to_write.append(line_over)
            line_under = 1/(prob_under*1.08)
            if math.isnan(line_under) or math.isinf(line_under) or line_under>100:
                line_over = 100
            row_to_write.append(line_under)

        rows_to_write.append(row_to_write)
    
    ordered_rows = sorted(rows_to_write, key=itemgetter(26), reverse=True)
    # we first sort on saves to get the goalies 
    for row in ordered_rows:
        if row[26] == 0: #if the player is not a goalie anymore
            break
        worksheet.write_row(row_count, 0, row)
        row_count += 1
        
    ordered_rows = ordered_rows[row_count-1:]
    # and now we sort by goals
    ordered_rows = sorted(ordered_rows, key=itemgetter(2), reverse=True)
    for row in ordered_rows:
        worksheet.write_row(row_count, 0, row)
        row_count += 1

    for player in not_predicting[hometeam]:
        worksheet.write_row(row_count, 0, [hometeam, player_names[player], "Not predicting, players has not played enough"])
        row_count += 1
    for player in home_injured_players:
        worksheet.write_row(row_count, 0, [hometeam, player, "Player is injured"])
        row_count += 1
    
    
    
    ## and now we do the same thing for the away team
    row_count = 49
    rows_to_write = []
    for player in average_stats_per_player_away:
        player_predictions = {}
        for stat in average_stats_per_player_away[player]:
              if stat != "percent_played":
                player_predictions[stat]  = average_stats_per_player_away[player][stat]*60*average_stats_per_player_away[player]["percent_played"]
        player_predictions["points"]  = player_predictions["goals"] + player_predictions["assists"]
        row_to_write = [awayteam, player_names[player]]
        stat_order = ["points", "goals", "assists", "shots_on_goal", "saves"]
        for stat in stat_order:
            row_to_write.append(player_predictions[stat]) # predicted value
            if stat == "points" or stat=="goals":
                sia_value = 0.5
            else:
                sia_value = int(player_predictions[stat]) + 0.5  
            row_to_write.append(sia_value) #value that we should put in SIA
            prob_under =  poisson.cdf(sia_value-0.5, player_predictions[stat]) #*48*average_stats_per_player_away[player]["percent_played"])  # prob of being under the SIA value
            prob_over = 1-prob_under # prob of being over the SIA value
            row_to_write.append(prob_over*100)
            row_to_write.append(prob_under*100)
            if prob_over == 0:
                prob_over = 0.00001
            if prob_under == 0:
                prob_under = 0.00001
            line_over = 1/(prob_over*1.08)
            if math.isnan(line_over) or math.isinf(line_over) or line_over > 100:
                line_over = 100
            row_to_write.append(line_over)
            line_under = 1/(prob_under*1.08)
            if math.isnan(line_under) or math.isinf(line_under) or line_under>100:
                line_over = 100
            row_to_write.append(line_under)

        rows_to_write.append(row_to_write)

         
        
    goalie_rows = []
    ordered_rows = sorted(rows_to_write, key=itemgetter(26), reverse=True)
    # we first sort on saves to get the goalies 
    for row in ordered_rows:
        if row[26] == 0: #if the player is not a goalie anymore
            break
        worksheet.write_row(row_count, 0, row)
        row_count += 1    
    
    ordered_rows = ordered_rows[row_count-49:]
    # and now we sort by goals
    ordered_rows = sorted(ordered_rows, key=itemgetter(2), reverse=True)
    for row in ordered_rows:
        worksheet.write_row(row_count, 0, row)
        row_count += 1
    
    for player in not_predicting[awayteam]:
        worksheet.write_row(row_count, 0, [awayteam, player_names[player], "Not predicting, players has not played enough"])
        row_count += 1 
    for player in away_injured_players:
        worksheet.write_row(row_count, 0, [awayteam,player, "Player is injured"])
        row_count += 1

    workbook.close()

 

def generate_all_game_predictions(date, email_recipient, predict_for_gtd, send_email=False):
    
    year = datetime.today().year
    current_season = year
    seasons_to_use = [current_season-1, current_season]
    while True:
    ## we want to get the current season. We first try to see if we are the very beginning of a season
        try:
            Teams(str(current_season+1))
            current_season = current_season+1
            seasons_to_use = [current_season-1, current_season]
            
        except:
            #then we are not
            break
    print("Loading data from missing games")
    print(f"And fetching all games happening on : {date.day} / {date.month} / {date.year}")
    games_today = fetch_data_for_all_games(current_season, date)
    print(games_today)
    
    print("fetching injured players")
#    injuries, gtd = fetch_injured_player_list()
#    #we first want to change the team name to the abbreviation
#    file = open("Data/TeamAbbrv.txt", 'r')
#    lines = file.readlines()
#    abbrv_dict = {}
#    for line in lines:
#        values = (line.strip()).split(":")
#        teamname = values[0]
#        teamabbrv = values[1]
#        abbrv_dict[teamname] = teamabbrv
#    file.close()
    final_injuries = {}
    final_gtd  = {}
#    for key in injuries.keys():
#        for key2 in abbrv_dict.keys():
#            if key in key2:
#                final_injuries[abbrv_dict[key2]] = injuries[key]
#    for key in gtd.keys():
#        for key2 in abbrv_dict.keys():
#            if key in key2:
#                final_gtd[abbrv_dict[key2]] = gtd[key]           
#    
    
    for index, row  in games_today.iterrows():
        gameid = row["gameid"]
        home = row["hometeam"]
        away = row["awayteam"]
        print(f"predicting stats for game {gameid}")
        generate_expected_statistics( date, home, away, seasons_to_use, current_season, False, predict_for_gtd, final_injuries, final_gtd)
    
    # once we have made a predictions for each game, we want to send out am email to the line management team with the results
    # if predictions had already been made, we want to only send the data if the predictions have changed (for example if 
    # a player has been ruled out etc ... )
    if send_email:
        strdate = date.strftime('%m-%d-%Y')
        if os.path.isdir(f"predictions/{strdate}"):
            attachments = os.listdir(f"predictions/{strdate}")
            path = f"predictions/{strdate}/"
            subject = f"NHL player props predictions {strdate} "
            body = "Here are the NHL player props predictions for all games happening today"
            print("sending emails ... ")
            try:
                send_automatic_email(attachments,path, email_recipient, subject, body)
                print("Success")
            except:
                print("Failure, trying again") 
                try:
                    send_automatic_email(attachments,path, email_recipient, subject, body)
                    print("Success")
                except:
                    print("Failure, make sure information provided to send the emails is accurate")
    


def send_automatic_email(attachments, directory_path, receiver_email, subject, body):
    
    sender_email = "sportsinteraction.predictions@gmail.com"
    password = "SI_predictions"
    
    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    
    # Add body to email
    message.attach(MIMEText(body, "plain"))


    for filename in attachments:  # add files to the message
        attachment = MIMEApplication(open(directory_path + filename, "rb").read(), _subtype="txt")
        attachment.add_header('Content-Disposition','attachment', filename=filename)
        message.attach(attachment)

    text = message.as_string()
    
    # Log in to server using secure context and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, text)
    
    return True


