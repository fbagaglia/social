"""CLI di xpost: prepara una bozza, mostrala, e solo su comando esplicito pubblicala.

    python -m xpost login [--set-client]
    python -m xpost whoami
    python -m xpost draft --text "..." [--image FOTO] [--reply-to ID] [--source URL]
    python -m xpost list
    python -m xpost show <id|latest>
    python -m xpost publish <id|latest> [--yes]
"""

from __future__ import annotations

import argparse
import getpass
import json
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

from . import api, auth
from . import config as cfg

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def out(line: str = "") -> None:
    """Stampa robusta: il codepage di Windows non regge ogni carattere."""
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write(line.encode(enc, errors="replace").decode(enc) + "\n")


def slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:limit] or "post").strip("-")


# --------------------------------------------------------------------------- #
# Bozze
# --------------------------------------------------------------------------- #

def draft_path(draft_id: str) -> Path:
    return cfg.OUTBOX / f"{draft_id}.json"


def save_draft(payload: dict) -> Path:
    cfg.ensure_dirs()
    path = draft_path(payload["id"])
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_draft(ref: str) -> dict:
    if ref == "latest":
        drafts = sorted(cfg.OUTBOX.glob("*.json"))
        if not drafts:
            raise cfg.ConfigError("Nessuna bozza in outbox/. Crea prima un draft.")
        path = drafts[-1]
    else:
        path = draft_path(ref)
        if not path.exists():
            raise cfg.ConfigError(f"Bozza non trovata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def estimate_cost(text: str) -> float:
    return cfg.COST_WITH_URL_USD if URL_RE.search(text) else cfg.COST_TEXT_OR_MEDIA_USD


def validate(text: str, images: list[Path]) -> list[str]:
    """Problemi bloccanti (-) e avvisi (~)."""
    problems: list[str] = []
    if not text.strip():
        problems.append("- il testo e' vuoto")
    if len(text) > cfg.MAX_TEXT_CHARS:
        problems.append(
            f"- testo di {len(text)} caratteri, oltre i {cfg.MAX_TEXT_CHARS} "
            "di un account senza X Premium"
        )
    if len(images) > cfg.MAX_IMAGES_PER_POST:
        problems.append(f"- {len(images)} immagini, X ne ammette al massimo {cfg.MAX_IMAGES_PER_POST}")
    for image in images:
        try:
            api.check_image(image)
        except SystemExit as exc:
            problems.append(f"- {exc}")
    if not images:
        problems.append("~ nessuna immagine: il post partira' di solo testo")
    if URL_RE.search(text):
        problems.append(
            f"~ il testo contiene un URL: il costo stimato sale a "
            f"~${cfg.COST_WITH_URL_USD:.2f} invece di ~${cfg.COST_TEXT_OR_MEDIA_USD:.3f}"
        )
    return problems


# --------------------------------------------------------------------------- #
# Comandi
# --------------------------------------------------------------------------- #

def cmd_login(args: argparse.Namespace) -> int:
    if args.set_client:
        out("Credenziali dell'app X (le trovi su https://console.x.com, sezione Keys and tokens).")
        client_id = input("Client ID: ").strip()
        if not client_id:
            raise cfg.ConfigError("Client ID vuoto: annullato.")
        secret = getpass.getpass("Client Secret (invio se l'app e' un client pubblico): ").strip()
        path = cfg.save_client(client_id, secret or None)
        out(f"Credenziali salvate in {path.relative_to(cfg.ROOT)}")
        out("(non finiscono in git: .state/ e' in .gitignore)\n")
    auth.login()
    out("Login completato.")
    return cmd_whoami(args)


def cmd_whoami(_args: argparse.Namespace) -> int:
    me = api.get_me(auth.access_token())
    flag = " (verificato)" if me.get("verified") else ""
    out(f"Account autorizzato: @{me.get('username')} — {me.get('name')}{flag}")
    out(f"id: {me.get('id')}")
    return 0


def cmd_draft(args: argparse.Namespace) -> int:
    cfg.ensure_dirs()
    images = [Path(p).expanduser().resolve() for p in (args.image or [])]
    text = args.text
    problems = validate(text, images)
    blocking = [p for p in problems if p.startswith("-")]

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    payload = {
        "id": f"{stamp}-{slugify(text)}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "draft",
        "text": text,
        "images": [str(p) for p in images],
        "reply_to": args.reply_to,
        "source": args.source,
        "chars": len(text),
        "estimated_cost_usd": estimate_cost(text),
        "posted": None,
    }
    path = save_draft(payload)

    out(f"Bozza salvata: {path.relative_to(cfg.ROOT)}")
    out(f"  {len(text)}/{cfg.MAX_TEXT_CHARS} caratteri · {len(images)} immagini "
        f"· costo stimato ~${payload['estimated_cost_usd']:.3f}")
    for note in problems:
        out("  " + note)
    if blocking:
        out("\nBozza scritta ma NON pubblicabile finche' restano i punti con '-'.")
        return 1
    out("\nNon e' stato pubblicato nulla. Per inviarlo:  python -m xpost publish " + payload["id"])
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    cfg.ensure_dirs()
    drafts = sorted(cfg.OUTBOX.glob("*.json"))
    if not drafts:
        out("Nessuna bozza in outbox/.")
        return 0
    for path in drafts:
        data = json.loads(path.read_text(encoding="utf-8"))
        state = data.get("status", "?")
        first = data.get("text", "").splitlines()[0][:60] if data.get("text") else ""
        out(f"{data['id']:<48} {state:<8} {first}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    data = load_draft(args.ref)
    out("=" * 72)
    out(data["text"])
    out("=" * 72)
    out(f"caratteri: {data.get('chars')} · stato: {data.get('status')}")
    if data.get("images"):
        for image in data["images"]:
            out(f"immagine: {image}")
        out("Per la via manuale: apri il compositore, incolla il testo, allega il file.")
    for line in validate(data["text"], [Path(p) for p in data.get("images", [])]):
        out("  " + line)

    if args.intent:
        query = urllib.parse.urlencode({"text": data["text"][: cfg.MAX_TEXT_CHARS]})
        out("\nIntent URL (testo e link soltanto, l'immagine resta manuale):")
        out(f"{cfg.INTENT_URL}?{query}")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    data = load_draft(args.ref)
    images = [Path(p) for p in data.get("images", [])]
    problems = validate(data["text"], images)
    blocking = [p for p in problems if p.startswith("-")]
    if blocking and not args.force:
        for note in problems:
            out("  " + note)
        raise cfg.ConfigError("Bozza non pubblicabile: correggi i punti con '-'.")

    token = auth.access_token()
    me = api.get_me(token)
    out(f"Pubblico come @{me.get('username')}")
    out("-" * 72)
    out(data["text"])
    for image in images:
        out(f"[immagine] {image}")
    out("-" * 72)
    out(f"costo stimato ~${data.get('estimated_cost_usd', 0):.3f}")

    if not args.yes:
        answer = input("Confermi l'invio su X? [s/N] ").strip().lower()
        if answer not in ("s", "si", "sì", "y", "yes"):
            out("Annullato: nulla e' stato pubblicato.")
            return 0

    media_ids = [api.upload_image(image, token) for image in images] or None
    if media_ids:
        out(f"Immagini caricate: {', '.join(media_ids)}")
    result = api.create_post(data["text"], token, media_ids=media_ids,
                             reply_to=data.get("reply_to"))
    data["status"] = "published"
    data["posted"] = {"at": datetime.now().isoformat(timespec="seconds"), **result}
    save_draft(data)
    out(f"Pubblicato: {result['permalink']}")
    return 0


# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m xpost",
        description="Prepara e pubblica post su X (testo + immagine) con l'API ufficiale v2.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("login", help="autorizza l'account (OAuth 2.0 PKCE)")
    p.add_argument("--set-client", action="store_true",
                   help="chiede Client ID/Secret dell'app e li salva in .state/client.json")
    p.set_defaults(func=cmd_login)

    sub.add_parser("whoami", help="mostra su quale account stai operando").set_defaults(func=cmd_whoami)

    p = sub.add_parser("draft", help="crea una bozza in outbox/ (non pubblica nulla)")
    p.add_argument("--text", required=True)
    p.add_argument("--image", action="append", help="ripetibile, max 4")
    p.add_argument("--reply-to", help="id del post a cui rispondere")
    p.add_argument("--source", help="URL dell'articolo da cui nasce il post")
    p.set_defaults(func=cmd_draft)

    sub.add_parser("list", help="elenca le bozze").set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="mostra una bozza (e l'intent URL)")
    p.add_argument("ref", help="id della bozza oppure 'latest'")
    p.add_argument("--intent", action="store_true", help="stampa anche l'intent URL di X")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("publish", help="PUBBLICA davvero su X")
    p.add_argument("ref", help="id della bozza oppure 'latest'")
    p.add_argument("--yes", action="store_true", help="salta la conferma interattiva")
    p.add_argument("--force", action="store_true", help="ignora i problemi bloccanti (sconsigliato)")
    p.set_defaults(func=cmd_publish)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except cfg.ConfigError as exc:
        out(str(exc))
        return 2
    except KeyboardInterrupt:
        out("\nInterrotto.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
