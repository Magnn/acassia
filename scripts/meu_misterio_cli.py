"""CLI da API Meu Mistério. Use MM_BASE_URL e MM_API_KEY ou flags globais."""
import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from sdk import MeuMisterioClient, MeuMisterioError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="meu-misterio")
    parser.add_argument("--base-url", default=os.getenv("MM_BASE_URL", "http://localhost:5000"))
    parser.add_argument("--api-key", default=os.getenv("MM_API_KEY"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ping")
    get = sub.add_parser("contact-get"); get.add_argument("contact")
    upsert = sub.add_parser("contact-upsert"); upsert.add_argument("phone"); upsert.add_argument("--name", default=""); upsert.add_argument("--tag", action="append", default=[])
    send = sub.add_parser("message-send"); send.add_argument("recipient"); send.add_argument("text"); send.add_argument("--channel", default="whatsapp")
    enroll = sub.add_parser("sequence-enroll"); enroll.add_argument("sequence_id", type=int); enroll.add_argument("--contact-id", type=int); enroll.add_argument("--phone")
    args = parser.parse_args(argv)
    if not args.api_key:
        parser.error("informe --api-key ou MM_API_KEY")
    client = MeuMisterioClient(args.base_url, args.api_key)
    try:
        if args.command == "ping": result = client.ping()
        elif args.command == "contact-get": result = client.get_contact(args.contact)
        elif args.command == "contact-upsert": result = client.upsert_contact(args.phone, args.name, args.tag)
        elif args.command == "message-send": result = client.send_message(args.recipient, args.text, args.channel)
        else: result = client.enroll_sequence(args.sequence_id, contact_id=args.contact_id, phone=args.phone)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except MeuMisterioError as exc:
        print(json.dumps({"error": str(exc), "status": exc.status}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
