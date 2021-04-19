import json
import requests
from urllib.parse import urlencode

def find_stats(day, home_team, away_team):
    match_id = find_match_id(day, home_team, away_team)
    if match_id == None:
        return
    
    # response = requests.get("https://webws.365scores.com/web/game/?langId=31&gameId=" + str(match_id))
    response = requests.get("https://webws.365scores.com/web/game/?gameId=" + str(match_id))
    data = response.json()
    
    home_stats_list = data["game"]["homeCompetitor"]["statistics"]
    away_stats_list = data["game"]["awayCompetitor"]["statistics"]
    home_stats = {}
    away_stats = {}
    
    for s in home_stats_list:
        home_stats[s["name"]] = str(s["value"])
    for s in away_stats_list:
        away_stats[s["name"]] = str(s["value"])
    
    stats_str = home_team + " | Estatística | " + away_team + "\n :---: | :---: | :---: \n"
    for key, value in home_stats.items():
        stats_str += value + " | " + translate_stat(key) + " | " + away_stats[key] + "\n"
        
    return stats_str
    
def translate_stat(str):
    translations = {
        "Possession": "Posse de Bola",
        "Total Shots": "Finalizações",
        "Shots On Target": "Finalizações Certas",
        "Shots Off Target": "Finalizações Erradas",
        "Hit Woodwork": "Finalizações na Trave",
        "Big chances": "Chances Claras",
        "Corners": "Escanteios",
        "Crosses": "Cruzamentos",
        "Offsides": "Impedimentos",
        "Free Kicks": "Tiro Livre",
        "Total passes": "Passes",
        "Passes Completed": "Passes Certos",
        "Attacks": "Ataques",
        "Fouls": "Faltas",
        "Goalkeeper Saves": "Defesas de Goleiro",
        "Tackles": "Desarmes",
        "Shots Blocked": "Chutes Bloqueados",
        "Throw-ins": "Arremessos Laterais",
        "Goal Kicks": "Tiro de Meta",
        "Tackles Won": "Desarmes Certos",
        "Yellow Cards": "Cartões Amarelos",
        "Red Cards": "Cartões Vermelhos"
    }
    if str in translations:
        return translations[str]
    return str

def get_all_matches(day):
    base_url = "https://webws.365scores.com/web/games/allscores/?"
    params = {
        'appTypeId': 5,
        'langId': 1,
        'startDate': day,
        'endDate': day,
        'onlyMajorGames': 'false',
        'sports': 1,
        'timezoneName': 'Etc/GMT+3',
        'userCountryId': 21
    }
    
    response = requests.get(base_url + urlencode(params))
    return response.json()

def find_match_id(day, home_team, away_team):
    data = get_all_matches(day)
    games = data["games"]
    
    for g in games:
        if g["homeCompetitor"]["name"] == home_team and g["awayCompetitor"]["name"] == away_team:
            return g["id"]
    return None
    
    