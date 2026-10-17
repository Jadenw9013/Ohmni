"""Harmless first-round-trip operation, sourced from the real application options."""
from ohmni.application.projects import project_options


def supported_options_reply(message: str) -> str:
    if not isinstance(message, str) or not message.strip() or len(message) > 2000:
        return "Describe your board or ask for supported options in 1–2,000 characters."
    options = project_options()
    families = "\n".join(f"- {item['title']}: {item['description']}" for item in options['families'])
    return (
        "Ohmni’s real supported board options:\n" + families
        + "\n\nAll use USB-C power and an ESP32. Supported sensors measure temperature, "
        "humidity and pressure; smell identification is not supported.\n\n"
        "This first connectivity release lists options only: it has not saved a plan or "
        "started a build. Planning, explicit confirmation and build tools are the next integration step.\n\n"
        + "\n".join(options['limitations'])
    )
