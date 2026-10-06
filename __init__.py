"""d3bian-init-paleta-xfce: prepara e ajusta um Debian por uma pagina local.

Roda so com a biblioteca padrao do Python, que ja vem instalada no Debian.
Nada de pip, nada de dependencia externa.

A identidade do projeto mora so aqui. O criar.py troca estes valores ao gerar
um projeto novo; o codigo le daqui e as paginas recebem pelo servidor.
"""

NOME = "d3bian-init-paleta-xfce"
DESCRICAO = "Deixa o Xfce do Debian numa paleta so: Nord, Gruvbox ou Everforest nas janelas, icones, terminal e papel de parede."
VERSAO = "0.1.0"
# cada projeto na sua porta, para dois paineis poderem ficar abertos juntos
PORTA = 8931

__all__ = ["NOME", "DESCRICAO", "VERSAO", "PORTA"]
