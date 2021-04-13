#!/usr/bin/env python
import nba_py
from nba_py import team
from nba_py import player
from nba_py import game
from collections import OrderedDict
import ast
import sys
import json
import operator

def fetchLast10Games(teamId, gamesPlayed, isSimulation):
	value = team.TeamGameLogs(teamId, season='2017-18', season_type='Regular Season')
	gameList = value.info()
	i = 0
	totalHomeGames = 0
	totalAwayGames = 0
	homeWins = 0
	awayWins =0
	gameIDList = {}
	if(gamesPlayed == -1):
		gamesPlayed = len(gameList)
	i = 0	
	for game in gameList:
		outcome = game.get("WL")
		matchup = game.get("MATCHUP")
		start = (len(gameList) - gamesPlayed)
		
		if(i>=start and i<(start+10)):
			id = game.get("Game_ID")
			value = [outcome, matchup]
			gameIDList[id] = value;
		if(i>= start):
			if('@' in matchup):
				#ie this game was at home
				totalAwayGames = totalAwayGames + 1
				if(outcome == "W"):
					awayWins = awayWins + 1
			else:
				totalHomeGames = totalHomeGames + 1
				if(outcome == "W"):
					homeWins = homeWins + 1
		i = i + 1			
	toReturn = []
	toReturn.append(gameIDList)
	toReturn.append((float)(homeWins)/(float)(totalHomeGames))
	toReturn.append((float)(awayWins)/(float)(totalAwayGames))
	
	return toReturn

def getTeamL10Stats(gameIDList,teamId, notPlaying):
	#notPlaying is a list of names of players not playing, so that their performance is not taking in account for the team score
	
	playerStats = {}
	for gameID in gameIDList.keys():
		print(gameID)
 		value=game.Boxscore(gameID, season='2017-18', season_type='Regular Season', range_type='0', start_period='0', end_period='0', start_range='0', end_range='0')
		stats = value.player_stats()
		teamStats = value.team_stats()[1]
		teamAbbrevation = teamStats.get("TEAM_ABBREVIATION")
		otherInfo=gameIDList.get(gameID)
		for stat in stats:
 			if(stat.get("TEAM_ID") == (int)(teamId)):
				#then we know the player is in the team we are interested, so we get his stats
				name = "test"			
				if(stat.get("PLAYER_NAME") in notPlaying):
					print("this player is not playing")
				else:
					min = stat.get("MIN")
					playerId = stat.get("PLAYER_ID")
					#print(player.PlayerSummary(playerId).info()[0].get("POSITION"))
					#if player did not play this will be 'none'
					value = []
					toInput = []
					played = True	
					minutes = 0
			
					if(min is None):
						played = False
					else: 
					# we get the time played by the player
						separated = min.split(":")
						minutes = (float)(separated[0])
						secondes = (float)(separated[1])
						minutes = minutes + secondes/60
					
					# we calculate the score of the player for that game
					
						ranking = getScoreFromStats(stat)
						matchup = otherInfo[1]
						home = True
						if('@' in matchup):
							home = False
						if(otherInfo[0] == "W"):
						#ie the team won the game
							ranking = ranking + 5
						else:
						#if the team lost at home
							ranking = ranking - 5

						'''
					# I will test the PER rating system. 
					###
					
					if(played):
						factor = (2/3) - (0.5 * ast/(fgm + fglm)) /(2*(fgm+fglm)/ftm)
						VOP = pts/(fga + fgla) - oreb + tov + 0.44 * fta
						DRBP = dreb/reb		
					
						uPER = (1/minutes) * ( fglm + (2/3) * ast + (2-factor*(team_ast/team_fg)) * (fgm + fglm) + (ftm*0.5 *(1+(1-(1/3)*(team_ast/team_fg)))) - VOP*tov - VOP*DRBP*((fga +fgla) - (fgm+fglm)) - VOP * 0.44 * (0.44 + (0.56*DRBP)) * (fta-ftm) + VOP*(1-DRBP) * (reb - oreb)+VOP*DRBP*oreb + VOP*stl+VOP*DRBP*blk - pf *((log10(ftm)/log10(pf)) - 0.44*(log10(fta)/log10(pf)) * VOP))
						print("uper is : " + str(uPER))
											
					### 
					'''	
					if(stat.get("PLAYER_NAME") == "Marcus Morris"):
						print("MArcus morris")
						print(ranking)
				
					if(playerId in playerStats.keys()):
					#ie the player already has stats
						value = playerStats.get(playerId)
						if(played):
							newScore = (value[0]*value[1]+ ranking)/(value[0] + 1)
							toInput.append(value[0] + 1) # number of games played in the last 10
							toInput.append(newScore) # overall score
							toInput.append(value[2] + minutes)
					else:
						if(played):
							toInput.append(1)
							toInput.append(ranking)
							toInput.append(minutes)
				
					if(played):
						playerStats[playerId] = toInput
				# from these stats we want to create a certain rating for the player
				# and we update the player rating in the dictionary 		
				
						
	# player Stats contains is a dictionary with keys being the played ID of the players that played during the last 10 games
	# the time they played and how many points they scored			
	return playerStats	


