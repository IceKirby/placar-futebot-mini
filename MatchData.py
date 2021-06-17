import json
import requests
import random
import math
from datetime import datetime, timedelta
from PostTemplate import match_template, match_icons

class Match:
    base_url = "https://globoesporte.globo.com/globo/raw/"
    
    def __init__(self, settings={}, url=None):
        self.url = url
        self.is_finished = False
        self.detailed = self.get_setting(settings, "detailed_log", False) == "True"
     
    # Update Match Data based on content from GE Match URL
    def update_data(self, url=None):
        if url == None:
            url = self.url
        self.url = url
        
        target_url = self.url.replace("ge.globo.com/", "ge.globo.com/globo/raw/");
        
        response = requests.get(target_url, timeout=10)
        response.raise_for_status()
        self.data = response.json()
        
        try:
            self.home_team = self.get_data("resource.transmissao.jogo.mandante", {})
            self.away_team = self.get_data("resource.transmissao.jogo.visitante", {})
            self.plays = self.get_data("resource.lances", [])
            
            self.fixed_plays = self.mark_period_transitions(self.fix_plays_order(self.plays[::-1]))
            self.subbed_players = self.find_substitutions(self.fixed_plays)
            self.goalscorers = self.find_goalscorers()
            
            period = self.get_data("resource.transmissao.periodo", "PRE_JOGO")
            self.is_finished = period == "POS_JOGO" or period == "FIM_DE_JOGO"
        except Exception as e:
            print(e)
            return
    
    # Get content for thread based on PostTemplate
    def print_match(self, post_id):
        play_list = self.filter_plays(self.fixed_plays)
        play_text = self.organize_plays(play_list)
        
        return match_template.format(
            Campeonato = self.get_data("resource.transmissao.jogo.edicao.nome", "N/D"),
            CampeonatoFase = self.get_data("resource.transmissao.jogo.fase.nome", "N/D"),
            CampeonatoRodada = self.get_data("resource.transmissao.jogo.campeonato.nome", "N/D"),
            Estadio = self.get_data("resource.transmissao.jogo.estadio.nome", "N/D"),
            TimeCasa = self.get_data("resource.transmissao.jogo.mandante.nome", "N/D"),
            TimeFora = self.get_data("resource.transmissao.jogo.visitante.nome", "N/D"),
            TimeCasaTitulares = self.get_team_list(self.home_team, "titulares"),
            TimeCasaReservas = self.get_team_list(self.home_team, "reservas"),
            TimeCasaTreinador = self.get_data("resource.transmissao.jogo.mandante.tecnico.nome_popular", "N/D"),
            TimeForaTitulares = self.get_team_list(self.away_team, "titulares"),
            TimeForaReservas = self.get_team_list(self.away_team, "reservas"),
            TimeForaTreinador = self.get_data("resource.transmissao.jogo.visitante.tecnico.nome_popular", "N/D"),
            TimeCasaGols = self.get_goals_list("home"),
            TimeForaGols = self.get_goals_list("away"),
            TimeCasaEsquema = self.get_formation(self.home_team),
            TimeForaEsquema = self.get_formation(self.away_team),
            Arbitragem = self.get_referees(),
            PlacarFinal = self.get_final_score(),
            PlacarCasa = self.get_score("mandante"),
            PlacarFora = self.get_score("visitante"),
            Data = self.format_date(self.get_data("resource.transmissao.jogo.dataRealizacao", "N/D")),
            Horario = self.format_time(self.get_data("resource.transmissao.jogo.horaRealizacao", "N/D")),
            Lances = play_text,
            MomentoPartida = self.get_match_moment(),
            RedditStream = "https://reddit-stream.com/comments/" + post_id,
            LinkGE = self.get_data("resource.url", "N/D")
        )

    # Finds substitutions (because GE data for this is unreliable)
    def find_substitutions(self, play_list):
        filtered = list(filter(lambda x: x["tipoLance"] == "SUBSTITUICAO", play_list))
        subs = {}
        for s in filtered:
            if "jogador" in s and s["jogador"] != None and "jogadorReserva" in s and s["jogadorReserva"] != None:
                subs[s["jogador"]] = {
                    "sub_in": s["jogadorReserva"],
                    "sub_out": s["jogador"]
                }
        return subs
    
    def get_match_moment(self):
        status = self.get_data("resource.transmissao.periodo", "PRE_JOGO")
        
        if status == "PRE_JOGO":
            return "Pré-Jogo"
        elif status == "POS_JOGO" or status == "FIM_DE_JOGO":
            return "Encerrado"
        elif status == "INTERVALO":
            return "Intervalo"
        elif status == "PRIMEIRO_TEMPO":
            return self.guess_time("PRIMEIRO_TEMPO") + "1T"
        elif status == "SEGUNDO_TEMPO":
            return self.guess_time("SEGUNDO_TEMPO") + "2T"
        elif status == "PRIMEIRO_TEMPO_PRORROGACAO":
            return self.guess_time("PRIMEIRO_TEMPO_PRORROGACAO") + "1P"
        elif status == "SEGUNDO_TEMPO_PRORROGACAO":
            return self.guess_time("SEGUNDO_TEMPO_PRORROGACAO") + "2P"
        elif status == "AGUARDANDO_PRORROGACAO":
            return "Prorrogação"
        elif status == "PENALIDADES" or status == "AGUARDANDO_PENALIDADES":
            return "Pênaltis"
        
    # Tries to guess current match time using some plays from the ongoing half as sample
    # It looks for the difference between the current time and the time the play was created
    # and adds the difference to the play's moment, then returns the lowest value from the sampled plays
    def guess_time(self, period):
        # Filter plays by only getting those from the current half
        plays = list(filter(lambda x: x["periodo"] == period, self.fixed_plays))
        
        # Gets the first play, last and some other random one
        sample = []
        if len(plays) > 0:
            sample.append(plays[0])
        if len(plays) > 2:
            sample.append(random.choice(plays[1:-1]))
        if len(plays) > 1:
            sample.append(plays[-1])
        
        now = datetime.utcnow()
        minutes = 0
        seconds = 0
        diff = []
        
        # For each sample play, check how long ago it was added to the system, then
        # add that difference to the moment it happend in that half
        for s in sample:
            # Check how long ago the play was input into the system
            delta = now - datetime.strptime(s["created"], "%Y-%m-%dT%H:%M:%S.%fZ")
            
            # Add that difference to the moment the play was said to have happened
            raw = s["momento"].split(":")
            seconds = int(raw[1]) + (delta.seconds % 60)
            minutes = int(raw[0]) + math.floor(delta.seconds / 60)
            if seconds >= 60:
                seconds = seconds % 60
                minutes = minutes + 1
                
            # Save adjusted moment for later comparison
            diff.append({ "min":minutes, "sec":seconds })
        if len(diff) == 0:
            return "0/"
            
        # Return the lowest value found in the sampled plays
        diff = sorted(diff, key=lambda x: x["min"]*60 + x["sec"])
        return "{Minuto}/".format(Minuto=diff[0]["min"], Segundos=diff[0]["sec"])
    
    # Fix plays' order in list since they are originally sorted by input time,
    # which may differ from the moment it actually happened
    def fix_plays_order(self, list):
        list.sort(key=self.play_moment_order)
        return list
    
    def play_moment_order(self, play):
        period_order = ["PRE_JOGO", "PRIMEIRO_TEMPO", "INTERVALO", "SEGUNDO_TEMPO", "AGUARDANDO_PRORROGACAO", "PRIMEIRO_TEMPO_PRORROGACAO", "SEGUNDO_TEMPO_PRORROGACAO", "AGUARDANDO_PENALIDADES", "PENALIDADES", "FIM_DE_JOGO", "POS_JOGO", "JOGO_ENCERRADO"]
        period_mod = str(period_order.index(play["periodo"]))
        
        if play["momento"] == "":
            minutes_mod, seconds_mod = "00", "00"
        else:
            minutes_mod, seconds_mod, *rest = play["momento"].split(":")
        
        return int(period_mod + minutes_mod + seconds_mod)
    
    # Add some plays to the list to act as markers for each half's start/end
    def mark_period_transitions(self, list):
        match_period = self.get_data("resource.transmissao.periodo", "PRE_JOGO")
        ongoing = {
            "PRIMEIRO_TEMPO": "o Primeiro Tempo",
            "SEGUNDO_TEMPO": "o Segundo Tempo",
            "PRIMEIRO_TEMPO_PRORROGACAO": "o Primeiro Tempo da Prorrogação",
            "SEGUNDO_TEMPO_PRORROGACAO": "o Segundo Tempo da Prorrogação",
            "PENALIDADES": "a Decisão nos Pênaltis"
        }
        finished_types = ["FIM_DE_JOGO", "POS_JOGO"]
        l = len(list)
        
        # Flags where period transitions are
        transitions = []
        for index in range(0, l):
            play = list[index]
            prev_ = None
            next_ = None
            if index > 0:
                prev_ = list[index - 1]
            if index < (l - 1):
                next_ = list[index + 1]
            
            if play["periodo"] in ongoing:
                if prev_ != None and prev_["periodo"] != play["periodo"]:
                    transitions.append({
                        "index": index,
                        "period": play["periodo"],
                        "moment": "00:00",
                        "type": "TRANSICAO_INICIO",
                        "created": play["created"],
                        "title": "Começa " + ongoing[play["periodo"]] + "!"
                    })
                if (next_ != None and next_["periodo"] != play["periodo"]) or (next_ == None and match_period in finished_types):
                    transitions.append({
                        "index": index + 1,
                        "period": play["periodo"],
                        "moment": play["momento"],
                        "type": "TRANSICAO_FIM",
                        "created": play["created"],
                        "title": "Termina " + ongoing[play["periodo"]] + "!"
                    })
        
        # Flags if match is finished
        if match_period in finished_types:
            transitions.append({
                "index": l+1,
                "period": "JOGO_ENCERRADO",
                "moment": play["momento"],
                "type": "TRANSICAO_INICIO",
                "created": play["created"],
                "title": "Fim de Jogo!"
            })
        
        # Actually adds the transition messages where previously flagged
        for trans in reversed(transitions):
            list.insert(trans["index"], {
                "corpo": {
                    "blocks": [{
                            "text": ""
                        }
                    ],
                    "entityMap": {}
                },
                "titulo": trans["title"],
                "periodo": trans["period"],
                "momento": trans["moment"],
                "created": trans["created"],
                "tipoLance": trans["type"]
            })
            
        return list
    
    # Sorts plays in blocks for better spacing between each half and interval subs
    def organize_plays(self, play_list):
        period_blocks = [
            self.get_plays_from_period(play_list, ["PRE_JOGO"]),
            self.get_plays_from_period(play_list, ["PRIMEIRO_TEMPO"]),
            self.get_plays_from_period(play_list, ["INTERVALO"]),
            self.get_plays_from_period(play_list, ["SEGUNDO_TEMPO"]),
            self.get_plays_from_period(play_list, ["AGUARDANDO_PRORROGACAO"]),
            self.get_plays_from_period(play_list, ["PRIMEIRO_TEMPO_PRORROGACAO"]),
            self.get_plays_from_period(play_list, ["SEGUNDO_TEMPO_PRORROGACAO"]),
            self.get_plays_from_period(play_list, ["AGUARDANDO_PENALIDADES", "PENALIDADES"]),
            self.get_plays_from_period(play_list, ["FIM_DE_JOGO", "POS_JOGO", "JOGO_ENCERRADO"])
        ]
        blocks = list(filter(lambda x: len(x) > 0, period_blocks))
                
        blocks_text = []
        for block in blocks:
            block_translated = list(map(self.translate_play, block))
            blocks_text.append("  \n".join(block_translated))
        
        return "  \n&nbsp;  \n".join(blocks_text)
    
    def get_plays_from_period(self, play_list, periods):
        return list(filter(lambda x: x["periodo"] in periods, play_list))
    
    # Filter plays to only keep relevant stuff
    def filter_plays(self, play_list):
        return list(filter(self.is_valid_play, play_list))
        
    def is_valid_play(self, play):
        types = ["SUBSTITUICAO", "CARTAO_AMARELO", "CARTAO_VERMELHO", "GOL", "GOL_CONTRA", "PENALTI", "TRANSICAO_INICIO", "TRANSICAO_FIM"]
        if self.detailed:
            types.append("IMPORTANTE")
        return play["tipoLance"] in types

    # Formats play's output text according to its type
    def translate_play(self, play):
        period = self.get_play_period(play)
        title = self.get_play_title(play)
        body = []
        for b in play["corpo"]["blocks"]:
            body.append(b["text"].replace("\n", ", "))
        body = ". ".join(list(filter(lambda x: len(x) > 0, body)))
        
        if play["tipoLance"] == "SUBSTITUICAO":
            body = body.replace("Sai: ", "SAIU: ", 1).replace("Entra: ", "ENTROU: ", 1)
        if play["tipoLance"] == "TRANSICAO_INICIO":
            return "{Title}".format(Title=title)
        if play["tipoLance"] == "TRANSICAO_FIM":
            return "**{Period}** {Title}".format(Period = period, Title=title)
        if play["periodo"] == "INTERVALO":
            return "**[{Period}]** {Title} {Body}".format(
                Period = period,
                Title = title,
                Body = body
            )
        
        return "**{Period}** {Title} {Body}".format(
            Period = period,
            Title = title,
            Body = self.beautify_title(body)
        )

    # Get label for the moment the play happened
    def get_play_period(self, play):
        period_labels = {
            "PRIMEIRO_TEMPO": "{Minutos}/1T",
            "SEGUNDO_TEMPO": "{Minutos}/2T",
            "PRIMEIRO_TEMPO_PRORROGACAO": "{Minutos}/1P",
            "SEGUNDO_TEMPO_PRORROGACAO": "{Minutos}/2P",
            "INTERVALO": "Intervalo",
            "AGUARDANDO_PRORROGACAO": "Intervalo",
            "AGUARDANDO_PENALIDADES": "Intervalo",
            "PENALIDADES": "Pênaltis",
            "JOGO_ENCERRADO": "Fim de Jogo",
            "FIM_DE_JOGO": "Fim de Jogo"
        }
        label = period_labels[play["periodo"]] or ""
        minutes = play["momento"].split(":")[0]
        
        return label.format(Minutos=minutes)

    # Formats plays' title, adding icon when necessary
    def get_play_title(self, play):
        type = play["tipoLance"]
        
        if type == "PENALTI":
            team_name = self.home_team["nome"] if play["time"] == self.home_team["equipe_id"] else self.away_team["nome"]
            return "{Icone} {Time} |".format(
                Icone = match_icons["penalti_scored"] if play["disputaPenalti"] == "penalti-convertido" else match_icons["penalti_missed"],
                Time = team_name
            )
        
        if "jogador" not in play:
            if "jogadorReserva" in play:
                player = self.find_player(play["jogadorReserva"])
                team = self.get_player_team(play["jogadorReserva"])
            else:
                return self.get_play_icon(type) + self.beautify_title(play["titulo"])
        else:
            player = self.find_player(play["jogador"])
            team = self.get_player_team(play["jogador"])
        other_team = self.away_team if team == self.home_team else self.home_team
        
        if type == "SUBSTITUICAO":
            return match_icons["subs"] + " Substituição n{Artigo} {Time}:".format(
                Artigo = self.get_article(team),
                Time = team["nome"]
            )
        elif type == "CARTAO_AMARELO":
            return match_icons["yellow_card"] + " " + self.beautify_title(play["titulo"])
        elif type == "CARTAO_VERMELHO":
            return match_icons["red_card"] + " " + self.beautify_title(play["titulo"])
        elif type == "GOL":
            return "**{Icone} Gol d{Artigo} {Time}!**".format(
                Icone = match_icons["goal"],
                Jogador = player["nome_popular"],
                Artigo = self.get_article(team),
                Time = team["nome"]
            )
        elif type == "GOL_CONTRA":
            return "**{Icone} Gol d{Artigo} {Time}!**".format(
                Icone = match_icons["own_goal"],
                Jogador = player["nome_popular"],
                Artigo = self.get_article(team),
                Time = other_team["nome"]
            )
        else:
            return self.beautify_title(play["titulo"])
    
    def get_play_icon(self, type):
        if type == "SUBSTITUICAO":
            return match_icons["subs"] + " "
        elif type == "CARTAO_AMARELO":
            return match_icons["yellow_card"] + " "
        elif type == "CARTAO_VERMELHO":
            return match_icons["red_card"] + " "
        elif type == "GOL":
            return match_icons["goal"] + " "
        elif type == "GOL_CONTRA":
            return match_icons["own_goal"] + " "
            
        return ""
        
    # Strips trailing spaces and adds period to the end of line if needed
    def beautify_title(self, str):
        if len(str) == 0:
            return str
        symbols = [",",".",";","!","?","(",")","[","]"]
        str = str.strip()
        punctuation = "" if str[-1] in symbols else "."
        return str[0].upper() + str[1:] + punctuation
    
    # Get score for a single team, with penalties added between brackets if needed
    # Format differs between teams to accomodate the 1 (5) x (4) 1 format
    # Output Format for Home team: 1 (5)
    # Output Format for Away team: (5) 1
    def get_score(self, team):
        try:
            score = self.get_data("resource.transmissao.jogo_sde.resultados.placar_oficial_"+team, "")
            penalties = self.get_data("resource.transmissao.jogo_sde.resultados.placar_penaltis_"+team, "")
            
            if penalties == "":
                return str(score)
            else:
                if team == "mandante":
                    return "{Placar} ({Penaltis})".format(Placar=score, Penaltis=penalties)
                else:
                    return "({Penaltis}) {Placar}".format(Placar=score, Penaltis=penalties)
        except:
            return "0"
    
    # Get score for both teams, with the 1 (5) x (4) 1
    # x is already included, and penalties only show up if needed
    def get_final_score(self):
        home_score = self.get_data("resource.transmissao.jogo_sde.resultados.placar_oficial_mandante", None)
        away_score = self.get_data("resource.transmissao.jogo_sde.resultados.placar_oficial_visitante", None)
        home_penalties = self.get_data("resource.transmissao.jogo_sde.resultados.placar_penaltis_mandante", None)
        away_penalties = self.get_data("resource.transmissao.jogo_sde.resultados.placar_penaltis_visitante", None)
        
        if home_score == None:
            return "x"
        elif home_penalties == None:
            return "{PlacarCasa} x {PlacarFora}".format(PlacarCasa = home_score, PlacarFora = away_score)
        else:
            return "{PlacarCasa} ({PenaltisCasa}x{PenaltisFora}) {PlacarFora}".format(PlacarCasa = home_score, PlacarFora = away_score, PenaltisCasa = home_penalties, PenaltisFora = away_penalties)
    
    # Removes seconds from time format because who needs them?
    def format_time(self, raw):
        parts = raw.split(":")
        return parts[0] + ":" + parts[1]
        
    # Formats date from '2021-02-28' format to '28 de Fevereiro de 2021' format
    def format_date(self, raw):
        parts = raw.split("-")
        day = str(int(parts[2]))
        month = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][int(parts[1])-1]
        
        return "{Dia} de {Mes} de {Ano}".format(Dia=day, Mes=month, Ano=parts[0])
    
    # Find player based on id
    def find_player(self, player_id):
        for p in self.home_team["atletas"]["titulares"] + self.home_team["atletas"]["reservas"]:
            if player_id == p["atleta_id"]:
                return p
        for p in self.away_team["atletas"]["titulares"] + self.away_team["atletas"]["reservas"]:
            if player_id == p["atleta_id"]:
                return p
        return None
    
    # Find team based on player's id
    def get_player_team(self, player_id):
        if self.is_player_from_team(player_id, self.home_team):
            return self.home_team
        if self.is_player_from_team(player_id, self.away_team):
            return self.away_team

    # Checks if player_id belongs to team
    def is_player_from_team(self, player_id, team):
        for p in team["atletas"]["titulares"]:
            if p["atleta_id"] == player_id:
                return True
        for p in team["atletas"]["reservas"]:
            if p["atleta_id"] == player_id:
                return True
        return False
    
    # Returns gender-specific article for the team's name
    def get_article(self, team):
        return "o" if team["genero"] == "M" else "a"
    
    # Get list of players for the team, with substitutions between brackets if needed
    def get_team_list(self, team, type):
        if team["atletas"] == None or type not in team["atletas"]:
            return "Não disponível"
        
        res = []
        list = team["atletas"][type]
        for player in list:
            if type == "titulares":
                res.append(player["nome_popular"] + self.get_subs(player["atleta_id"]))
            elif not self.was_subbed_in(player["atleta_id"]):
                res.append(player["nome_popular"])
        return ", ".join(res)
    
    # Gets substitutes for player
    def get_subs(self, player_id):
        subbed = self.subbed_players
        if player_id in subbed:
            info = subbed[player_id]
            subbed_in = self.find_player(info["sub_in"])
            sub_name = subbed_in["nome_popular"]
            if subbed_in["atleta_id"] in subbed:
                sub_name += self.get_subs(info["sub_in"])
            return " ({Sub})".format(Sub=sub_name)
        return ""
        
    def was_subbed_in(self, player_id):
        for key, sub in self.subbed_players.items():
            if sub["sub_in"] == player_id:
                return True
        return False
    
    # Identifies goalscorers and sort them by team
    def find_goalscorers(self):
        home_id = self.home_team["equipe_id"]
        away_id = self.away_team["equipe_id"]
        scorers = { "home": {}, "away": {}}
        
        filtered = list(filter(lambda x: x["tipoLance"] == "GOL" or x["tipoLance"] == "GOL_CONTRA", self.fixed_plays))
        for s in filtered:
            if "jogador" in s and s["jogador"] != None:
                is_own = ""
                if s["tipoLance"] == "GOL_CONTRA":
                    team = "home" if s["time"] == away_id else "away"
                    is_own = ", contra"
                else:
                    team = "home" if s["time"] == home_id else "away"
                
                player_id = s["jogador"]
                if player_id not in scorers[team]:
                    scorers[team][player_id] = []
                
                scorers[team][player_id].append(self.get_play_period(s) + is_own)
        return scorers
    
    # Get lists of goalscorers for the team
    def get_goals_list(self, team):
        scorers = self.goalscorers[team]
        
        if len(scorers) == 0:
            return "N/D"
        
        out = []
        for key, val in scorers.items():
            player = self.find_player(key)
            out.append(player["nome_popular"] + " (" + ", ".join(val) + ")")
        return ", ".join(out)
    
    # Formats team's formation
    def get_formation(self, team):
        if "esquema_tatico" in team and team["esquema_tatico"] != None:
            return "-".join(list(team["esquema_tatico"]))
        else:
            return "N/D"
    
    def get_referees(self):
        referees = self.get_data("resource.transmissao.jogo.arbitragem", None)
        if referees == None:
            return "Não disponível"
            
        referee_list = []
        if "arbitroPrincipal" in referees and referees["arbitroPrincipal"] != None:
            referee_list.append(referees["arbitroPrincipal"]["nome_popular"] + " (Árbitro Principal)")
        if "arbitroAssistente1" in referees and referees["arbitroAssistente1"] != None:
            referee_list.append(referees["arbitroAssistente1"]["nome_popular"] + " (Assistente 1)")
        if "arbitroAssistente2" in referees and referees["arbitroAssistente2"] != None:
            referee_list.append(referees["arbitroAssistente2"]["nome_popular"] + " (Assistente 2)")
        if "quartoArbitro" in referees and referees["quartoArbitro"] != None:
            referee_list.append(referees["quartoArbitro"]["nome_popular"] + " (Quarto Árbitro)")
            
        return ", ".join(referee_list)
    
    def format_time(self, raw):
        parts = raw.split(":")
        return parts[0] + ":" + parts[1]
        
    def format_date(self, raw):
        parts = raw.split("-")
        day = str(int(parts[2]))
        month = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][int(parts[1])-1]
        
        return "{Dia} de {Mes} de {Ano}".format(Dia=day, Mes=month, Ano=parts[0])
    
    # Gets value from Settings object; if value is not found, returns default_value
    def get_setting(self, settings, prop, default_value):
        if prop in settings:
            return settings[prop]
        else:
            return default_value
    
    # Gets value from GE Match JSON; if value is not found, returns default_value
    def get_data(self, path, default_value="-"):
        obj = self.data
        for i in path.split("."):
            if i in obj and obj[i] != None:
                obj = obj[i]
            else:
                return default_value
        return obj
    