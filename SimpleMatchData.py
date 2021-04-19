import json
import requests
from PostTemplate import simple_match_template, match_no_info
import ScheduleManager as schedule

# SimpleMatch only updates the Match Thread with a smaller subset of information
# Used when GE doesn't make detailed play by play report for a match
class SimpleMatch:

    def __init__(self, match_info):
        self.match_date = "-".join(match_info["data"].split("/")[::-1])
        self.match_time = match_info["hora"]
        self.home_team = match_info["mandante"]
        self.away_team = match_info["visitante"]
        self.competition = match_info["competicao"]
        self.score_home = "0"
        self.score_away = "0"
        self.is_finished = False
    
    def update_data(self, url=None):
        self.data = self.find_match_data()
        self.score_home = self.get_score("home")
        self.score_away = self.get_score("away")
        self.is_finished = self.data["winner"] != None

    def print_match(self, post_id):
        template = match_no_info if self.data == None else simple_match_template
        return template.format(
            TimeCasa=self.home_team,
            TimeFora=self.away_team,
            PlacarCasa=self.score_home,
            PlacarFora=self.score_away,
            Campeonato=self.competition,
            Data=self.format_date(self.match_date),
            Horario=self.format_time(self.match_time),
            RedditStream="https://reddit-stream.com/comments/" + post_id
        )
        
    def get_score(self, team):
        match = self.data
        if team == "mandante":
            team = "home"
        elif team == "visitante":
            team = "away"
        
        if match != None and "scoreboard" in match and match["scoreboard"] != None:
            if match["scoreboard"]["penalty"] == None:
                return match["scoreboard"][team]
            else:
                line = "{Score} ({Penalties})" if team == "home" else "({Penalties}) {Score}"
                return line.format(
                    Score = match["scoreboard"][team],
                    Penalties = match["scoreboard"]["penalty"][team]
                )
        else:
            return "0"
        
    def find_match_data(self):
        try:
            sched = schedule.get_day_matches(self.match_date)
        except requests.exceptions.RequestException as err:
            print("Request Error when trying to run Simple Match Data: " + str(err))
            return None
        
        championships = sched["data"]["championshipsAgenda"]
        for ch in championships:
            if ch["championship"]["name"] == self.competition:
                for match in ch["now"] + ch["past"] + ch["future"]:
                    info = match["match"]
                    if info["homeTeam"]["popularName"] == self.home_team and info["awayTeam"]["popularName"] == self.away_team:
                        return info
        return None
    
    def format_time(self, raw):
        parts = raw.split(":")
        return parts[0] + ":" + parts[1]
        
    def format_date(self, raw):
        parts = raw.split("-")
        day = str(int(parts[2]))
        month = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][int(parts[1])-1]
        
        return "{Dia} de {Mes} de {Ano}".format(Dia=day, Mes=month, Ano=parts[0])