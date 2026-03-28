import argparse
import smtplib
from email.message import EmailMessage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smtp-host", required=True)
    parser.add_argument("--smtp-port", type=int, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--from-addr", required=True)
    parser.add_argument("--to", action="append", required=True, dest="recipients")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--ssl", action="store_true")
    args = parser.parse_args()

    msg = EmailMessage()
    msg["From"] = args.from_addr
    msg["To"] = ", ".join(args.recipients)
    msg["Subject"] = args.subject
    with open(args.body_file, "r", encoding="utf-8") as handle:
        msg.set_content(handle.read())

    if args.ssl:
        server = smtplib.SMTP_SSL(args.smtp_host, args.smtp_port, timeout=30)
    else:
        server = smtplib.SMTP(args.smtp_host, args.smtp_port, timeout=30)
        server.starttls()

    with server:
        server.login(args.username, args.password)
        server.send_message(msg)


if __name__ == "__main__":
    main()
