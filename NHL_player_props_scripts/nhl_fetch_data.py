from sportsreference.nhl.teams import Teams
from sportsreference.nhl.boxscore import Boxscore
from sportsreference.nhl.roster import Roster
from sportsreference.nhl.schedule import Schedule
from datetime import datetime, timedelta
import os
import math
import pandas as pd
import requests
import xml.etree.ElementTree as et 
import unidecode
from nhl_optimized_values import compute_opt_weights
#import win32com.client




########## PLAYER METHODS ############
'''
¬	This method fetches and individual players’ stats for a given game. If the player did not play in that game it returns an empty dataframe
•	Season:  season in which the game is
•	Gameid: Gameid of the game we are interested in
•	Playerid: The unique player id

'''   
def fetch_playerstat_for_player(season, gameid, playerid):
    # this method returns the stats of a given player for a given game
    # if the player did not play this game, it returns {}
    
    df = pd.read_csv(f"Data/{season}/Games/{gameid}_players.csv")
    teams = df.team.unique() #teams that were playing in the game. (in first position home team)
    to_return = pd.DataFrame()
    total_minutes = 0
    for i, row in df.iterrows():
        total_minutes += convert_time_to_decimal(row["time_on_ice"])
        if row["Unnamed: 0"] == playerid:  #Unamed : 0 is the column name for player ids
            row["time_on_ice"] = convert_time_to_decimal(row["time_on_ice"])
            if math.isnan(row["time_on_ice"]):
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
            
            to_return = row
    if not to_return.empty:
        to_return["total_game_minutes"] = total_minutes/12
    return to_return



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

'''
This method first checks if the data for the given game has already been loaded, if it has it returns 2 dataframes, one containing the overall game data, 
and another one containing individual player data. 
•	season:  season in which the game is
•	Gameid: Gameid of the game we are interested in

'''

def get_stats_from_game(gameid, season):
    if not os.path.isfile(f"Data/{season}/Games/{gameid}.csv"):
        #we need to go fetch the data online, and we store it 
        count = 0
        while True:
            try:
                game = Boxscore(gameid)
                break
            except:
                count += 1
                if count > 1000:
                    return pd.DataFrame(), pd.DataFrame()
        try:
            game_df = game.dataframe
        except:
            return pd.DataFrame(), pd.DataFrame()
        home_abbrv = gameid[len(gameid)-3:]
        if game_df["winning_abbr"][0] == home_abbrv:
            away_abbrv = game_df["losing_abbr"][0]
        else:
            away_abbrv = game_df["winning_abbr"][0]

        player_df = pd.DataFrame()
        # we store individual player stats from the hometeam
        home_players = game.home_players
        for player in home_players:
            player_data = player.dataframe
            player_data["team"] = home_abbrv
            player_df = pd.concat([player_df,player_data], axis=0)
        
        # then awayteam      
        away_players = game.away_players
        for player in away_players:
            player_data = player.dataframe
            player_data["team"] = away_abbrv
            player_df = pd.concat([player_df,player_data], axis=0)
        
        player_df.to_csv(f"Data/{season}/Games/{gameid}_players.csv")
        game_df.to_csv(f"Data/{season}/Games/{gameid}.csv")

    player_df = pd.read_csv(f"Data/{season}/Games/{gameid}_players.csv")
    game_df = pd.read_csv(f"Data/{season}/Games/{gameid}.csv")
    return game_df, player_df

'''
¬	This method is called when it is the first time we are loading data for a given game. It first calls 
the method above (get_stats_for_game). It then goes through every player that played for that game and updates the 
individual player’s game lists. We also want to know if this game is a playoff game or a regular season game to update the correct game lists
•	Season:  season in which the game is
•	Gameid: Gameid of the game we are interested in
•	isplayoff: This is a True/False value representing if the game is a playoff game or not


'''

