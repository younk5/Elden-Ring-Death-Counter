# ☠ Elden Ring Death Counter

Contador de mortes automático para Elden Ring. Detecta a tela de "VOCÊ MORREU" via captura de tela e incrementa o contador em tempo real — sem precisar clicar em nada.

Compatível com OBS via arquivo de texto. Overlay configurável para aparecer direto na stream.

![Python](https://img.shields.io/badge/Python-3.8+-c9a227?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Plataforma-Windows-8b1a1a?style=flat-square&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/Licença-MIT-555555?style=flat-square)

---

## Funcionalidades

- Detecção automática da tela de morte por análise de cor e contorno das letras
- Overlay transparente e arrastável com o número de mortes
- Cor, tamanho e posição do overlay totalmente configuráveis
- Ajuste manual do contador (+1 / −1 / reset)
- Salva o valor em `voce_morreu.txt` para uso no OBS
- Salva screenshots automáticas de cada morte (se a pasta `save_img/` existir)

---

## Requisitos

- Windows 10 ou 11
- Python 3.8+
- Elden Ring rodando em tela cheia ou janela sem bordas em resolução base **1920×1080**

---

## Instalação

```bash
git clone https://github.com/younk5/Elden-Ring-Death-Counter.git
cd elden-ring-counter
pip install opencv-python mss numpy
python elden_ring_counter.py
```

As dependências também são instaladas automaticamente na primeira execução caso não estejam presentes.

---

## Uso

1. Abra o Elden Ring
2. Execute `elden_ring_counter.py`
3. Clique em **▶ INICIAR**
4. Morra (inevitavelmente)

O contador atualiza sozinho. Para ajuste manual use os botões **+1**, **−1** ou **RESET**.

### Overlay

Marque **"Mostrar overlay"** para exibir só o número flutuando na tela. Clique em **⚙ Configurar overlay** para mudar cor, tamanho e posição. O overlay pode ser arrastado diretamente com o mouse; clique direito o esconde.

### OBS

Adicione uma fonte de texto no OBS apontando para o arquivo `voce_morreu.txt` gerado na mesma pasta do script. O valor atualiza automaticamente a cada morte.

---


## Detecção

A detecção funciona por análise de imagem sem OCR:

- Captura a tela a cada ~350ms e normaliza para 1920×1080
- Aplica máscara HSV calibrada para o vermelho escuro do texto "VOCÊ MORREU"
- Valida os contornos encontrados por dimensão, alinhamento horizontal, span e espaçamento entre letras
- Cooldown de 5 segundos entre detecções para evitar contagem dupla

Funciona com qualquer idioma do sistema, pois a detecção é visual, não textual.

---

## Estrutura

```
elden-ring-counter/
├── elden_ring_counter.py   # script principal
├── voce_morreu.txt         # contador (criado automaticamente)
└── save_img/               # screenshots de mortes (opcional, crie a pasta)
```