def teamSeasonStats(teamID):
	return (team.TeamSeasons(teamID,league_id='00', season_type='Regular Season', per_mode='PerGame')).info()
	
def updateTeamStats():
	file = open("/Users/romainboudet/Documents/Betting/NBA/Teams/teams.txt", "r")
	dict = {}
	for line in file:
		print(line)
		values = line.split(":")
		teamName = values[0]
		print(teamName)
		teamID = values[1]
		file2 = open("/Users/romainboudet/Documents/Betting/NBA/Teams/" + teamName + ".txt", "w")
		stats = teamSeasonStats(teamID)
		toWrite = stats[len(stats)-1]
		for key in toWrite.keys():
			file2.write(key + ":" + str(toWrite[key]))
			file2.write("\n")
		file2.close()	
		
	file.close()



def updatePlayersL10Stats():
	file = open("/Users/romainboudet/Documents/Betting/NBA/Teams/teams.txt", "r")
	for line in file:
		values = line.split(":")
		teamName = values[0]
		teamID = values[1]
		l10Stats = {}
		roster = (team.TeamCommonRoster(teamID, season='2017-18')).roster()
		file2 = open("/Users/romainboudet/Documents/Betting/NBA/Players/" + teamName + ".txt", "w")
		for p in roster:
			playerId = p.get("PLAYER_ID")
			name = p.get("PLAYER")
			info = player.PlayerLastNGamesSplits(playerId, team_id=0, measure_type='Base', per_mode='PerGame', plus_minus='N', pace_adjust='N', rank='N', league_id='00', season='2016-17', season_type='Regular Season', po_round='0', outcome='', location='', month='0', season_segment='', date_from='', date_to='', opponent_team_id='0', vs_conference='', vs_division='', game_segment='', period='0', shot_clock_range='', last_n_games='0')
			l10 = info.last10()
			try:
				l10 = l10[0]
				l10Stats["MIN"] = l10.get("MIN")
				l10Stats["REB"] = l10.get("REB")
				l10Stats["AST"] = l10.get("AST")
				l10Stats["PTS"] = l10.get("PTS")
				l10Stats["BLK"] = l10.get("BLK")
				l10Stats["STL"] = l10.get("STL")
				file2.write(name + ":" + str(playerId) + ":" + str(l10Stats))
				file2.write("\n")
			except:
				print("Player " + name + " doesnt have any stats")
		file2.close()			
	file.close()		
		
		
			
def getTeamSeasonScore(teamID, isSimulation):
	#first we get the team name Abreviation
	if(isSimulation):
		teamName = teamID
	else:
		teamName = getTeamAbbrv(teamID.rstrip())
	print("team Name : " + teamName)
	if(isSimulation):
		file= open("/Users/romainboudet/Documents/Betting/NBA/Simulate/" +teamName + ".txt", "r")
	else:
		file = open("/Users/romainboudet/Documents/Betting/NBA/Teams/" +teamName + ".txt", "r")
	stats = {}
	
	for line in file:
		value = line.split(":")
		stats[value[0]] = value[1].rstrip()
		
	file.close()
	
	
	pts = stats.get("PTS")
	tov = stats.get("TOV")
	wins = stats.get("WINS")
	stl = stats.get("STL")
	reb = stats.get("REB")
	blk = stats.get("BLK")	
	stl = stats.get("STL")
	score = 0
	if(not isSimulation):
		conf_rank = stats.get("CONF_RANK")
		losses = stats.get("LOSSES")
		rankScore = (16 - (float)(conf_rank)) #15

	else:
		played = stats.get("gamesPlayed")
		rankScore = 15 * (float)(wins) / (float)(played)
	
	ptsScore = (float)(pts) * 25/115	 #25
	tovScore = (20-(float)(tov)) * 10 /7 #10
	stlScore = (float)(stl) *15/10		 #15
	rebScore = (float)(reb) * 20/57		 #20
	blkScore = (float)(blk) * 15/9		 #15
	score = rankScore + ptsScore + tovScore + stlScore + rebScore + blkScore
	return score
	

