"""
SOFIA – Smart Office File Intelligence Agent
=============================================
Klassifiserer dokumenter etter en forhåndsdefinert kategoriliste og gir
en kort beskrivelse av innholdet.

Arkitektur-oversikt:
    Prosjektet er bygget som en Azure AI Foundry-agent med ett lokalt verktøy:
        - read_document: Leser innholdet fra en fil (.docx, .pdf, .txt, .pptx)

    Flyten er:
    1. Konfigurasjon lastes fra .env via python-dotenv
    2. Agentdefinisjon bygges med system prompt + read_document-verktøy
    3. Agenten registreres i Azure AI Foundry (create-kommandoen)
    4. Chat-løkken håndterer verktøykall og viser klassifiseringsresultat

Bruk:
    python agent.py create          # Opprett / oppdater agenten i Foundry
    python agent.py chat            # Start interaktiv samtale med agenten
    python agent.py create chat     # Opprett og start samtale umiddelbart

Forutsetninger:
    - Kopier .env.example til .env og fyll inn verdiene
    - Logg inn med: azd auth login --scope https://ai.azure.com/.default
    - Installer avhengigheter: pip install -r requirements.txt

Avhengigheter:
    - azure-ai-projects: Foundry-klient for agentregistrering og chat
    - azure-identity: Autentisering mot Azure (DefaultAzureCredential)
    - python-dotenv: Laster .env-variabler
    - python-docx: Lesing av .docx-filer
    - PyPDF2: Lesing av .pdf-filer
    - python-pptx: Lesing av .pptx-filer
"""

# ── Standardbibliotek ────────────────────────────────────────────────────────
import json
import os
import sys
import logging
from pathlib import Path

# ── Tredjepartspakker ────────────────────────────────────────────────────────
from dotenv import load_dotenv     # Laster miljøvariabler fra .env-fil
from azure.identity import DefaultAzureCredential  # Azure-autentisering
from azure.ai.projects import AIProjectClient      # Foundry-klient for agenter og chat

# ── Lokale moduler ───────────────────────────────────────────────────────────
from readDocument import READ_DOCUMENT_TOOL_DEFINITION, read_document

# ── Lasting av konfigurasjon ────────────────────────────────────────────────
# override=False betyr at eksisterende OS-miljøvariabler har forrang over .env
load_dotenv(override=False)

# PROJECT_ENDPOINT: Full URL til Foundry-prosjektet
PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT", "")

# MODEL_DEPLOYMENT_NAME: Navnet på modell-deploymenten i Azure AI Foundry
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-5-mini")

# AGENT_NAME: Identifikator for agenten i Foundry
AGENT_NAME = os.environ.get("AGENT_NAME", "sofia")

# Sti til system prompt-filen
SYSTEM_PROMPT_FILE = Path(__file__).parent / "system_prompt.txt"

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ── Verktøy-dispatcher ──────────────────────────────────────────────────────


def execute_tool_call(tool_name: str, tool_args: dict) -> str:
    """
    Dispatcher for verktøykall fra Foundry-agenten.

    Støttede verktøy:
        - read_document: Leser innholdet fra en fil i dokumentmappen

    Returnerer: JSON-streng med resultatet (eller feilmelding for ukjente verktøy)
    """
    if tool_name == "read_document":
        result = read_document(tool_args.get("filename", ""))
        return json.dumps(result, ensure_ascii=False)
    return json.dumps({"error": f"Ukjent verktøy: {tool_name}"})


# ── Hjelpefunksjoner ─────────────────────────────────────────────────────────


def load_system_prompt() -> str:
    """Les system prompt fra fil. Kaster FileNotFoundError hvis filen mangler."""
    if not SYSTEM_PROMPT_FILE.exists():
        raise FileNotFoundError(f"Finner ikke system prompt: {SYSTEM_PROMPT_FILE}")
    return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")


def build_agent_definition(system_prompt: str) -> dict:
    """
    Bygg agentdefinisjon med verktøy for registrering i Foundry.

    Denne dict-en sendes til Foundry via create_version() og definerer:
        - kind: "prompt" = en instruksjonsbasert agent
        - instructions: System-prompten som styrer agentens oppførsel
        - model: Hvilken LLM-deployment som skal brukes
        - tools: read_document-verktøyet for å lese filer
    """
    return {
        "kind": "prompt",
        "instructions": system_prompt,
        "model": MODEL_DEPLOYMENT_NAME,
        "tools": [READ_DOCUMENT_TOOL_DEFINITION],
    }