def fetch_data_for_game(season, gameid):
    
    ## we want to add the data for that game if it is not already present in the files.
  
    print(f"fetching data for game {gameid}")
    game_df, player_df = get_stats_from_game(gameid, season)
    home_goals = game_df["home_goals"].item()
    away_goals = game_df["away_goals"].item()
    winning_abbr = game_df["winning_abbr"].item()
    losing_abbr = game_df["losing_abbr"].item()
    home_sog =  game_df["home_shots_on_goal"].item()
    away_sog =  game_df["away_shots_on_goal"].item()

    if os.path.isfile(f"Data/{season}/defense_file.csv"):
        df =  pd.read_csv(f"Data/{season}/defense_file.csv")
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
                
        df.to_csv(f"Data/{season}/defense_file.csv")

    else:
        if int(home_goals) > int(away_goals):
            data = {"games_played":[1,1], "goals_allowed":[away_goals, home_goals], "shots_on_goal_allowed":[away_sog, home_sog]}
        else:
            data = {"games_played":[1,1], "goals_allowed":[home_goals, away_goals], "shots_on_goal_allowed":[home_sog, away_sog]}
        df = pd.DataFrame(data, index=[winning_abbr, losing_abbr])
        df.index.name = "team_names"
        df.to_csv(f"Data/{season}/defense_file.csv", index=True)

    for index, row in player_df.iterrows():
        playerid = row["Unnamed: 0"]
        ##want to check if the player actually played that game
        try:
            time_on_ice = convert_time_to_decimal(row["time_on_ice"])
            if time_on_ice != 0:
                if os.path.isfile(f"Data/{season}/Players/{playerid}.txt"):
                    file = open(f"Data/{season}/Players/{playerid}.txt", "a")
                    file.write(f"\n{gameid}")
                else:
                    file = open(f"Data/{season}/Players/{playerid}.txt", "w")
                    file.write(f"{gameid}")
                file.close()
        except:
            pass


'''
¬	This method is used to go through all the games that are happening during the season provided. It loads each team’s schedule, 
and goes through every game. If the data for each game hasn’t been loaded, it calls the method above. In particular this is used for 
the initialization process. As we are going through each game, we can also give a ‘date’ parameter, and this method will return all the games 
happening that day in a dataframe
•	Season:  season in which the game is
•	date: The date we want to get games from, in datetime format

'''
def fetch_data_for_all_games(season, date):
    teams = Teams(season)
    games_today = pd.DataFrame()
    hometeams  = []
    awayteams = []
    gameids = []
    games_to_compute = pd.DataFrame(columns=["gameid", "date"])
    for team in teams:
        team_schedule = Schedule(team.abbreviation, season)
        df = team_schedule.dataframe
        df.to_csv(f"Data/{season}/Teams/{team.abbreviation}_schedule.csv")
        playoff_games = []
        reg_games = []
        for index, row in df.iterrows(): 
            gameid = row["boxscore_index"]
            datestring = str(row["datetime"])
            values = datestring.split(" ")[0].split("-")
            game_date=datetime(int(values[0]), int(values[1]), int(values[2]))
            if(game_date.date() == date.date()):
                opponent = row["opponent_abbr"]
                location = row["location"]
                month = date.strftime('%m')
                day = date.strftime('%d')
                year = date.strftime('%Y')
                gameidstring = str(year) + str(month) + str(day) + '0'
                if location == "Home":
                    gameidstring +=  str(team.abbreviation)
                    if gameidstring not in gameids:
                        hometeams.append(team.abbreviation)
                        awayteams.append(opponent)
                        gameids.append(gameidstring)
                else:
                    gameidstring += opponent
                    if gameidstring not in gameids:
                        awayteams.append(team.abbreviation)
                        hometeams.append(opponent)
                        gameids.append(gameidstring)
                
            if game_date < (datetime.today() - timedelta(days=1)) and '<td' not in gameid:
                games_to_compute =  games_to_compute.append({"gameid":gameid, "date":game_date.date()}, ignore_index=True)          
            else:
                continue

    ## then we want to sort the dataframe by date so we consider the games in the correct order. 
    games_to_compute= games_to_compute.sort_values(by='date')
    for index, row in games_to_compute.iterrows():
        gameid = row["gameid"]
        if not os.path.isfile(f"Data/{season}/Games/{gameid}.csv"):
            fetch_data_for_game(season, gameid)
    
    games_today["gameid"] = gameids
    games_today["hometeam"] = hometeams
    games_today["awayteam"] = awayteams

    
    return games_today          
   
########### HELPER METHODS ###########
                   