def getPlayerL10Stats(Team,playerID):
	teamName = getTeamAbbrv(Team)
	file = open("/Users/romainboudet/Documents/Betting/NBA/Players/" + teamName + ".txt", "r")
	for line in file:
		values = line.split(":")
		if((int)((values[1]).rstrip()) == (int)(playerID)):
			index = len(values[0])+ len(values[1]) + 2
			line = line[index:]
			stat = ast.literal_eval(line)
			min = stat.get("MIN")
			if((int)(min) == 0):
				return 0
			value = []
			toInput = []
			played = True
			score = getScoreFromStats(stat)
			toReturn = []
			toReturn.append(score)
			toReturn.append(min)
						
			return toReturn			
		


def getTeamScoreL10(teamID, notPlaying, gamesPlayed, isSimulation):
	teamInfo = fetchLast10Games(teamID,gamesPlayed, isSimulation)
	gameIDList = teamInfo[0]
	homeRatio = teamInfo[1]
	awayRatio = teamInfo[2]
	print("last 10 games list : " + str(len(gameIDList)))
	stats = getTeamL10Stats(gameIDList, teamID, notPlaying)
	total = 0
	playerCount = 0
	totalMinutes = 0
	for key in stats.keys():
		playerStats = stats.get(key)
		score = playerStats[1]
		minutesPlayed = (int)(playerStats[2])
		gamesPlayed = (int)(playerStats[0])
		#if the player hasnt played many games, but for the games he played he played a lot, 
		# then we use his season stats and weight it as if he had played the 10 last games. 
		# this is useful for example when a good player just came back
		if((gamesPlayed < 5) and (minutesPlayed/gamesPlayed) > 15):
			print("we are here")
			try:
				player = getPlayerL10Stats(teamID.rstrip(), key)
				totalMinutes = totalMinutes + 10*(int)(player[1])
				total = total + ((int)(player[1]) * (int)(player[0]) * 10)
			except:
				#there will be an error if the player has no stats2
				totalMinutes = totalMinutes + minutesPlayed
				total = total + (minutesPlayed * score)
		# we weight the player score depending on how many minutes they played
		else:
			totalMinutes = totalMinutes + minutesPlayed
			total = total + (minutesPlayed * score)
	total= total/totalMinutes 
	#divide by the total number of minutes allocated
	
	toReturn = [total, homeRatio, awayRatio]
	return toReturn


def getPVP(teamID, vsTeamName, notPlaying):
	roster = (team.TeamCommonRoster(teamID, season='2017-18')).roster()
	totalMinutes = 0
	totalScore = 0
	for p in roster:
		playerId = p.get("PLAYER_ID")
		name = p.get("PLAYER_NAME")
		if(not(name in notPlaying)):
			byOpponent = (player.PlayerOpponentSplits(playerId, team_id=0, measure_type='Base', per_mode='PerGame', plus_minus='N', pace_adjust='N', rank='N', league_id='00', season='2016-17', season_type='Regular Season', po_round='0', outcome='', location='', month='0', season_segment='', date_from='', date_to='', opponent_team_id='0', vs_conference='', vs_division='', game_segment='', period='0', shot_clock_range='', last_n_games='0')).by_opponent()
			for opp in byOpponent:
				if(opp.get("GROUP_VALUE") == vsTeamName):
					#then we want to get the stats
					score = getScoreFromStats(opp)
					minutes = opp.get("MIN")
					totalScore = totalScore + minutes * score
					totalMinutes = totalMinutes + minutes
					
			
	return (totalScore / totalMinutes)
			