def get_client() -> AIProjectClient:
    """
    Opprett Foundry-klient med DefaultAzureCredential.

    DefaultAzureCredential prøver flere autentiseringsmetoder i rekkefølge:
        1. Miljøvariabler (AZURE_CLIENT_ID osv.)
        2. Managed Identity (i Azure-miljø)
        3. Azure CLI (az login)
        4. Azure Developer CLI (azd auth login)

    Kaster ValueError hvis PROJECT_ENDPOINT ikke er konfigurert.
    """
    if not PROJECT_ENDPOINT:
        raise ValueError(
            "PROJECT_ENDPOINT er ikke satt. "
            "Kopier .env.example til .env og fyll inn endepunktet."
        )
    credential = DefaultAzureCredential()
    return AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)


# ── Opprett / oppdater agent ─────────────────────────────────────────────────


def create_or_update_agent() -> None:
    """Opprett en ny versjon av SOFIA-agenten i Foundry."""
    log.info("Laster system prompt fra %s", SYSTEM_PROMPT_FILE)
    system_prompt = load_system_prompt()

    definition = build_agent_definition(system_prompt)

    log.info("Kobler til Foundry: %s", PROJECT_ENDPOINT)
    client = get_client()

    log.info("Oppretter / oppdaterer agent '%s' ...", AGENT_NAME)
    result = client.agents.create_version(AGENT_NAME, {"definition": definition})

    log.info(
        "Agent opprettet. Navn: '%s'  |  Versjon: %s",
        AGENT_NAME,
        result.get("version", "ukjent"),
    )
    print(f"\n✅  Agent '{AGENT_NAME}' er klar i Foundry.\n")


# ── Interaktiv chat med verktøy-loop ─────────────────────────────────────────


def interactive_chat() -> None:
    """Start en interaktiv samtale med SOFIA-agenten, inkludert verktøy-loop."""
    log.info("Kobler til Foundry for chat: %s", PROJECT_ENDPOINT)
    client = get_client()
    openai_client = client.get_openai_client()

    # conversation_history holder hele samtalen for kontekst
    conversation_history: list[dict] = []

    print("\n📄  SOFIA – Smart Office File Intelligence Agent")
    print("    Jeg klassifiserer dokumenter for deg.")
    print("    Skriv filnavnet på dokumentet du vil klassifisere, eller 'avslutt' for å avslutte.\n")

    while True:
        try:
            user_input = input("Du: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nAvslutter samtalen.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"avslutt", "exit", "quit"}:
            print("Samtalen er avsluttet.")
            break

        conversation_history.append({"role": "user", "content": user_input})

        try:
            # Første API-kall med brukerens melding + full historikk
            response = openai_client.responses.create(
                model=MODEL_DEPLOYMENT_NAME,
                input=conversation_history,
                extra_body={
                    "agent_reference": {
                        "type": "agent_reference",
                        "name": AGENT_NAME,
                    }
                },
            )

            # ── Verktøy-loop ──────────────────────────────────────────────────
            # Fortsett å kjøre verktøy til svaret er ren tekst
            while True:
                tool_calls = [
                    item for item in (response.output or [])
                    if getattr(item, "type", None) == "function_call"
                ]

                if not tool_calls:
                    break

                # Kjør verktøy og samle resultater
                tool_outputs = []
                for tc in tool_calls:
                    tool_name = tc.name
                    tool_args = json.loads(tc.arguments or "{}")
                    log.info("Verktøykall: %s(%s)", tool_name, tool_args)
                    print("  📖 Leser dokument ...", flush=True)

                    tool_result = execute_tool_call(tool_name, tool_args)
                    tool_outputs.append({
                        "type": "function_call_output",
                        "call_id": tc.call_id,
                        "output": tool_result,
                    })

                # Send verktøyresultatene tilbake med previous_response_id
                response = openai_client.responses.create(
                    model=MODEL_DEPLOYMENT_NAME,
                    input=tool_outputs,
                    extra_body={
                        "agent_reference": {
                            "type": "agent_reference",
                            "name": AGENT_NAME,
                        },
                        "previous_response_id": response.id,
                    },
                )

            assistant_message = response.output_text or ""
            conversation_history.append(
                {"role": "assistant", "content": assistant_message}
            )
            print(f"\nSOFIA: {assistant_message}\n")

        except Exception as exc:
            log.error("Feil under API-kall: %s", exc)
            print(f"\n⚠️  Feil: {exc}\n")


# ── Inngangspunkt ─────────────────────────────────────────────────────────────


def main() -> None:
    """Parse kommandolinjeargumenter og kjør valgt(e) kommando(er)."""
    args = set(sys.argv[1:])

    if not args or args.isdisjoint({"create", "chat"}):
        print(__doc__)
        sys.exit(0)

    if "create" in args:
        create_or_update_agent()

    if "chat" in args:
        interactive_chat()


if __name__ == "__main__":
    main()
