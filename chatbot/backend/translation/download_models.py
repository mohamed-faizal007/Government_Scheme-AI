"""One-time setup: download and install the Argos Translate language packages
needed for en<->ta and en<->hi translation.

Run manually once per machine/environment:
    python -m chatbot.backend.translation.download_models

Do NOT call this at application startup — downloading is slow and should not
happen on every process boot.
"""
import logging

from argostranslate import package

logger = logging.getLogger(__name__)

# (from, to) language pairs required by translator.py
REQUIRED_PAIRS = [
    ("en", "ta"),
    ("ta", "en"),
    ("en", "hi"),
    ("hi", "en"),
]


def main():
    print("Updating Argos Translate package index...")
    package.update_package_index()
    available_packages = package.get_available_packages()

    installed_codes = {
        (p.from_code, p.to_code) for p in package.get_installed_packages()
    }

    for from_code, to_code in REQUIRED_PAIRS:
        if (from_code, to_code) in installed_codes:
            print(f"Already installed: {from_code} -> {to_code}")
            continue

        match = next(
            (p for p in available_packages if p.from_code == from_code and p.to_code == to_code),
            None,
        )
        if match is None:
            print(f"WARNING: no package found for {from_code} -> {to_code}")
            continue

        print(f"Downloading and installing {from_code} -> {to_code}...")
        package.install_from_path(match.download())
        print(f"Installed {from_code} -> {to_code}")

    print("Done.")


if __name__ == "__main__":
    main()
