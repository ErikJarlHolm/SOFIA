# SOFIA – Smart Office File Intelligence Agent

Dokumentklassifiseringsagent som analyserer og klassifiserer kontordokumenter i 90 forhåndsdefinerte kategorier.

## Oppsett

1. Kopier `.env.example` til `.env` og fyll inn verdiene
2. Logg inn: `azd auth login --scope https://ai.azure.com/.default`
3. Installer avhengigheter: `pip install -r requirements.txt`

## Bruk

```bash
# Opprett agenten i Foundry
python agent.py create

# Start interaktiv klassifisering
python agent.py chat

# Begge deler
python agent.py create chat
```

## Støttede filtyper

- `.docx` – Word-dokumenter
- `.pdf` – PDF-filer
- `.txt` – Ren tekst
- `.pptx` – PowerPoint-presentasjoner

## Dokumentmappe

Dokumentene som skal klassifiseres legges i:
```
C:\Users\erikholm\OneDrive - Atea\Documents\Kunder\Atea AI Norge\Dokumentklassifisering
```
