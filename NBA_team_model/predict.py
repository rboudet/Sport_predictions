from betting import *

argumentList = sys.argv
if(len(argumentList) == 1):
	## then we want to do an update of tean stats
	print("updtating all team stats")
	##updateTeamStats()
	print("updtating player last 10 games stats")
	#updatePlayersL10Stats()
	print("done")
	rankAllTeams()



if(len(argumentList) == 2):
	#we just want the score of this team
	teamName = argumentList[1]
	teamID = getIDForTeam(teamName)
	roster = (team.TeamCommonRoster(teamID, season='2017-18')).roster()

	players = input("input comma separated list of players not playing (full Names) for " + teamName + " :")
	list = players.split(",")	
	print("getting score for team  " + teamName)
	score1 = getTeamSeasonScore(teamID)
	score2 = getTeamScoreL10(teamID, list)
	print(score1)
	print(score2[0])
	score = 0.3*score1 + 0.7*(float)(score2[0])
	#score = score * (float)(score2[1])
	print("score is : " + str(score))
	
	
	
if(len(argumentList) == 3):
	## then we want to see which team is more likely to win, and with which certitude
	homeTeam = argumentList[1]
	awayTeam = argumentList[2]
	
	players = input("input comma separated list of players not playing (full Names) for " + homeTeam + " :")
	home = players.split(",")
	players = input("input comma separated list of players not playing (full Names) for " + awayTeam + " :")
	away = players.split(",")
	
	print("checking who will win between " +  homeTeam + " and " + awayTeam)
	homeTeamID = getIDForTeam(homeTeam)
	awayTeamID = getIDForTeam(awayTeam)
	homeScore = getTeamScoreL10(homeTeamID,home, -1, False)
	awayScore = getTeamScoreL10(awayTeamID,away, -1, False)	
	
	
	homeTeamName = getTeamNameForID(homeTeamID)
	awayTeamName = getTeamNameForID(awayTeamID)
	
	homeSeasonScore = getTeamSeasonScore(homeTeamID,0)
	awaySeasonScore = getTeamSeasonScore(awayTeamID,0)
	

	
	
	##homePVP = getPVP(homeTeamID, awayTeamName, home)
	##awayPVP = getPVP(awayTeamID, homeTeamName, away)
	##print("pvp score : ")
	##print(homePVP)
	##print(awayPVP)
	
	
	finalHomeScore = 0.7*(float)(homeScore[0]) + 0.3*homeSeasonScore #+ homePVP *0.03
	finalAwayScore = 0.7*(float)(awayScore[0])+ 0.3*awaySeasonScore #+ awayPVP * 0.03
	
	#now we want to modify the home and away score, depending on how well these teams perform at home and away
	print("finalHomeScore  : " + str(finalHomeScore))
	print("home ratio : " +	str(homeScore[1]))
	finalHomeScore = finalHomeScore + (10 * (float)(homeScore[1]))
	print("final score : " + str(finalHomeScore))
	
	print("finalAwayScore  : " + str(finalAwayScore))
	print("away ratio : " +	str(awayScore[2]))
	finalAwayScore = finalAwayScore + (10 * (float)(awayScore[2]))
	print("finalAway : " + str(finalAwayScore))
	if(finalHomeScore > finalAwayScore):
		print(homeTeam + "is more likely to win against " + awayTeam)
	else:
		print(awayTeam + "is more likely to win against " + homeTeam)
	difference = abs(finalHomeScore - finalAwayScore)
	certitude = 0
	if(difference > 20):
		certitude = 100
	else :
		certitude = difference * 100 /20
	print("with certitude : " + str(certitude))