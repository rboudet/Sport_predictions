# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 13:38:09 2019

@author: Romain Boudet


This file will be used to fetch and store all the data needed for Baseball data analysis

"""
#from sportsreference.mlb import boxscore
#from sportsreference.mlb import player
#from sportsreference.mlb import roster

from sportsreference.mlb.boxscore import Boxscore, Boxscores
from sportsreference.mlb.teams import Teams
from sportsreference.mlb.roster import Player, Roster
import os
import math
import pandas as pd
from datetime import datetime
import mlbgame
#import importlib

#importlib.reload(player)
#importlib.reload(boxscore)
#importlib.reload(roster)

#### this needs to be updated as a new season starts ###
reg_season_start_dates = { "2020": datetime(2020,7, 23), "2019" : datetime(2019, 3, 20), "2018":datetime(2018, 3, 29),  "2017":datetime(2017, 4, 2), "2016":datetime(2016, 4, 3), "2015":datetime(2015, 4, 5)}
reg_season_end_dates = {"2020":datetime(2020,9, 28),"2019": datetime(2019,9,29), "2018": datetime(2018, 10, 1),  "2017":datetime(2017,10,1), "2016":datetime(2016, 10, 2),"2015":datetime(2015, 10, 4)}

playoff_season_start_dates = {"2020":datetime(2020,9, 29),"2019":datetime(2019,10,1), "2018":datetime(2018,10,2),"2017":datetime(2017,10,3), "2016":datetime(2016,10,3),"2015":datetime(2015, 10, 6)}
playoff_season_end_dates = {"2020":datetime(2020,10,27),"2019":datetime(2019,10,30), "2018":datetime(2018,10,28), "2017":datetime(2017,11,1),"2016":datetime(2016,11,2),"2015":datetime(2015, 11, 1)}



########## PLAYER METHODS ############
     
def fetch_playerstat_for_player(season, gameid, playerid):
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
            total_minutes = convert_time_to_decimal(game_df.iloc[0]["home_minutes_played"])
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


def create_player_data_file(season):
    for filename in os.listdir(f"Data/{season}/Teams"):
        file = open(f"Data/{season}/Teams/{filename}")
        for line in file:
            playerid = (line.strip()).split(":")[1]
            if not os.path.isfile(f"Data/Players/{playerid}.csv"):
                playerinfo = Player(playerid)
                playerinfo.dataframe.to_csv(f"Data/Players/{playerid}.csv")
        file.close()
        

def create_roster_files(season):
    print("Creating roster files")
    try:
        file = open("Data/TeamAbbrv.txt","r")
    except:
        create_team_abbreviation_file()
        file = open("Data/TeamAbbrv.txt","r")
        
    for line in file:
        abbrv = (line.strip()).split(":")[1]
        if not os.path.isfile(f"Data/{season}/Teams/{abbrv}.txt"):
            roster = Roster(abbrv, season, True)
            file2 = open(f"Data/{season}/Teams/{abbrv}.txt", "w")
            k = 0
            for playerid in roster.players:
                k = k + 1
                playername = roster.players[playerid]
                file2.write(playername + ":" + playerid)
                if len(roster.players) != k:
                    file2.write("\n")            
            file2.close()
    file.close()
   
        

########## GAME METHODS #############


def update_gameid_file(season, ongoing):
    if ongoing:
        print("Updating gameid file")
    else:
        print("Creating game id file, this could take some time")

    reg_season_games = []
    playoff_games = []
    try:
        reg_season_start = reg_season_start_dates[season]
    except:
        print("Please add start and end date of the season to the season_start_dates as follows : season:datetime(year,month,day)")
        return
    
    if ongoing :
        # if the season is ongoing, we want to fetch games up to this day
        # we check what the last update date was, and only fetch games in that range
        # if the current date is greater than the end of the regular season, then we also fetch playoff games
        try:
            # we also want to store the last update that we made
            file = open(f"Data/{season}/last_update.txt")
            date_str = file.readlines()[0]
            start = datetime.strptime(date_str,"%m/%d/%Y")
            file.close()
            today = datetime.today()
            if start == datetime(today.year, today.month, today.day):
                return [],[]
        except:
            start = reg_season_start
            
        try:
            reg_season_end = reg_season_end_dates[season]
            if datetime.today() > reg_season_end:
                reg_season_ended = True
            else:
                reg_season_ended = False
        except:
            reg_season_ended = False
        
        if reg_season_ended:
            # now we want to check if the current date is greater then that
            if start < reg_season_end:
                #there are still regular season games to fetch
                file = open(f"Data/{season}/Gameids.txt","a")
                games = Boxscores(start, reg_season_end)
                game_list = games.games
                print("fetching regular season game ids")
                gameids = []
                for key in game_list:
                    day_games = game_list[key]
                    for game in day_games:
                        boxscore = game["boxscore"]
                        if boxscore in gameids:
                            break
                        else:
                            gameids.append(boxscore)
                        
                        file.write(boxscore)
                        file.write("\n")    
                        reg_season_games.append(boxscore)
                                    
                file.close()
            
            start_playoff = playoff_season_start_dates[season]
            if datetime.today() > start_playoff:
                if start > start_playoff:
                    start_playoff = start
                # then we also want to fetch playoff games
                playoff = open(f"Data/{season}/Playoff_Gameids.txt", "a")
                playoff_boxscores = Boxscores(start_playoff, datetime.today())
                playoff_game_list = playoff_boxscores.games
                print("fetching playoff game ids")
                gameids= []
                for key in playoff_game_list:
                    day_games = playoff_game_list[key]
                    for game in day_games:
                        boxscore = game["boxscore"]
                        if boxscore in gameids:
                            break
                        else:
                            gameids.append(boxscore)
                            
                        playoff_games.append(boxscore)
                        playoff.write(boxscore)
                        playoff.write("\n")
                    
                playoff.close()
                
        else:
            # if the regular season hasnt ended, then we just fetch game ids
            # between the last update and today
            
            file = open(f"Data/{season}/Gameids.txt","a")
            games = Boxscores(start, datetime.today())
            game_list = games.games
            gameids = []
            print("fetching regular season game ids")
            for key in game_list:
                day_games = game_list[key]
                for game in day_games:
                    boxscore = game["boxscore"]
                    if boxscore in gameids:
                        break
                    else:
                        gameids.append(boxscore)
                    file.write(boxscore)
                    file.write("\n")
                    reg_season_games.append(boxscore)
            file.close()
            
            
        # and we update the last update to today's date
        file = open(f"Data/{season}/last_update.txt", "w")
        file.write(datetime.today().strftime("%m/%d/%Y"))
        file.close()
       
    else:
        # if the season is not ongoing, ie if we are loading all of the season data at once
        end = reg_season_end_dates[season]
        start = reg_season_start
        start_playoff = playoff_season_start_dates[season]
        end_playoff = playoff_season_end_dates[season]
        file = open(f"Data/{season}/Gameids.txt","w")
        playoff = open(f"Data/{season}/Playoff_Gameids.txt", "w")
        games = Boxscores(start, end)
        playoff_boxscores = Boxscores(start_playoff, end_playoff)
        game_list = games.games
        playoff_game_list = playoff_boxscores.games
        print("fetching all regular season game data")
        gameids = []
        for key in game_list:
            day_games = game_list[key]
            for game in day_games:
                boxscore = game["boxscore"]
                if boxscore in gameids:
                    break
                else:
                    gameids.append(boxscore)
                file.write(boxscore)
                file.write("\n")
                reg_season_games.append(boxscore)
        file.close()
        gameids = []
        for key in playoff_game_list:
            day_games = playoff_game_list[key]
            for game in day_games:
                boxscore = game["boxscore"]
                if boxscore in gameids:
                    break
                else:
                    gameids.append(boxscore)
                playoff.write(boxscore)
                playoff.write("\n")
                playoff_games.append(boxscore)
        playoff.close()
           
    return reg_season_games, playoff_games
    


def get_stats_from_game(gameid, season, creating):
    file_gameid = gameid.split('/')[1]  #MLB gameids have the hometeam abbreviation twice with a /. causing problems to store them
    if not os.path.isfile(f"Data/{season}/Games/{file_gameid}.csv"):
        #we need to go fetch the data online, and we store it 
        game = Boxscore(gameid)
        game_df = game.dataframe
        if not game_df is None:
            losing_abbrv = game_df["losing_abbr"][0]
            winning_abbrv = game_df["winning_abbr"][0]
            

            if game_df["winner"][0] == "Home":
                home_abbrv = winning_abbrv
                away_abbrv = losing_abbrv
            else:
                home_abbrv = losing_abbrv
                away_abbrv = winning_abbrv
            
            
                
            player_df = pd.DataFrame()
            # we store individual player stats from the hometeam
            home_players = game.away_players
            for p in home_players:
                player_data = p.dataframe
                try:
                    player_data["details"] = (player_data["details"][0][0])
                except:
                     player_data["details"] = ""
                player_data["team"] = home_abbrv
                player_data["opponent"] = away_abbrv
                player_data["is_home"] = True
                player_df = pd.concat([player_df,player_data], axis=0)
            
            # then awayteam      
            away_players = game.home_players
            for p in away_players:
                player_data = p.dataframe
                try:
                    player_data["details"] = (player_data["details"][0][0])
                except:
                    player_data["details"] = ""
                player_data["team"] = away_abbrv
                player_data["opponent"] = home_abbrv
                player_data["is_home"] = False
                player_df = pd.concat([player_df,player_data], axis=0)
            
            player_df.to_csv(f"Data/{season}/Games/{file_gameid}_players.csv")
            game_df.to_csv(f"Data/{season}/Games/{file_gameid}.csv")
    try:
        player_df = pd.read_csv(f"Data/{season}/Games/{file_gameid}_players.csv")
        game_df = pd.read_csv(f"Data/{season}/Games/{file_gameid}.csv")
    except:
        return None, None
    return game_df, player_df



        
def update_games(season, ongoing):
    #we first want to fetch the ids of all the new games
    if not os.path.isdir(f"Data/{season}"):
       create_folders_for_season(season)
     
    if (not ongoing) and os.path.isfile(f"Data/{season}/Gameids.txt"):
        file = open(f"Data/{season}/Gameids.txt",'r')
        new_reg_season_games = file.readlines()
        file.close()
        if os.path.isfile(f"Data/{season}/Playoff_Gameids.txt"):
            file = open(f"Data/{season}/Playoff_Gameids.txt", 'r')
            new_playoff_games = file.readlines()
        else:
            new_playoff_games = []
    else:
        new_reg_season_games, new_playoff_games = update_gameid_file(season, ongoing)
    
    #for each of these games, we also need to create the vectors associated to each player
    # add the correct value and append it to the training_vectors file and at the end we 
    # recompute the optimal weights 
#    training_file = open(f"training_vectors.csv", 'a', newline='')
#    writer = csv.writer(training_file)
    for gameid in new_reg_season_games:
        gameid = gameid.strip()
        print(f"fetching data for game {gameid}")
        game_df, player_df = get_stats_from_game(gameid, season, True)
        if game_df is None or player_df is None:
            continue
        teams = [game_df.iloc[0]["losing_abbr"],game_df.iloc[0]["winning_abbr"]]
        players = {teams[0]:[], teams[1]:[] }
        
       
        for index, row in player_df.iterrows():
            playerid = row["Unnamed: 0"]
            players[row["team"]].append(playerid)
            if os.path.isfile(f"Data/{season}/Players/{playerid}.txt"):
                file = open(f"Data/{season}/Players/{playerid}.txt", "a")
                file.write(f"\n{gameid}")
            else:
                file = open(f"Data/{season}/Players/{playerid}.txt", "w")
                file.write(f"{gameid}")
            file.close()
        
#            player_name = row["name"]
#            if not math.isnan(row["pitches_thrown"]):
#                writer.writerow(["strikeouts",playerid, player_name, row["strikeouts"]])
#                writer.writerow(["home_runs_thrown", playerid, player_name, row["home_runs_thrown"]])
#            
#            if not math.isnan(row["at_bats"]):
#                writer.writerow(["runs_batted_in",playerid, player_name, row["runs_batted_in"]])
#                tb =  row["at_bats"]*row["slugging_percentage"]
#                if not math.isnan(tb):
#                    writer.writerow(["total_bases", playerid, player_name, tb])
#        
    for gameid in new_playoff_games:
        gameid = gameid.strip()
        print(f"fetching data for game {gameid}")
        game_df, player_df = get_stats_from_game(gameid, season, True)
        if game_df is None or player_df is None:
            continue
        teams = [game_df.iloc[0]["losing_abbr"],game_df.iloc[0]["winning_abbr"]]
        players = {teams[0]:[], teams[1]:[] }
        for index, row in player_df.iterrows():
            playerid = row["Unnamed: 0"]
            players[row["team"]].append(playerid)                
            if os.path.isfile(f"Data/{season}/Players/{playerid}_playoff.txt"):
                file = open(f"Data/{season}/Players/{playerid}_playoff.txt", "a")
                file.write(f"\n{gameid}")
            else:
                file = open(f"Data/{season}/Players/{playerid}_playoff.txt", "w")
                file.write(f"{gameid}")
            file.close()
#        player_name = row["name"]
#        if not math.isnan(row["pitches_thrown"]):
#            writer.writerow(["strikeouts",playerid, player_name, row["strikeouts"]])
#            if not math.isnan(tb):
#                    writer.writerow(["total_bases", playerid, player_name, tb])
#        
#        if not math.isnan(row["at_bats"]):
#            writer.writerow(["runs_batted_in",playerid, player_name, row["runs_batted_in"]])
#            writer.writerow(["total_bases", playerid, player_name, row["at_bats"]*row["slugging_percentage"]])
#    
#    training_file.close()

   
########### HELPER METHODS ###########
                   
def create_folders_for_season(season):
    #this method will be called when there is a new season.
    # ie when none of the folders exist already. We will create all the 
    # necessary files and folders here before continuing
    if not os.path.isdir("Data"):
        os.mkdir("Data")
    os.mkdir(f"Data/{season}")
    os.mkdir(f"Data/{season}/Games")
    os.mkdir(f"Data/{season}/Teams")
    os.mkdir(f"Data/{season}/Players")
    try:
        create_roster_files(season)
    except:
        print(f"error creating the roster files for season {season}, check if the season has already started, or if season is valid")

def convert_time_to_decimal(time):
    if ":" in str(time):
        minutes = time.split(":")[0]
        seconds = time.split(":")[1]
        time = float(minutes) + float(seconds)/60
    return time


# this method will go through the updated nba injury list and return the current 
# injured players per team. 
def fetch_injured_player_list(season):
    file = open("Data/TeamAbbrv.txt","r")
    team_abbrv = {}
    for line in file:
        abbrv = (line.strip()).split(":")[1]
        name = (line.strip()).split(":")[0]
        team_abbrv[name] = abbrv
        
    injuries_per_team = {}
    try:
        df = pd.read_excel(f"Data/{season}/Injuries.xlsx", sheet_name ="PowerQuery (B_Reference)")
        for index, row in df.iterrows():
            team = team_abbrv[row["Team"]]
            if team in injuries_per_team.keys():
                injuries_per_team[team].append(row["Player"])
            else:
                injuries_per_team[team] = [row["Player"]]
    except:
        print(f"Could not find player injuries file, in should be located at Data/{season}/Injuries.xlsx")
        print("Continuing without any injured players specified" )
        
    return injuries_per_team


def create_team_abbreviation_file():
    print("Creating team abbreviation file")
    teams = Teams()
    file = open("Data/TeamAbbrv.txt","w")
    count = 1
    for team in teams:
        file.write(f"{team.name}:{team.abbreviation}")
        if count != len(teams):
            file.write("\n")
        count += 1
    file.close()
    
    file = open("Data/TeamAbbrv_mlbgame.txt","w")
    count = 1
    teams = mlbgame.teams()
    for team in teams:
        name = team.club_full_name
        abbreviation = team.team_code.upper()
        file.write(f"{name}:{abbreviation}")
        if count != len(teams):
            file.write("\n")
        count += 1
    file.close()
    
    
    
    

def cleanup_game_files(season):
    for filename in os.listdir(f"Data/{season}/Players"):
        print(filename)
        file = open(f"Data/{season}/Players/{filename}",'r')
        lines = []
        for line in file:
            if line.strip() not in lines:
                lines.append(line.strip())
        file.close()
        file = open(f"Data/{season}/Players/{filename}",'w')
        count = 1
        for line in lines:
            if count == 1:
                file.write(line)
            else:
                file.write(f"\n{line}")
            count += 1

 
def get_value(vector, weights):
    #given a player vector and the set of optimal weights,by simply multiplying them we and adding the offset + rounding
    # we get the prediction value
    keys = ["l5","l10","location","opponent","season", "team"]
    prediction = 0
    for i in range(len(keys)):
        prediction += float(vector[i]) * float(weights[keys[i]])
    return prediction #+ float(weights["offset"]) 


      #game_df = game.dataframe

