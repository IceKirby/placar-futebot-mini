# Thread Template for ongoing matches
match_template = """
# [{MomentoPartida}] {TimeCasa} {PlacarFinal} {TimeFora}  
**Gols {TimeCasa}:** *{TimeCasaGols}*  
**Gols {TimeFora}:** *{TimeForaGols}*  
  
---  
  
**{Campeonato} - {CampeonatoFase}**  
**Estádio:** {Estadio}  
**Data:** {Data}, {Horario}  
[Link para Live Match Thread]({RedditStream})  
  
---  
  
Escalações:  
  
| {TimeCasa} ({TimeCasaEsquema}) | {TimeFora} ({TimeForaEsquema}) |  
| :-- | :-- |  
| {TimeCasaTitulares} | {TimeForaTitulares} |  
| **Suplentes:** | **Suplentes:** |  
| {TimeCasaReservas} | {TimeForaReservas} |  
| **Técnico:** {TimeCasaTreinador} | **Técnico:** {TimeForaTreinador} |  
  

**Arbitragem:** {Arbitragem}  
  
---  
  
# Lances  
{Lances}
"""

# Thread Template for upcoming matches
match_no_info = """
# {TimeCasa} x {TimeFora}  
**{Campeonato}**  
**Data:** {Data}, {Horario}  
"""

# Thread Template for matches without GE reporting
simple_match_template = """
# {TimeCasa} {PlacarCasa} x {PlacarFora} {TimeFora}  

---  
  
**{Campeonato}**  
**Data:** {Data}, {Horario}  
[Link para Live Thread]({RedditStream})  
  
*(Detalhes da partida não disponíveis)*
"""

# Icons used in match descriptions
match_icons = {
    "goal": "⚽",
    "own_goal": "⚽",
    "subs": "🔃",
    "yellow_card": "🟨",
    "red_card": "🟥",
    "penalti_scored": "✔️",
    "penalti_missed": "❌"
}