def create_folders_for_season(season):
    #this method will be called when there is a new season.
    # ie when none of the folders exist already. We will create all the 
    # necessary files and folders here before continuing
    try:
        os.mkdir("Data")
    except:
        pass
    try:
        os.mkdir(f"Data/{season}")
    except:
        pass
    try:
        os.mkdir(f"Data/{season}/Games")
    except:
        pass
    try:
        os.mkdir(f"Data/{season}/Teams")
    except:
        pass
    try:
        os.mkdir(f"Data/{season}/Players")
    except:
        pass
    
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
def fetch_injured_player_list():
    skip_next = False
    injured_dict ={} 
    gtd_dict = {} 
    df = pd.read_excel("NHLInjuriesFile.xlsx")
    for index, row in df.iterrows():
        if skip_next:
            skip_next = False
            continue
        player_name = row["Player Name"]
        if player_name != "Player" and not pd.isna(player_name) and player_name != "No injuries to report.":
            skip_next = True
            player_team = row["Team"]
            status = row["Notes"]
            if player_team not in injured_dict.keys(): 
                injured_dict[player_team] = [] 
                gtd_dict[player_team] = [] 
            if 'Ques' in status or 'ques' in status: 
                gtd_dict[player_team].append(player_name) 
            elif ("prob" not in status) and ("Prob" not in status): 
                injured_dict[player_team].append(player_name) 
            
#    cwd = os.getcwd() 
#    path = cwd.replace("\\","\\\\") 
#    xlapp = win32com.client.Dispatch("Excel.Application") 
#    wb = xlapp.Workbooks.Open(f'{path}\\NHLInjuriesFile.xlsx') 
#    wb.RefreshAll() 
#    xlapp.CalculateUntilAsyncQueriesDone() 
#    ws = wb.Worksheets("Sheet1") 
#    xlUp = -4162 
#    lastrow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row + 1 
#    skipNext = False 
#    team_counter = 0
#    team_list = []
#    current_team = ""
#    for i in range(2, lastrow): 
#        if skipNext: 
#            skipNext = False
#            continue 
#        team = ws.Cells(i,1).Value 
#        if team != current_team:
#            team_list.append(team)
#            current_team = team
#            
#        player = ws.Cells(i,2).Value 
#        status = ws.Cells(i,4).Value 
#        if team is None: 
#            break 
#        if(player == "Player"):
#            team_counter += 1
#            continue
#        if player is None or status is None: 
#            continue 
#        else:
#            skipNext = True 
#        
#        player_team = team_list[team_counter]
#        if player_team not in injured_dict.keys(): 
#            injured_dict[player_team] = [] 
#            gtd_dict[player_team] = [] 
#
#        if 'Ques' in status or 'ques' in status: 
#            gtd_dict[player_team].append(player) 
#        elif ("prob" not in status) and ("Prob" not in status): 
#            injured_dict[player_team].append(player) 
#
#    wb.Save() 
#    wb.Close(False) 
    
    return injured_dict, gtd_dict



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



'''

¬	This is the method that is run from the nba_init_script.py file. Depending on the date at which t
his function is run, we know which was the last nba season. This will fetch data for the current_season
 and the one just before. For each of those, it starts by calling the creat_folders function to set up the 
 file system. And then it loads all the games from that season.Finally it creates files for each current players
 which will be used to compute  the individual optimized weights. 

'''

def initial_setup():
    ## this is the intial setup that needs to run when the model is first ran
    ## we want to get the data from the previous season. 
    ## and load the data to compute the optimized weights for the players. 
    year = datetime.today().year
    ## we want to get the current season. We first try to see if we are the very beginning of a season
    try:
        Teams(str(year+1))
        seasons = [year, year+1]
        current_season = year+1
        
    except:
        #then we are not
        seasons = [year-1 , year]
        current_season = year

    print("Initial setup of the NBA props model")
    print(f"This will take some time, fetching data for seasons {seasons[0]} and {seasons[1]}")
    print("And computing data to include for optimized weights computation")
    # we wat to check if the season is ongoing: 
    for season in seasons:
        create_folders_for_season(season)
        fetch_data_for_all_games(season, datetime.today())
    
#    print("Computing data for optimized weight computations")
#    files = os.listdir(f"Data/{current_season}/Players")
#    cutoff = len(files)/10
#    counter = 1
#    for i in range(len(files)):
#        if i > counter*cutoff:
#            print(f"completed {counter}0 %")
#            counter += 1
#        file = files[i]
#        playerid= file[:-4]
#        compute_opt_weights(playerid,seasons, None)
       
    