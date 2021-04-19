import praw
import time
import requests
import configurations
import Stats
import traceback
import ScheduleManager as schedule
from datetime import datetime, timedelta, timezone
from PostTemplate import match_no_info
from MatchData import Match
from SimpleMatchData import SimpleMatch

reddit = praw.Reddit('bot1')
settings = configurations.get_config()
match_info = configurations.get_config(section="MATCH")
store= configurations.get_config(section="STORE")

match = None
attempt_count = 10

def start_up():
    print("Iniciando Placar Futebot Mini...")

    global match
    if store["simplified_data"] == "True":
        match = SimpleMatch(match_info)
    else:
        match = Match(settings)

    while True:
        if run_loop(match):
            break
        if attempt_count <= 0:
            print("Encerrando programa devido ao excesso de erros durante as tentativas de atualizar Match Thread.")
            break
        print("Próxima atualização em 30 segundos")
        time.sleep(30)

    print("Finished!")

def run_loop(match_data):
    # Creates Match Thread if past the scheduled time
    if store["thread_id"] == "":
        if is_match_time(include_pre_time=True):
            print("Criando Match Thread")
            create_thread()
        else:
            return False

    # Find GE Match URL
    if store["match_url"] == "":
        print("Procurando URL da partida no GE")
        if find_match_url():
            match_data.update_data(store["match_url"])
            update_match_thread(match_data)
        # If GE url can't be found until match time, change to SimpleMatch mode
        elif is_match_time(include_pre_time=False):
            print("URL da partida no GE não encontrada, alternando para Modo Simples")
            global match
            match = SimpleMatch(match_info)
            configurations.save_setting(property="match_url", value="N/A")
            configurations.save_setting(property="simplified_data", value="True")
            reload_config()
    else:
        # Update/Finish Match
        if match_data.is_finished:
            finish_match(match_data)
            return True
        else:
            update_match_thread(match_data)
    return False

# Checks if it's past the schedule time
def is_match_time(include_pre_time=True):
    match_date = match_info["data"]
    match_time = match_info["hora"]

    now = datetime.now(timezone(-timedelta(hours=3)))
    pre_match_time = timedelta(minutes=int(settings["pre_match"]))
    res = datetime.strptime(match_date + " " + match_time, "%d/%m/%Y %H:%M")
    if include_pre_time:
        res = res - pre_match_time
    res = res.replace(tzinfo=timezone(-timedelta(hours=3)))
    return now > res

# Creates Match Thread according to MATCH and SETTINGS from config.ini
def create_thread():
    subreddit = reddit.subreddit(settings["subreddit"])
    title = settings["title"].format(
        Campeonato=match_info["competicao"],
        Mandante=match_info["mandante"],
        Visitante=match_info["visitante"]
    )

    flair = find_flair(subreddit, settings["flair"])
    text = match_no_info.format(
        Campeonato=match_info["competicao"],
        TimeCasa=match_info["mandante"],
        TimeFora=match_info["visitante"],
        Data=match_info["data"],
        Horario=match_info["hora"]
    )
    if flair:
        submission_id = subreddit.submit(title, selftext=text, flair_id=flair["id"])
    else:
        submission_id = subreddit.submit(title, selftext=text)
    reddit.submission(submission_id).disable_inbox_replies()
    configurations.save_setting(property="thread_id", value=submission_id)
    reload_config()

# Update Match Data and print content to Match Thread
def update_match_thread(match):
    print("Atualizando conteúdo da Match Thread")
    try:
        match.update_data(store["match_url"])
        run_text_match(match)
    except requests.exceptions.RequestException as err:
        print("Request Error when trying to update Match Data: " + str(err))
        global attempt_count
        attempt_count = attempt_count - 1

# Try to find GE Match URL from the GE Agenda page
def find_match_url():
    day = "-".join(match_info["data"].split("/")[::-1])
    try:
        sched = schedule.get_day_matches(day)
    except requests.exceptions.RequestException as err:
        print("Request Error when trying to find URL: " + str(err))
        return False

    tour_name = match_info["competicao"]
    home_team = match_info["mandante"]
    away_team = match_info["visitante"]

    championships = sched["data"]["championshipsAgenda"]
    for ch in championships:
        if ch["championship"]["name"] == tour_name:
            for match in ch["now"] + ch["past"] + ch["future"]:
                info = match["match"]
                if info["homeTeam"]["popularName"] == home_team and info["awayTeam"]["popularName"] == away_team:
                    if "transmission" in info and info["transmission"] != None and "url" in info["transmission"] and info["transmission"]["url"] != None:
                        configurations.save_setting(property="match_url", value=info["transmission"]["url"])
                        reload_config()
                        return True
    return False

# Clears STORE variables from config.ini
def reset_store_vars():
    configurations.save_setting(property="thread_id", value="")
    configurations.save_setting(property="match_url", value="")
    configurations.save_setting(property="simplified_data", value="")
    reload_config()

# Reloads settings variables (required after settings are changed)
def reload_config():
    global settings
    settings = configurations.get_config()

    global match_info
    match_info = configurations.get_config(section="MATCH")

    global store
    store= configurations.get_config(section="STORE")

# Find Post Flair in specific sub
def find_flair(sub, str):
    for f in sub.flair.link_templates:
        if f["text"] == str:
            return f

# Creates Post-Match Thread
def finish_match(match):
    print("Criando Post Match Thread")
    post_match_thread(match)
    reset_store_vars()

def post_match_thread(match):
    subreddit = reddit.subreddit(settings["subreddit"])
    flair = find_flair(subreddit, settings["post_flair"])
    title = settings["post_title"].format(
        Campeonato=match_info["competicao"],
        Mandante=match_info["mandante"],
        Visitante=match_info["visitante"],
        PlacarMandante=match.get_score("mandante"),
        PlacarVisitante=match.get_score("visitante")
    )
    text = match.print_match(store["thread_id"])
    stats = Stats.find_stats(match_info["data"], match_info["mandante_stat"], match_info["visitante_stat"])
    if stats != None:
        text += "  \n--- \n"
        text += stats

    if flair:
        submission_id = subreddit.submit(title, selftext=text, flair_id=flair["id"])
    else:
        submission_id = subreddit.submit(title, selftext=text)
    reddit.submission(submission_id).disable_inbox_replies()

# Process Match text and edit Thread with it
def run_text_match(match):
    txt = match.print_match(store["thread_id"])
    submission = reddit.submission(id=store["thread_id"])
    submission.edit(txt)

if __name__ == "__main__":
    import sys
    try:
        start_up()
    except KeyboardInterrupt:
        print("Comando para encerrar programa detectado.")
    except Exception:
        traceback.print_exc()
    finally:
        input("Programa encerrado, pressione Enter para fechar.")