def getScoreFromStats(stat):
	min = stat.get("MIN")
	if(min is None):
		return 0
	value = []
	toInput = []
	played = True
	reb = (float)(stat.get("REB"))
	assist = (float)(stat.get("AST"))
	pts = (float)(stat.get("PTS"))
	blk = (float)(stat.get("BLK"))
	stl = (float)(stat.get("STL"))
	to = (stat.get("TO"))
	if(to is None):
		to = 0.0
	else:
		to = (float)(stat.get("TO"))
		
	plus_minus = (float)(stat.get("PLUS_MINUS"))
	pf = (float)(stat.get("PF"))
		
	minutes = 0.0
	ptsNote = 0.0
	astNote = 0.0
	rebNote = 0.0
	blkNote = 0.0
	stlNote = 0.0
	toNote = 0.0
	pfNote = 0.0
	pmNote = 0.0
					
	# we calculate the score of the player for that game
	
	#We want to have a different score system if the player is more a defence player 
	# ie have less emphasis on pts and assists, but more on Drebounds plus minus, blks and so on
	
	
	#30 points, 20 assists, 20 rebounds, 7 blocks, 7 steals, 6 to, 10 pm
	
	
	# points 
	if(pts>25):
		ptsNote = 30
	else:
		ptsNote = pts *30/25
	
	# assists		
	if(assist>10):
		astNote = 20
	else:
		astNote = assist * 20/10
	
	#rebounds 					
	if(reb > 12):
		rebNote = 20
	else :
		rebNote = reb*20/12
	
	#blocks
	if(blk>5):
		blkNote = 7
	else:
		blkNote = blk*7/5
	#steals
	if(stl > 2):
		stlNote = 7
	else:
		stlNote = stl *7/2
	
	#turnovers
	if(to<1):
		toNote = 6
	else:
		toNote = 6 - to
	if(toNote < 0):
		toNote = 0
	
	#Plus/Minus - ie the difference in points when that player was on the court
	if(plus_minus> 10):
		pmNote = 10
	elif(plus_minus < -10):
		pmNote = -10
	else:
		pmNote = plus_minus
		
		
	#personal fouls 
	if(pf > 3):
		pfNote = 0
	else:
		pfNote = (4-pf)
						
	score = ptsNote+ astNote + rebNote + blkNote + stlNote + toNote	
	score = score * 98/72
	
	return score
	
#### methods to get team information #####


def getIDForTeam(teamName):
	file = open("/Users/romainboudet/Documents/Betting/NBA/Teams/teams.txt", "r")
	for line in file:
		values = line.split(":")
		if(values[0] == str(teamName)):
			return values[1]
	file.close()
	return None

def getTeamAbbrv(teamID):
	file = open("/Users/romainboudet/Documents/Betting/NBA/Teams/teams.txt", "r")
	teamName = ""
	for line in file:
		value = line.split(":")
		if((value[1].rstrip()) == teamID):
			teamName = value[0]
			break
	return teamName
	file.close()

def getTeamNameForID(TeamID):
	file = open("/Users/romainboudet/Documents/Betting/NBA/TeamID.txt", "r")
	for line in file:
		value = line.split(":")
		if((int)(value[1].rstrip()) == (int)(TeamID)):
			return value[0]
	file.close()
	
	return None


def rankAllTeams():
	file= open("/Users/romainboudet/Documents/Betting/NBA/TeamID.txt", "r")
	dict = {}
	for line in file:
		print(line)
		value = line.split(":")
		id = value[1]
		score1 = getTeamScoreL10(id, [], -1, False)[0]
		print(score1)
		score2 = getTeamSeasonScore(id, False)
		print(score2)
		score = 0.7*score1 + 0.3*score2
		dict[value[0]]= score
		sortedDict = sorted(dict.items(), key=operator.itemgetter(1))
		print(sortedDict)
	file.close()
	print(sortedDict)
	file = open("/Users/romainboudet/Documents/Betting/NBA/RankedTeams.txt", "w")
	for key in sortedDict.keys():
		file.write(key + " : " + sortedDict[key] + "\n")
	file.close()	



def getAllGameIds():

	list = []
	for m in range(10,13):
		for d in range(1,32):
			print(str(m) + " " + str(d))
			value=((m==10) and (d<16))
			if(not value):
				try:
					test = nba_py.Scoreboard(month=m, day=d, year=2017, league_id='00', offset=0)
					games = test.available()
					print(test.game_header())
					for game in games:
						print(game.get("GAME_ID"))
						list.append(game.get("GAME_ID"))
				except:
					print("error")
	for d in range(1,14):
		test = nba_py.Scoreboard(month=1, day=d, year=2018, league_id='00', offset=0)
		games = test.available()
		for game in games:
			list.append(game.get("GAME_ID"))
	file = open("/Users/romainboudet/Documents/Betting/NBA/Games.txt", "w")
	print(list)
	for game in list:
		file.write(game)
		file.write('\n')
	
