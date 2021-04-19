# Placar Futebot Mini
Um simples bot que captura informações de partidas do GE e posta no Reddit como uma Match Thread

# Como Funciona?

O programa cria a Match Thread na hora do jogo, atualizando as informações a cada 30 segundos com os dados do Placar GE.

# Como Usar

#### Configuração Inicial

- Baixe a versão mais recente para seu sistema operacional em [Releases](https://github.com/IceKirby/placar-futebot-mini/releases).
- Crie um ClientID e Client Secret da sua conta do Reddit de acordo [com estas instruções](https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example#first-steps).
- Abra `praw.ini` em um editor de texto e preencha com o seu nome de usuário do Reddit, senha, ClientID e Client Secret.
- Abra `config.ini` em um editor de texto e preencha os campos sob `[SETTINGS]` de acordo com as instruções.

Estas instruções só precisam ser executadas uma vez.

#### Preparando para uma partida

- Acesse a página da [Agenda GE](https://globoesporte.globo.com/agenda/#/todos) e encontre o jogo que você quer rodar com o Placar Futebot.
- Abra `config.ini` em um editor de texto e preencha os campos de `data`, `hora`, `competicao`, `mandante` e `visitante` conforme listados no GE. **Importante:** Os nomes dos times e competição devem ser preenchidos exatamente como no GE, ou o bot não conseguirá identificar a partida.
- **[Opcional]** Acesse o site [365scores.com](https://www.365scores.com) e encontre o jogo que você quer acompanhar. Copie os nomes dos times para os campo `mandante_stat` e `visitante_stat`. Estes campos são usados para estatísticas pós-jogo, e os nomes dos times podem diferir entre GE e 365scores, então preencha com atenção.
- Execute o programa Placar-Futebot-Mini e deixe-o rodando até o término do jogo. É possível deixar o programa rodando com antecedência, permitindo acompanhar uma partida mesmo quando você estiver indisponível.

Estas instruções precisam ser executadas para cada partida que você quiser acompanhar.


# Limitações

Esta versão do bot só roda uma Match Thread por vez.

# Por que Mini?

A ideia inicial era criar um bot mais robusto, que pudesse rodas múltiplas partidas simultaneamente e rodasse em um servidor dedicado. Entretanto, essa versão reduzida foi criada antes para permitir que qualquer usuário rode sua Match Thread a partir de seu computador, assim podendo permitir que o bot já seja utilizado enquanto a versão expandida é desenvolvida.

A versão expandida ainda está nos planos, mas sem promessa de prazos.
