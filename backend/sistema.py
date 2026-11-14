"""Azioni sul sistema: appunti e finestra delle cartelle.

Servono al flusso manuale. Quando il post si pubblica dal compositore, l'immagine
deve essere a portata di mano: copiarla negli appunti significa allegarla con
Ctrl+V, senza andare a cercare il file.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class SistemaError(Exception):
    """Azione sul sistema non riuscita, con il motivo leggibile."""


# Lo script sta in un file e si lancia con -File: passare lo stesso codice inline
# con -Command e' la via fragile (virgolette e percorso da difendere).
# -STA non e' opzionale: senza, gli appunti di Windows non rispondono.
SCRIPT_APPUNTI = """param([string]$Percorso)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile($Percorso)
[System.Windows.Forms.Clipboard]::SetImage($img)
$img.Dispose()
if ([System.Windows.Forms.Clipboard]::ContainsImage()) { Write-Output "immagine-negli-appunti" }
"""


def copia_immagine(percorso: Path) -> str:
    """Mette l'immagine negli appunti, come bitmap: si incolla con Ctrl+V."""
    percorso = Path(percorso)
    if not percorso.exists():
        raise SistemaError(f"immagine inesistente: {percorso.name}")

    with tempfile.TemporaryDirectory() as cartella:
        script = Path(cartella) / "appunti.ps1"
        script.write_text(SCRIPT_APPUNTI, encoding="utf-8")
        try:
            esito = subprocess.run(
                ["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
                 "-File", str(script), "-Percorso", str(percorso)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=90)
        except (OSError, subprocess.TimeoutExpired) as errore:
            raise SistemaError(f"non ho potuto usare gli appunti: {errore}") from None

    if "immagine-negli-appunti" in (esito.stdout or ""):
        return "immagine negli appunti: nel compositore basta Ctrl+V"
    dettaglio = (esito.stderr or esito.stdout or "").strip().replace("\n", " ")
    raise SistemaError("l'immagine non e' arrivata negli appunti: " + dettaglio[:300])


def apri_cartella(percorso: Path) -> str:
    """Apre Esplora file con quel file selezionato."""
    percorso = Path(percorso)
    if not percorso.exists():
        raise SistemaError(f"immagine inesistente: {percorso.name}")
    try:
        # explorer esce con codice 1 anche quando riesce: non si controlla l'esito.
        subprocess.Popen(["explorer", f"/select,{percorso}"])
    except OSError as errore:
        raise SistemaError(f"non ho potuto aprire la cartella: {errore}") from None
    return "cartella aperta con il file selezionato"
