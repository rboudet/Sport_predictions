import nba_py
from nba_py import team
from nba_py import player
from nba_py import game
from betting import getTeamScoreL10,getIDForTeam,getTeamSeasonScore

# this file will be used for testing the mode
# it will simulate all the games with IDs in the Games.txt file
# it will not simulate a game if both teams have not played more than 10 games
# it then compares the output of the model to the actual result

def simulateSeason():
	totalGames = 0
	totalCorrect = 0
	Ids = open("/Users/romainboudet/Documents/Betting/NBA/Games.txt").readlines()
	i = 0
	while i<len(Ids):
		gameID = Ids[i].rstrip()
		print(gameID)
		result=game.Boxscore(gameID, season='2017-18', season_type='Regular Season', range_type='0', start_period='0', end_period='0', start_range='0', end_range='0').team_stats()
		winner = ""
		homeScore = 0
		awayScore = 0
		homeTeam =""
		awayTeam = ""
		k = 0
		for team in result:
			print(team)	
			l10Score = 0	
			teamName = team.get("TEAM_ABBREVIATION")
			if(k == 0):
				homeTeam = teamName
			else:
				awayTeam = teamName
			
			
			if((int)(team.get("PLUS_MINUS")) > 0):
				l10Score = updateTestingSeasonStats(team, True)
				winner = teamName
				if(l10Score[0] != -1):
					if(k==0):
						l10Score[0] = l10Score[0] + 10*(float)(l10Score[1])
					else:
						l10Score[0] = l10Score[0] + 10*(float)(l10Score[2])
					
			else:
				l10Score = updateTestingSeasonStats(team, False)
				if(l10Score[0] != -1):
					if(k==0):
						l10Score[0] = l10Score[0] + 10*(float)(l10Score[1])
					else:
						l10Score[0] = l10Score[0] + 10*(float)(l10Score[2])
			if(l10Score[0] != -1):
				score = getTeamSeasonScore(teamName, True)
				finalScore = 0.7*l10Score[0] + 0.3*score
				if(k==0):
					homeScore =  finalScore
				else:
					awayScore = finalScore
			k = k+1
		
		modelWinner = ""
		if((homeScore != 0) and (awayScore != 0)):
			if(homeScore > awayScore):
				modelWinner = homeTeam
			else:
				modelWinner = awayTeam
			totalGames = totalGames + 1
			
			print("For the game " + awayTeam + " @ " + homeTeam)
			print("model precicted " + modelWinner + " to win")
			print(winner + " won this game")
		
			print("home score : " + str(homeScore))
			print("away score : " +str(awayScore))
			if(winner == modelWinner):
				totalCorrect = totalCorrect + 1
			print("total game tested : " + str(totalGames))
			print("Correctly guessed " + str(totalCorrect))
			
		i = i +1




def updateTestingSeasonStats(stats, wonGame):
	# I need to add a return statement, if a team has played more then 10 games, we return the players l10 games
	

	keySet=["PTS","REB", "AST", "TOV", "BLK", "STL", "FGA", "FGM", "FG3A", "FG3M", "OREB", "FTA", "FTM", "DREB", "gamesPlayed", "WINS"]
	# first we check if we already have stats
	teamName = stats.get("TEAM_ABBREVIATION")
	temp = {}
	newStats = {}
	stats["TOV"] = stats.get("TO")
	try:
		file = open("/Users/romainboudet/Documents/Betting/NBA/Simulate/" + teamName + ".txt","r")
		for line in file: 
			line = line.rstrip()
			values = line.split(":")
			temp[values[0]] = values[1]
		file.close()
		
	except:
		print(teamName)
		print("file did not exists")
		
	if bool(temp):
		# ie if it not empty. then we add the new stats
		nbGames = temp.get("gamesPlayed")
		for key in temp.keys():
			if(not((key == "gamesPlayed") or (key == "WINS"))):
				value = (float)(nbGames)*(float)(temp.get(key)) + (float)(stats.get(key))
				newStats[key] = (float)(value) /(float)((int)(nbGames) + 1)
		newStats["gamesPlayed"] = (int)(nbGames) + 1
		if(wonGame):
			newStats["WINS"] = (int)(temp.get("WINS")) + 1
		else:
			newStats["WINS"] = (int)(temp.get("WINS"))
	else:
		#this is the first game we are logging
		newStats = stats
		newStats["gamesPlayed"] = 1
		if wonGame:
			newStats["WINS"]= 1
		else:
			newStats["WINS"]= 0 
	print(newStats["gamesPlayed"])
	# and then we write to the file the stats. 
	file = open("/Users/romainboudet/Documents/Betting/NBA/Simulate/" + teamName + ".txt","w")
	for key in newStats.keys():
		if(key in keySet):
			file.write(key + ":" + str(newStats.get(key)))
			file.write('\n')
	gamesPlayed = (int)(newStats.get("gamesPlayed"))
	l10Score = [-1, -1, -1]
	if(gamesPlayed>9):
		print("we will try and predict this game")
		teamID = getIDForTeam(teamName)
		l10Score = getTeamScoreL10(teamID,[], gamesPlayed, True)
		
	return l10Score
	
	
	
simulateSeason()