"""
sensitivityClassifier – Sensitivitetsklassifisering for SOFIA
===============================================================
Denne modulen definerer sensitivitetsklassene og verktøydefinisjonen
som lar agenten klassifisere dokumenter etter informasjonssensitivitet.

Et dokument kan tilhøre flere klasser samtidig dersom innholdet dekker
flere sensitivitetsnivåer.

Klassene er designet for å støtte GDPR-etterlevelse og
informasjonssikkerhetspolicyer i norske virksomheter.

Eksporterer:
    - SENSITIVITY_CLASSES: Dict med alle sensitivitetsklasser og beskrivelser
    - SENSITIVITY_TOOL_DEFINITION: JSON-definisjon for Foundry function-calling
    - format_sensitivity_result(): Hjelpefunksjon for formatering av resultater

Bruk fra agent.py:
    from sensitivityClassifier import SENSITIVITY_TOOL_DEFINITION, SENSITIVITY_CLASSES
"""

import logging

log = logging.getLogger(__name__)

# ── Sensitivitetsklasser ─────────────────────────────────────────────────────
# Hver klasse har en ID (brukes i kode/automasjon), et norsk navn, og en
# beskrivelse som hjelper agenten å velge riktig klassifisering.
# Et dokument kan tilhøre FLERE klasser samtidig.

SENSITIVITY_CLASSES = {
    "open": {
        "name": "Åpen",
        "level": 1,
        "description": (
            "Ingen begrensninger, kan deles fritt. "
            "Eksempler: markedsmateriell, offentlige rapporter, pressemeldinger."
        ),
    },
    "internal": {
        "name": "Intern",
        "level": 2,
        "description": (
            "Ikke ment for eksterne, men uten særskilt sensitivitet. "
            "Eksempler: vanlige interne notater, møtereferater uten persondata, "
            "interne prosedyrer."
        ),
    },
    "personal_data": {
        "name": "Personopplysninger",
        "level": 3,
        "description": (
            "Inneholder persondata regulert av GDPR: navn koblet med kontaktinfo, "
            "fødselsdato, adresse, e-post, telefonnummer, bruker-IDer, "
            "ansattnummer, eller andre identifiserbare opplysninger om enkeltpersoner."
        ),
    },
    "sensitive_personal_data": {
        "name": "Sensitive personopplysninger",
        "level": 4,
        "description": (
            "Særlige kategorier etter GDPR art. 9: helseopplysninger, "
            "fagforeningsmedlemskap, religiøs eller filosofisk overbevisning, "
            "politiske meninger, seksuell orientering, biometriske data, "
            "genetiske data, eller straffbare forhold."
        ),
    },
    "health_data": {
        "name": "Helseopplysninger",
        "level": 4,
        "description": (
            "Spesifikt helse- og pasientrelatert informasjon: journaler, "
            "diagnoser, behandlingsplaner, medisinlister, sykmeldinger, "
            "psykologvurderinger. Tilleggsflagg som brukes sammen med "
            "'Sensitive personopplysninger'."
        ),
    },
    "confidential_business": {
        "name": "Konfidensiell virksomhet",
        "level": 5,
        "description": (
            "Intern bedriftsinformasjon som kan skade virksomheten ved lekkasje. "
            "Eksempler: økonomiske analyser, interne strategidokumenter, "
            "ikke-offentlige rapporter, interne revisjoner, organisatoriske "
            "endringer som ikke er annonsert."
        ),
    },
    "business_critical": {
        "name": "Forretningskritisk",
        "level": 7,
        "description": (
            "Informasjon med høy økonomisk eller operasjonell betydning. "
            "Eksempler: kundeavtaler med priser, prisstrategi, "
            "interne risikovurderinger, fusjons-/oppkjøpsplaner, "
            "budsjetter med strategisk innhold, leverandørbetingelser."
        ),
    },
    "trade_secret": {
        "name": "Bedriftshemmelighet",
        "level": 8,
        "description": (
            "Kjernehemmeligheter og know-how som gir konkurransefortrinn. "
            "Eksempler: proprietære algoritmer, kildekode med unik verdi, "
            "produktformler, uannonserte innovasjoner, patentsøknader under arbeid."
        ),
    },
    "strictly_confidential": {
        "name": "Strengt konfidensielt",
        "level": 9,
        "description": (
            "Kombinasjon av svært sensitive persondata og/eller "
            "forretningshemmeligheter med høy risiko ved lekkasje. "
            "Kun et fåtall autoriserte personer skal ha tilgang. "
            "Eksempler: whistleblower-rapporter, sikkerhetsrevisjoner med "
            "kritiske sårbarheter, topphemmelige strategiplaner."
        ),
    },
}

# ── Verktøydefinisjon for Foundry ────────────────────────────────────────────
# Agenten bruker dette verktøyet til å rapportere sensitivitetsklassifiseringen.
# Det er et "output"-verktøy – agenten kaller det for å strukturere svaret sitt.

SENSITIVITY_TOOL_DEFINITION = {
    "type": "function",
    "name": "classify_sensitivity",
    "description": (
        "Klassifiser dokumentets sensitivitetsnivå basert på innholdet. "
        "Et dokument KAN tilhøre flere klasser samtidig. "
        "Kall dette verktøyet etter at du har lest og analysert dokumentet."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "classes": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": list(SENSITIVITY_CLASSES.keys()),
                },
                "description": (
                    "Liste med sensitivitetsklasse-IDer som gjelder for dokumentet. "
                    "Velg ALLE som er relevante. Gyldige verdier: "
                    + ", ".join(SENSITIVITY_CLASSES.keys())
                ),
            },
            "justification": {
                "type": "string",
                "description": (
                    "Kort begrunnelse (1-3 setninger) for hvorfor disse klassene ble valgt. "
                    "Nevn konkret hva i dokumentet som utløser klassifiseringen."
                ),
            },
        },
        "required": ["classes", "justification"],
    },
}


def format_sensitivity_result(classes: list[str], justification: str) -> dict:
    """
    Formater sensitivitetsklassifiseringen til et strukturert resultat.

    Args:
        classes: Liste med klasse-IDer (f.eks. ["internal", "personal_data"])
        justification: Begrunnelse fra agenten

    Returnerer:
        Dict med klassifiseringsresultat inkludert norske navn og nivåer.
    """
    result_classes = []
    max_level = 0

    for class_id in classes:
        if class_id in SENSITIVITY_CLASSES:
            cls = SENSITIVITY_CLASSES[class_id]
            result_classes.append({
                "id": class_id,
                "name": cls["name"],
                "level": cls["level"],
            })
            max_level = max(max_level, cls["level"])

    return {
        "status": "ok",
        "classes": result_classes,
        "highest_level": max_level,
        "justification": justification,
    }
